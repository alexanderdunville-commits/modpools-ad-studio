"""Budget Manager tab: budgets + live spend-vs-budget.

Writes require manager/admin; the spend summary is open to any authenticated user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Budget, User
from ..engine import spend_for
from ..enums import Role
from ..schemas import BudgetCreate, BudgetOut

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

_MANAGERS = (Role.manager,)


@router.post("", response_model=BudgetOut, status_code=201)
def create_budget(
    body: BudgetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> Budget:
    budget = Budget(
        scope=body.scope.value, scope_ref_id=body.scope_ref_id,
        scope_ref_value=body.scope_ref_value, period=body.period.value,
        amount=body.amount, currency=body.currency, cap_type=body.cap_type.value,
    )
    db.add(budget)
    db.flush()
    log_action(db, user=user, action="budget.create", entity_type="budget",
               entity_id=budget.id, detail={"scope": budget.scope,
                                            "period": budget.period,
                                            "amount": budget.amount})
    db.commit()
    db.refresh(budget)
    return budget


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Budget]:
    return db.query(Budget).order_by(Budget.scope, Budget.period).all()


@router.delete("/{budget_id}", status_code=204)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found.")
    log_action(db, user=user, action="budget.delete", entity_type="budget", entity_id=budget_id)
    db.delete(budget)
    db.commit()


@router.get("/summary")
def budget_summary(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[dict]:
    """Spend vs. budget for every configured budget, this period."""
    out = []
    for b in db.query(Budget).all():
        spent = spend_for(
            db, scope=b.scope,
            campaign_id=b.scope_ref_id if b.scope == "campaign" else None,
            platform=b.scope_ref_value if b.scope == "platform" else None,
            period=b.period,
        )
        out.append({
            "budget_id": b.id, "scope": b.scope, "period": b.period,
            "scope_ref_id": b.scope_ref_id, "scope_ref_value": b.scope_ref_value,
            "amount": b.amount, "spent": round(spent, 2),
            "remaining": round(max(0.0, b.amount - spent), 2),
            "used_pct": round(100 * spent / b.amount, 1) if b.amount else 0.0,
            "cap_type": b.cap_type,
        })
    return out
