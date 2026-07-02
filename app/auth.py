"""Authentication + role-based access control.

Dev shim: the current user is chosen by an `X-User-Email` header, defaulting to
the seeded admin. This lets RBAC be exercised locally without an identity
provider. In production, replace `get_current_user` with real SSO/JWT resolution
— every route already depends on it, so nothing else changes.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import User
from .enums import Role

DEV_DEFAULT_EMAIL = "admin@modpools.local"


def get_current_user(
    x_user_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    email = (x_user_email or DEV_DEFAULT_EMAIL).strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail=f"Unknown user '{email}'.")
    return user


def require_roles(*roles: Role):
    """Dependency factory — allow only the given roles. Admin always passes."""
    allowed = {r.value for r in roles} | {Role.admin.value}

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {', '.join(sorted(allowed))} (you are '{user.role}').",
            )
        return user

    return _dep
