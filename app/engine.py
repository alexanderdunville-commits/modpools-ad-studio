"""The enforcement engine — the safety core of the Ad Manager.

Two operations, meant to run on a schedule (Celery beat / cron) in production
and exposed via `POST /api/engine/tick` for local/manual runs:

- `run_poster`  — publish due, approved schedules, but ONLY after every guardrail
  passes: emergency stop, blackout dates, min-gap, volume limits, active-ad
  limits, and hard budget caps. Blocked posts are skipped with a reason.
- `run_rule_engine` — enforce hard budgets and auto-pause rules against stored
  metrics, pausing offending live ads.

All limit/budget lookups use the most-specific-wins resolver
(ad → campaign → platform → global).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from .db_models import (
    Ad,
    AutoPauseRule,
    BlackoutDate,
    Budget,
    Limit,
    Metric,
    Notification,
    PlatformConnection,
    Schedule,
    Setting,
)
from .enums import (
    AdStatus,
    AutoPauseAction,
    AutoPauseRuleType,
    BudgetPeriod,
    CapType,
    ConnectionMode,
    LimitMetric,
    ScheduleStatus,
)
from .publishing import get_adapter


# ---------------------------------------------------------------- helpers
def get_setting(db: Session) -> Setting:
    s = db.get(Setting, 1)
    if s is None:  # defensive; init_db seeds it
        s = Setting(id=1)
        db.add(s)
        db.flush()
    return s


def is_emergency_stopped(db: Session) -> bool:
    return get_setting(db).emergency_stop


def notify(db: Session, *, type: str, message: str,
           entity_type: str | None = None, entity_id: int | None = None) -> None:
    db.add(Notification(type=type, message=message,
                        entity_type=entity_type, entity_id=entity_id))


def _connection_mode(db: Session, platform: str) -> str:
    conn = db.query(PlatformConnection).filter(
        PlatformConnection.platform == platform
    ).first()
    return conn.mode if conn else ConnectionMode.sandbox.value


def effective_limit(db: Session, metric: LimitMetric, *,
                    platform: str, campaign_id: int) -> Limit | None:
    """Most-specific-wins: campaign → platform → global."""
    rows = db.query(Limit).filter(Limit.metric == metric.value).all()
    by_campaign = next((r for r in rows if r.scope == "campaign"
                        and r.scope_ref_id == campaign_id), None)
    if by_campaign:
        return by_campaign
    by_platform = next((r for r in rows if r.scope == "platform"
                        and r.scope_ref_value == platform), None)
    if by_platform:
        return by_platform
    return next((r for r in rows if r.scope == "global"), None)


def _period_start(period: str, today: date) -> date:
    if period == BudgetPeriod.daily.value:
        return today
    if period == BudgetPeriod.weekly.value:
        return today - timedelta(days=today.weekday())
    if period == BudgetPeriod.monthly.value:
        return today.replace(day=1)
    return date(1970, 1, 1)  # lifetime


def spend_for(db: Session, *, scope: str, campaign_id: int | None,
              platform: str | None, period: str, today: date | None = None) -> float:
    today = today or date.today()
    start = _period_start(period, today)
    q = db.query(func.coalesce(func.sum(Metric.spend), 0.0)).join(
        Ad, Metric.ad_id == Ad.id
    ).filter(Metric.date >= start)
    if scope == "campaign" and campaign_id is not None:
        q = q.filter(Ad.campaign_id == campaign_id)
    elif scope == "platform" and platform is not None:
        q = q.filter(Ad.platform == platform)
    return float(q.scalar() or 0.0)


def _count_posted(db: Session, *, since: datetime,
                  platform: str | None, campaign_id: int | None) -> int:
    q = db.query(func.count(Schedule.id)).filter(
        Schedule.status == ScheduleStatus.posted.value,
        Schedule.posted_at >= since,
    )
    if platform is not None:
        q = q.filter(Schedule.platform == platform)
    if campaign_id is not None:
        q = q.join(Ad, Schedule.ad_id == Ad.id).filter(Ad.campaign_id == campaign_id)
    return int(q.scalar() or 0)


def _active_on_platform(db: Session, platform: str) -> int:
    return int(
        db.query(func.count(Ad.id)).filter(
            Ad.platform == platform, Ad.status == AdStatus.live.value
        ).scalar() or 0
    )


def in_blackout(db: Session, *, platform: str, campaign_id: int,
                on: date | None = None) -> bool:
    on = on or date.today()
    rows = db.query(BlackoutDate).filter(
        BlackoutDate.start_date <= on, BlackoutDate.end_date >= on
    ).all()
    for r in rows:
        if r.scope == "global":
            return True
        if r.scope == "campaign" and r.scope_ref_id == campaign_id:
            return True
        if r.scope == "platform" and r.scope_ref_value == platform:
            return True
    return False


# ---------------------------------------------------------------- can-post gate
def can_post(db: Session, ad: Ad, *, now: datetime) -> tuple[bool, str, bool]:
    """Return (ok, reason, is_hard_block). A soft block (min-gap, emergency stop)
    keeps the schedule queued to retry; a hard block skips it."""
    if is_emergency_stopped(db):
        return False, "Emergency stop is active.", False  # keep queued
    if ad.status not in (AdStatus.approved.value, AdStatus.scheduled.value):
        return False, f"Ad is not approved (status: {ad.status}).", True
    if in_blackout(db, platform=ad.platform, campaign_id=ad.campaign_id,
                   on=now.date()):
        return False, "Blackout date — posting is paused.", True

    # min gap between posts on the same platform
    gap = effective_limit(db, LimitMetric.min_gap_minutes,
                          platform=ad.platform, campaign_id=ad.campaign_id)
    if gap:
        last = db.query(func.max(Schedule.posted_at)).filter(
            Schedule.platform == ad.platform,
            Schedule.status == ScheduleStatus.posted.value,
        ).scalar()
        if last and (now - last) < timedelta(minutes=gap.value):
            return False, f"Min {int(gap.value)} min between posts not met.", False

    # volume caps (day / week / month)
    windows = [
        (LimitMetric.max_ads_day, timedelta(days=1)),
        (LimitMetric.max_ads_week, timedelta(days=7)),
        (LimitMetric.max_ads_month, timedelta(days=30)),
    ]
    for metric, delta in windows:
        lim = effective_limit(db, metric, platform=ad.platform,
                              campaign_id=ad.campaign_id)
        if lim:
            scope_campaign = lim.scope == "campaign"
            scope_platform = lim.scope == "platform"
            posted = _count_posted(
                db, since=now - delta,
                platform=ad.platform if scope_platform or scope_campaign else None,
                campaign_id=ad.campaign_id if scope_campaign else None,
            )
            if posted >= lim.value:
                return False, f"{metric.value} cap reached ({int(lim.value)}).", True

    # max active ads per platform
    active_cap = effective_limit(db, LimitMetric.max_active_per_platform,
                                 platform=ad.platform, campaign_id=ad.campaign_id)
    if active_cap and _active_on_platform(db, ad.platform) >= active_cap.value:
        return False, f"Max active ads on {ad.platform} reached.", True

    # hard budget caps already reached (don't start spending more)
    for budget in db.query(Budget).filter(Budget.cap_type == CapType.hard.value).all():
        if budget.scope == "campaign" and budget.scope_ref_id != ad.campaign_id:
            continue
        if budget.scope == "platform" and budget.scope_ref_value != ad.platform:
            continue
        spent = spend_for(db, scope=budget.scope, campaign_id=ad.campaign_id,
                          platform=ad.platform, period=budget.period, today=now.date())
        if spent >= budget.amount:
            return False, (
                f"{budget.scope} {budget.period} budget "
                f"${budget.amount:.0f} already reached."
            ), True

    return True, "", False


# ---------------------------------------------------------------- poster
def run_poster(db: Session, *, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    due = db.query(Schedule).filter(
        Schedule.status == ScheduleStatus.queued.value,
        Schedule.scheduled_at <= now,
    ).order_by(Schedule.scheduled_at.asc()).all()

    posted, skipped, deferred = 0, 0, 0
    for sched in due:
        ad = db.get(Ad, sched.ad_id)
        if ad is None:
            sched.status = ScheduleStatus.failed.value
            sched.note = "Ad no longer exists."
            continue
        ok, reason, hard = can_post(db, ad, now=now)
        if not ok:
            if hard:
                sched.status = ScheduleStatus.skipped.value
                sched.note = reason
                notify(db, type="post_skipped",
                       message=f"Ad {ad.id} skipped: {reason}",
                       entity_type="ad", entity_id=ad.id)
                skipped += 1
            else:
                deferred += 1  # leave queued, retry next tick
            continue
        try:
            adapter = get_adapter(ad.platform, _connection_mode(db, ad.platform))
            result = adapter.publish(ad)
            sched.status = ScheduleStatus.posted.value
            sched.posted_at = now
            sched.external_post_id = result.external_post_id
            ad.status = AdStatus.live.value
            db.flush()  # so volume counts in this same tick see this post
            posted += 1
        except NotImplementedError as exc:
            sched.status = ScheduleStatus.failed.value
            sched.note = str(exc)
            notify(db, type="post_failed",
                   message=f"Ad {ad.id} failed to post: {exc}",
                   entity_type="ad", entity_id=ad.id)

    db.commit()
    return {"posted": posted, "skipped": skipped, "deferred": deferred,
            "considered": len(due)}


# ---------------------------------------------------------------- rule engine
def _window_metrics(db: Session, *, scope: str, campaign_id: int | None,
                    platform: str | None, hours: int) -> dict:
    since = date.today() - timedelta(days=max(1, hours // 24))
    q = db.query(
        func.coalesce(func.sum(Metric.spend), 0.0),
        func.coalesce(func.sum(Metric.leads), 0),
        func.coalesce(func.sum(Metric.clicks), 0),
        func.coalesce(func.sum(Metric.impressions), 0),
        func.coalesce(func.sum(Metric.conversions), 0),
        func.coalesce(func.max(Metric.frequency), 0.0),
    ).join(Ad, Metric.ad_id == Ad.id).filter(Metric.date >= since)
    if scope == "campaign" and campaign_id is not None:
        q = q.filter(Ad.campaign_id == campaign_id)
    elif scope == "platform" and platform is not None:
        q = q.filter(Ad.platform == platform)
    spend, leads, clicks, impressions, conv, freq = q.one()
    return {"spend": float(spend), "leads": int(leads), "clicks": int(clicks),
            "impressions": int(impressions), "conversions": int(conv),
            "frequency": float(freq)}


def _live_ads_in_scope(db: Session, rule: AutoPauseRule) -> list[Ad]:
    q = db.query(Ad).filter(Ad.status == AdStatus.live.value)
    if rule.scope == "campaign" and rule.scope_ref_id is not None:
        q = q.filter(Ad.campaign_id == rule.scope_ref_id)
    elif rule.scope == "platform" and rule.scope_ref_value is not None:
        q = q.filter(Ad.platform == rule.scope_ref_value)
    return q.all()


def _pause_ads(db: Session, ads: list[Ad], reason: str) -> int:
    paused = 0
    for ad in ads:
        sched = db.query(Schedule).filter(
            Schedule.ad_id == ad.id,
            Schedule.status == ScheduleStatus.posted.value,
        ).order_by(Schedule.posted_at.desc()).first()
        try:
            if sched and sched.external_post_id:
                get_adapter(ad.platform, _connection_mode(db, ad.platform)).pause(
                    sched.external_post_id
                )
        except NotImplementedError:
            pass
        ad.status = AdStatus.paused.value
        notify(db, type="auto_pause", message=f"Ad {ad.id} auto-paused: {reason}",
               entity_type="ad", entity_id=ad.id)
        paused += 1
    return paused


def _breached(rule_type: str, m: dict, threshold: float) -> bool:
    if rule_type == AutoPauseRuleType.cpl.value:
        if m["spend"] > 0 and m["leads"] == 0:
            return True  # spending with no leads → CPL effectively infinite
        return m["leads"] > 0 and (m["spend"] / m["leads"]) > threshold
    if rule_type == AutoPauseRuleType.zero_conversions.value:
        return m["spend"] > threshold and m["conversions"] == 0
    if rule_type == AutoPauseRuleType.frequency.value:
        return m["frequency"] > threshold
    if rule_type == AutoPauseRuleType.ctr.value:
        return m["impressions"] >= 500 and (
            (m["clicks"] / m["impressions"] if m["impressions"] else 0) < threshold
        )
    return False


def run_rule_engine(db: Session) -> dict:
    paused_total, alerts, budget_pauses = 0, 0, 0

    # hard budget caps → pause live ads in the over-budget scope
    for budget in db.query(Budget).filter(Budget.cap_type == CapType.hard.value).all():
        spent = spend_for(db, scope=budget.scope,
                          campaign_id=budget.scope_ref_id if budget.scope == "campaign" else None,
                          platform=budget.scope_ref_value if budget.scope == "platform" else None,
                          period=budget.period)
        if spent >= budget.amount:
            q = db.query(Ad).filter(Ad.status == AdStatus.live.value)
            if budget.scope == "campaign" and budget.scope_ref_id:
                q = q.filter(Ad.campaign_id == budget.scope_ref_id)
            elif budget.scope == "platform" and budget.scope_ref_value:
                q = q.filter(Ad.platform == budget.scope_ref_value)
            budget_pauses += _pause_ads(
                db, q.all(),
                f"{budget.scope} {budget.period} budget ${budget.amount:.0f} reached",
            )

    # auto-pause rules
    for rule in db.query(AutoPauseRule).filter(AutoPauseRule.enabled.is_(True)).all():
        m = _window_metrics(db, scope=rule.scope, campaign_id=rule.scope_ref_id,
                            platform=rule.scope_ref_value, hours=rule.window_hours)
        if not _breached(rule.rule_type, m, rule.threshold):
            continue
        reason = f"{rule.rule_type} rule breached (threshold {rule.threshold})"
        if rule.action == AutoPauseAction.pause.value:
            paused_total += _pause_ads(db, _live_ads_in_scope(db, rule), reason)
        else:
            notify(db, type="rule_alert", message=reason)
            alerts += 1

    db.commit()
    return {"auto_paused": paused_total, "budget_paused": budget_pauses,
            "alerts": alerts}


def activate_emergency_stop(db: Session) -> int:
    """Pause every live ad and set the global stop flag."""
    setting = get_setting(db)
    setting.emergency_stop = True
    live = db.query(Ad).filter(Ad.status == AdStatus.live.value).all()
    count = _pause_ads(db, live, "Emergency stop activated")
    notify(db, type="emergency_stop", message=f"EMERGENCY STOP — paused {count} live ad(s).")
    db.commit()
    return count


def clear_emergency_stop(db: Session) -> None:
    get_setting(db).emergency_stop = False
    notify(db, type="emergency_stop", message="Emergency stop cleared.")
    db.commit()
