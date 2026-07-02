"""Ad Calendar / scheduling: queue approved ads to post, view, and cancel.

Only *approved* ads can be scheduled. Actual posting (and all limit/budget
enforcement) happens in the engine's poster — see app/engine.py.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Ad, Schedule, User
from ..enums import AdStatus, Role, ScheduleStatus
from ..schemas import ScheduleCreate, ScheduleOut

router = APIRouter(prefix="/api/schedules", tags=["scheduling"])

_EDITORS = (Role.creator, Role.manager)


@router.post("", response_model=ScheduleOut, status_code=201)
def create_schedule(
    body: ScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Schedule:
    ad = db.get(Ad, body.ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found.")
    if ad.status != AdStatus.approved.value:
        raise HTTPException(
            status_code=409,
            detail=f"Only approved ads can be scheduled (status: {ad.status}).",
        )
    sched = Schedule(
        ad_id=ad.id, platform=ad.platform, scheduled_at=body.scheduled_at,
        status=ScheduleStatus.queued.value, note=body.note, created_by=user.email,
    )
    ad.status = AdStatus.scheduled.value
    db.add(sched)
    db.flush()
    log_action(db, user=user, action="schedule.create", entity_type="schedule",
               entity_id=sched.id, detail={"ad_id": ad.id,
                                           "at": body.scheduled_at.isoformat()})
    db.commit()
    db.refresh(sched)
    return sched


@router.get("", response_model=list[ScheduleOut])
def list_schedules(
    status: ScheduleStatus | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Schedule]:
    """Calendar feed. Filter by status and/or a [start, end] window."""
    q = db.query(Schedule)
    if status:
        q = q.filter(Schedule.status == status.value)
    if start:
        q = q.filter(Schedule.scheduled_at >= start)
    if end:
        q = q.filter(Schedule.scheduled_at <= end)
    return q.order_by(Schedule.scheduled_at.asc()).all()


@router.post("/{schedule_id}/cancel", response_model=ScheduleOut)
def cancel_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Schedule:
    sched = db.get(Schedule, schedule_id)
    if sched is None:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    if sched.status != ScheduleStatus.queued.value:
        raise HTTPException(
            status_code=409,
            detail=f"Only queued schedules can be canceled (status: {sched.status}).",
        )
    sched.status = ScheduleStatus.canceled.value
    log_action(db, user=user, action="schedule.cancel", entity_type="schedule", entity_id=sched.id)
    db.commit()
    db.refresh(sched)
    return sched
