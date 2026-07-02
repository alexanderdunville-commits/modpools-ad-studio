"""Dashboard tab: a single rollup of the numbers the team watches."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..db_models import Ad, Campaign, Metric, Notification, Schedule, User
from ..engine import get_setting
from ..enums import AdStatus, CampaignStatus, ScheduleStatus

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> dict:
    now = datetime.utcnow()
    week_ahead = now + timedelta(days=7)

    impr, clicks, leads, spend, conv, revenue = db.query(
        func.coalesce(func.sum(Metric.impressions), 0),
        func.coalesce(func.sum(Metric.clicks), 0),
        func.coalesce(func.sum(Metric.leads), 0),
        func.coalesce(func.sum(Metric.spend), 0.0),
        func.coalesce(func.sum(Metric.conversions), 0),
        func.coalesce(func.sum(Metric.revenue), 0.0),
    ).one()
    impr, clicks, leads, conv = int(impr), int(clicks), int(leads), int(conv)
    spend, revenue = float(spend), float(revenue)

    def count(model, *filters) -> int:
        q = db.query(func.count(model.id))
        for f in filters:
            q = q.filter(f)
        return int(q.scalar() or 0)

    return {
        "emergency_stop": get_setting(db).emergency_stop,
        "active_campaigns": count(Campaign, Campaign.status == CampaignStatus.active.value),
        "total_campaigns": count(Campaign),
        "live_ads": count(Ad, Ad.status == AdStatus.live.value),
        "pending_approvals": count(Ad, Ad.status == AdStatus.pending.value),
        "scheduled_next_7d": count(
            Schedule,
            Schedule.status == ScheduleStatus.queued.value,
            Schedule.scheduled_at >= now,
            Schedule.scheduled_at <= week_ahead,
        ),
        "unread_alerts": count(Notification, Notification.read.is_(False)),
        "kpis": {
            "impressions": impr, "clicks": clicks, "leads": leads,
            "spend": round(spend, 2), "conversions": conv,
            "revenue": round(revenue, 2),
            "ctr": round(clicks / impr, 4) if impr else 0.0,
            "cpl": round(spend / leads, 2) if leads else 0.0,
            "roas": round(revenue / spend, 2) if spend else 0.0,
        },
    }
