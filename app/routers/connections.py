"""Platform Connections tab.

Store one connection per platform. Access tokens are encrypted at rest and never
returned — reads show a masked preview only. Connections default to `sandbox`
mode (mock adapter, no real spend); switch to `live` once a real adapter is
implemented and credentials are provided.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import PlatformConnection, User
from ..enums import ConnectionStatus, Role
from ..publishing import PublishError
from ..schemas import ConnectionOut, ConnectionUpsert
from ..security import decrypt, encrypt, mask

router = APIRouter(prefix="/api/connections", tags=["connections"])

_MANAGERS = (Role.manager,)


def _to_out(conn: PlatformConnection) -> ConnectionOut:
    token = decrypt(conn.access_token_enc) if conn.access_token_enc else None
    return ConnectionOut(
        id=conn.id, platform=conn.platform, account_name=conn.account_name,
        external_account_id=conn.external_account_id, token_preview=mask(token),
        mode=conn.mode, status=conn.status, scopes=conn.scopes,
        config=conn.config, last_synced_at=conn.last_synced_at,
        created_at=conn.created_at,
    )


@router.put("", response_model=ConnectionOut)
def upsert_connection(
    body: ConnectionUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> ConnectionOut:
    conn = db.query(PlatformConnection).filter(
        PlatformConnection.platform == body.platform.value
    ).first()
    if conn is None:
        conn = PlatformConnection(platform=body.platform.value)
        db.add(conn)
    conn.account_name = body.account_name
    conn.external_account_id = body.external_account_id
    conn.mode = body.mode.value
    conn.scopes = body.scopes
    if body.config is not None:
        conn.config = body.config
    if body.access_token:
        conn.access_token_enc = encrypt(body.access_token)
        conn.status = ConnectionStatus.connected.value
    elif conn.access_token_enc is None:
        conn.status = ConnectionStatus.disconnected.value
    db.flush()
    log_action(db, user=user, action="connection.upsert", entity_type="connection",
               entity_id=conn.id, detail={"platform": conn.platform, "mode": conn.mode})
    db.commit()
    db.refresh(conn)
    return _to_out(conn)


@router.get("", response_model=list[ConnectionOut])
def list_connections(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[ConnectionOut]:
    return [_to_out(c) for c in db.query(PlatformConnection).order_by(
        PlatformConnection.platform).all()]


@router.post("/{platform}/test")
def test_connection(
    platform: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> dict:
    """Verify stored credentials against the real platform API (works while
    still in sandbox mode — test first, then flip to live)."""
    conn = db.query(PlatformConnection).filter(
        PlatformConnection.platform == platform
    ).first()
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found.")
    if platform != "tiktok":
        raise HTTPException(
            status_code=400,
            detail="Connection testing is only implemented for TikTok so far.",
        )
    if not conn.access_token_enc:
        raise HTTPException(status_code=400, detail="No access token saved yet.")

    from ..tiktok_api import TikTokLiveAdapter

    try:
        adapter = TikTokLiveAdapter(
            access_token=decrypt(conn.access_token_enc),
            advertiser_id=conn.external_account_id or "",
            config=conn.config or {},
        )
        info = adapter.test()
    except PublishError as exc:
        conn.status = ConnectionStatus.error.value
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    conn.status = ConnectionStatus.connected.value
    conn.last_synced_at = datetime.utcnow()
    log_action(db, user=user, action="connection.test", entity_type="connection",
               entity_id=conn.id, detail={"platform": platform, "ok": True})
    db.commit()
    return {"ok": True, "advertiser": info}


@router.delete("/{platform}", status_code=204)
def disconnect(
    platform: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    conn = db.query(PlatformConnection).filter(
        PlatformConnection.platform == platform
    ).first()
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found.")
    log_action(db, user=user, action="connection.delete", entity_type="connection", entity_id=conn.id)
    db.delete(conn)
    db.commit()
