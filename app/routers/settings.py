"""Settings tab + the Emergency Stop + the engine tick + notifications.

- Emergency Stop: one switch that pauses every live ad and blocks new posting.
- API keys: stored encrypted; listed as masked previews only.
- Engine tick: runs the poster + rule engine once (in production these run on a
  schedule; this endpoint lets you drive/verify them manually). Admin only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Notification, Setting, User
from ..engine import (
    activate_emergency_stop,
    clear_emergency_stop,
    get_setting,
    run_poster,
    run_rule_engine,
)
from ..enums import Role
from ..schemas import (
    ApiKeyUpsert,
    EmergencyStopRequest,
    NotificationOut,
    SettingsOut,
    SettingsUpdate,
    TickResult,
)
from ..security import encrypt, mask

router = APIRouter(prefix="/api", tags=["settings"])

_MANAGERS = (Role.manager,)
_ADMIN = ()  # require_roles always allows admin; empty extra roles = admin-only


def _to_out(s: Setting) -> SettingsOut:
    return SettingsOut(
        emergency_stop=s.emergency_stop, company=s.company or {},
        notifications=s.notifications or {},
        api_keys={name: mask("x" * 8 + name) for name in (s.api_keys_enc or {})},
        updated_at=s.updated_at,
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings_route(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> SettingsOut:
    return _to_out(get_setting(db))


@router.patch("/settings", response_model=SettingsOut)
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> SettingsOut:
    s = get_setting(db)
    if body.company is not None:
        s.company = body.company
    if body.notifications is not None:
        s.notifications = body.notifications
    log_action(db, user=user, action="settings.update", entity_type="settings", entity_id=1)
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.put("/settings/api-keys", response_model=SettingsOut)
def upsert_api_key(
    body: ApiKeyUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> SettingsOut:
    s = get_setting(db)
    keys = dict(s.api_keys_enc or {})
    keys[body.name] = encrypt(body.value)
    s.api_keys_enc = keys
    log_action(db, user=user, action="settings.api_key_set", entity_type="settings",
               entity_id=1, detail={"name": body.name})
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.post("/settings/emergency-stop", response_model=SettingsOut)
def emergency_stop(
    body: EmergencyStopRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> SettingsOut:
    if body.active:
        count = activate_emergency_stop(db)
        log_action(db, user=user, action="emergency_stop.activate",
                   entity_type="settings", entity_id=1, detail={"paused": count})
    else:
        clear_emergency_stop(db)
        log_action(db, user=user, action="emergency_stop.clear",
                   entity_type="settings", entity_id=1)
    db.commit()
    return _to_out(get_setting(db))


@router.post("/engine/tick", response_model=TickResult)
def engine_tick(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
) -> TickResult:
    """Run the poster then the rule engine once (production: scheduled worker)."""
    poster = run_poster(db)
    rules = run_rule_engine(db)
    return TickResult(poster=poster, rule_engine=rules)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Notification]:
    q = db.query(Notification)
    if unread_only:
        q = q.filter(Notification.read.is_(False))
    return q.order_by(Notification.created_at.desc()).limit(max(1, min(limit, 500))).all()
