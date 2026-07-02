"""Audit logging helper.

Every state-changing action (create/edit/submit/approve/reject/…) writes a row
so there's a who/when/what trail. Call `log_action` within the same session as
the change and commit once at the end of the route.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .db_models import AuditLog, User


def log_action(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_email=user.email if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )
