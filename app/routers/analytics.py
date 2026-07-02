"""Analytics tab: ingest metrics and read KPI rollups.

`POST /api/metrics` upserts a daily metric row per ad — this is where a real
platform sync (or a CRM/landing-page webhook for leads/sales) writes results.
`GET /api/analytics/summary` returns the funnel + derived KPIs (CTR, CPL, ROAS).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Ad, Metric, User
from ..enums import Role
from ..models import Platform
from ..schemas import KpiSummary, MetricIngest

router = APIRouter(prefix="/api", tags=["analytics"])

_MANAGERS = (Role.manager,)


@router.post("/metrics", status_code=201)
def ingest_metric(
    body: MetricIngest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> dict:
    """Upsert a daily metric row for an ad (idempotent per ad+date)."""
    if db.get(Ad, body.ad_id) is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ad not found.")
    row = db.query(Metric).filter(
        Metric.ad_id == body.ad_id, Metric.date == body.date
    ).first()
    if row is None:
        row = Metric(ad_id=body.ad_id, date=body.date)
        db.add(row)
    for field in ("impressions", "clicks", "leads", "spend", "conversions",
                  "booked_calls", "sales", "revenue", "frequency"):
        setattr(row, field, getattr(body, field))
    log_action(db, user=user, action="metric.ingest", entity_type="ad",
               entity_id=body.ad_id, detail={"date": body.date.isoformat()})
    db.commit()
    return {"ad_id": body.ad_id, "date": body.date.isoformat(), "status": "ok"}


@router.get("/analytics/summary", response_model=KpiSummary)
def analytics_summary(
    campaign_id: int | None = None,
    platform: Platform | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> KpiSummary:
    q = db.query(
        func.coalesce(func.sum(Metric.impressions), 0),
        func.coalesce(func.sum(Metric.clicks), 0),
        func.coalesce(func.sum(Metric.leads), 0),
        func.coalesce(func.sum(Metric.spend), 0.0),
        func.coalesce(func.sum(Metric.conversions), 0),
        func.coalesce(func.sum(Metric.booked_calls), 0),
        func.coalesce(func.sum(Metric.sales), 0),
        func.coalesce(func.sum(Metric.revenue), 0.0),
    ).join(Ad, Metric.ad_id == Ad.id)
    if campaign_id is not None:
        q = q.filter(Ad.campaign_id == campaign_id)
    if platform is not None:
        q = q.filter(Ad.platform == platform.value)
    if date_from is not None:
        q = q.filter(Metric.date >= date_from)
    if date_to is not None:
        q = q.filter(Metric.date <= date_to)

    impr, clicks, leads, spend, conv, calls, sales, revenue = q.one()
    impr, clicks, leads, conv, calls, sales = map(int, (impr, clicks, leads, conv, calls, sales))
    spend, revenue = float(spend), float(revenue)

    return KpiSummary(
        impressions=impr, clicks=clicks, leads=leads, spend=round(spend, 2),
        conversions=conv, booked_calls=calls, sales=sales, revenue=round(revenue, 2),
        ctr=round(clicks / impr, 4) if impr else 0.0,
        cpl=round(spend / leads, 2) if leads else 0.0,
        conversion_rate=round(conv / clicks, 4) if clicks else 0.0,
        roas=round(revenue / spend, 2) if spend else 0.0,
    )
