"""Approval queue: list pending ads and approve / reject / request-changes.

Only approver/manager/admin may decide. Every decision writes an Approval row
and an audit entry, and moves the ad's status. Nothing can go live without
passing through here (Phase 4 posting depends on `approved`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Ad, Approval, AuditLog, User
from ..enums import AdStatus, ApprovalDecision, Role
from ..schemas import AdOut, ApprovalAction, AuditLogOut

router = APIRouter(prefix="/api", tags=["approvals"])

_APPROVERS = (Role.approver, Role.manager)  # + admin


def _pending_ad(db: Session, ad_id: int) -> Ad:
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found.")
    if ad.status != AdStatus.pending.value:
        raise HTTPException(
            status_code=409,
            detail=f"Ad is not awaiting approval (status: {ad.status}).",
        )
    return ad


def _decide(
    db: Session, ad: Ad, user: User, decision: ApprovalDecision,
    new_status: AdStatus, comment: str | None,
) -> Ad:
    db.add(Approval(
        ad_id=ad.id, reviewer_email=user.email,
        decision=decision.value, comment=comment,
    ))
    ad.status = new_status.value
    log_action(db, user=user, action=f"approval.{decision.value}",
               entity_type="ad", entity_id=ad.id,
               detail={"comment": comment} if comment else None)
    db.commit()
    db.refresh(ad)
    return ad


@router.get("/approvals", response_model=list[AdOut])
def approval_queue(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_APPROVERS)),
) -> list[Ad]:
    return (
        db.query(Ad)
        .filter(Ad.status == AdStatus.pending.value)
        .order_by(Ad.updated_at.asc())  # oldest first (FIFO)
        .all()
    )


@router.post("/ads/{ad_id}/approve", response_model=AdOut)
def approve_ad(
    ad_id: int,
    body: ApprovalAction | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_APPROVERS)),
) -> Ad:
    ad = _pending_ad(db, ad_id)
    return _decide(db, ad, user, ApprovalDecision.approved,
                   AdStatus.approved, body.comment if body else None)


@router.post("/ads/{ad_id}/reject", response_model=AdOut)
def reject_ad(
    ad_id: int,
    body: ApprovalAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_APPROVERS)),
) -> Ad:
    if not body.comment or not body.comment.strip():
        raise HTTPException(status_code=422, detail="A reason is required to reject.")
    ad = _pending_ad(db, ad_id)
    return _decide(db, ad, user, ApprovalDecision.rejected,
                   AdStatus.rejected, body.comment.strip())


@router.post("/ads/{ad_id}/request-changes", response_model=AdOut)
def request_changes(
    ad_id: int,
    body: ApprovalAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_APPROVERS)),
) -> Ad:
    if not body.comment or not body.comment.strip():
        raise HTTPException(
            status_code=422, detail="A comment is required to request changes."
        )
    ad = _pending_ad(db, ad_id)
    return _decide(db, ad, user, ApprovalDecision.changes_requested,
                   AdStatus.changes_requested, body.comment.strip())


@router.get("/audit", response_model=list[AuditLogOut])
def audit_log(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_APPROVERS)),
) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
