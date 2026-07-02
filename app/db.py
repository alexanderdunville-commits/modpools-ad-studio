"""Database engine, session, and startup.

Defaults to SQLite for local dev (a file next to the app); set `DATABASE_URL`
to a Postgres URL for production. Tables are created on startup via
`init_db()`. Production should move to Alembic migrations — see the product plan.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, future=True
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables (if missing) and seed the dev users. Idempotent."""
    from . import db_models  # noqa: F401  (register models on Base.metadata)

    Base.metadata.create_all(engine)
    _seed_dev_users()
    _seed_settings()


def _seed_dev_users() -> None:
    """Seed one user per role so RBAC is usable locally without an identity
    provider. In production, replace this with your SSO/user provisioning."""
    from .db_models import User
    from .enums import Role

    seed = [
        ("Admin", "admin@modpools.local", Role.admin),
        ("Marketing Manager", "manager@modpools.local", Role.manager),
        ("Ad Creator", "creator@modpools.local", Role.creator),
        ("Approver", "approver@modpools.local", Role.approver),
        ("Analyst", "analyst@modpools.local", Role.analyst),
    ]
    with SessionLocal() as db:
        if db.query(User).count() > 0:
            return
        db.add_all(
            [User(name=n, email=e, role=r.value) for n, e, r in seed]
        )
        db.commit()


def _seed_settings() -> None:
    from .db_models import Setting

    with SessionLocal() as db:
        if db.get(Setting, 1) is None:
            db.add(Setting(id=1, emergency_stop=False, company={},
                           notifications={}, api_keys_enc={}))
            db.commit()
