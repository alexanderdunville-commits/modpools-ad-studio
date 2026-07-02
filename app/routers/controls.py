"""Ad Limits tab: posting/spend limits, blackout dates, and auto-pause rules.

Reads are open to any authenticated user; writes require manager/admin.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import AutoPauseRule, BlackoutDate, Limit, User
from ..enums import Role
from ..schemas import (
    AutoPauseRuleCreate,
    AutoPauseRuleOut,
    BlackoutCreate,
    BlackoutOut,
    LimitCreate,
    LimitOut,
)

router = APIRouter(prefix="/api", tags=["ad-limits"])

_MANAGERS = (Role.manager,)


# ---- Limits ----
@router.post("/limits", response_model=LimitOut, status_code=201)
def create_limit(
    body: LimitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> Limit:
    limit = Limit(
        scope=body.scope.value, scope_ref_id=body.scope_ref_id,
        scope_ref_value=body.scope_ref_value, metric=body.metric.value,
        value=body.value, cap_type=body.cap_type.value,
    )
    db.add(limit)
    db.flush()
    log_action(db, user=user, action="limit.create", entity_type="limit",
               entity_id=limit.id, detail={"metric": limit.metric, "value": limit.value})
    db.commit()
    db.refresh(limit)
    return limit


@router.get("/limits", response_model=list[LimitOut])
def list_limits(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Limit]:
    return db.query(Limit).order_by(Limit.scope, Limit.metric).all()


@router.delete("/limits/{limit_id}", status_code=204)
def delete_limit(
    limit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    limit = db.get(Limit, limit_id)
    if limit is None:
        raise HTTPException(status_code=404, detail="Limit not found.")
    log_action(db, user=user, action="limit.delete", entity_type="limit", entity_id=limit_id)
    db.delete(limit)
    db.commit()


# ---- Blackout dates ----
@router.post("/blackouts", response_model=BlackoutOut, status_code=201)
def create_blackout(
    body: BlackoutCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> BlackoutDate:
    if body.end_date < body.start_date:
        raise HTTPException(status_code=422, detail="end_date is before start_date.")
    bo = BlackoutDate(
        scope=body.scope.value, scope_ref_id=body.scope_ref_id,
        scope_ref_value=body.scope_ref_value, start_date=body.start_date,
        end_date=body.end_date, reason=body.reason,
    )
    db.add(bo)
    db.flush()
    log_action(db, user=user, action="blackout.create", entity_type="blackout", entity_id=bo.id)
    db.commit()
    db.refresh(bo)
    return bo


@router.get("/blackouts", response_model=list[BlackoutOut])
def list_blackouts(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[BlackoutDate]:
    return db.query(BlackoutDate).order_by(BlackoutDate.start_date).all()


@router.delete("/blackouts/{blackout_id}", status_code=204)
def delete_blackout(
    blackout_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    bo = db.get(BlackoutDate, blackout_id)
    if bo is None:
        raise HTTPException(status_code=404, detail="Blackout not found.")
    log_action(db, user=user, action="blackout.delete", entity_type="blackout", entity_id=blackout_id)
    db.delete(bo)
    db.commit()


# ---- Auto-pause rules ----
@router.post("/auto-pause-rules", response_model=AutoPauseRuleOut, status_code=201)
def create_rule(
    body: AutoPauseRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> AutoPauseRule:
    rule = AutoPauseRule(
        scope=body.scope.value, scope_ref_id=body.scope_ref_id,
        scope_ref_value=body.scope_ref_value, rule_type=body.rule_type.value,
        threshold=body.threshold, window_hours=body.window_hours,
        action=body.action.value, enabled=body.enabled,
    )
    db.add(rule)
    db.flush()
    log_action(db, user=user, action="auto_pause_rule.create",
               entity_type="auto_pause_rule", entity_id=rule.id,
               detail={"type": rule.rule_type, "threshold": rule.threshold})
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/auto-pause-rules", response_model=list[AutoPauseRuleOut])
def list_rules(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[AutoPauseRule]:
    return db.query(AutoPauseRule).order_by(AutoPauseRule.id).all()


@router.delete("/auto-pause-rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    rule = db.get(AutoPauseRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found.")
    log_action(db, user=user, action="auto_pause_rule.delete",
               entity_type="auto_pause_rule", entity_id=rule_id)
    db.delete(rule)
    db.commit()
