"""Audience Builder + Creative Library.

Saved audiences (luxury homeowners, Airbnb owners, compact-backyard buyers, …)
and reusable creative assets (images, videos, headlines, captions, CTAs,
testimonials, before/after). Writes require creator/manager; reads are open.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Audience, Creative, User
from ..enums import Role
from ..schemas import (
    AudienceCreate,
    AudienceOut,
    CreativeCreate,
    CreativeOut,
)

router = APIRouter(prefix="/api", tags=["library"])

_EDITORS = (Role.creator, Role.manager)


# ---- Audiences ----
@router.post("/audiences", response_model=AudienceOut, status_code=201)
def create_audience(
    body: AudienceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Audience:
    aud = Audience(**body.model_dump(), created_by=user.email)
    db.add(aud)
    db.flush()
    log_action(db, user=user, action="audience.create", entity_type="audience",
               entity_id=aud.id, detail={"name": aud.name})
    db.commit()
    db.refresh(aud)
    return aud


@router.get("/audiences", response_model=list[AudienceOut])
def list_audiences(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Audience]:
    return db.query(Audience).order_by(Audience.name).all()


@router.delete("/audiences/{audience_id}", status_code=204)
def delete_audience(
    audience_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> None:
    aud = db.get(Audience, audience_id)
    if aud is None:
        raise HTTPException(status_code=404, detail="Audience not found.")
    log_action(db, user=user, action="audience.delete", entity_type="audience", entity_id=audience_id)
    db.delete(aud)
    db.commit()


# ---- Creatives ----
@router.post("/creatives", response_model=CreativeOut, status_code=201)
def create_creative(
    body: CreativeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Creative:
    creative = Creative(
        type=body.type.value, name=body.name, url=body.url, body=body.body,
        tags=body.tags, aspect_ratio=body.aspect_ratio, created_by=user.email,
    )
    db.add(creative)
    db.flush()
    log_action(db, user=user, action="creative.create", entity_type="creative",
               entity_id=creative.id, detail={"type": creative.type})
    db.commit()
    db.refresh(creative)
    return creative


@router.get("/creatives", response_model=list[CreativeOut])
def list_creatives(
    type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Creative]:
    q = db.query(Creative)
    if type:
        q = q.filter(Creative.type == type)
    return q.order_by(Creative.created_at.desc()).all()


@router.post("/creatives/{creative_id}/approve", response_model=CreativeOut)
def approve_creative(
    creative_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Creative:
    creative = db.get(Creative, creative_id)
    if creative is None:
        raise HTTPException(status_code=404, detail="Creative not found.")
    creative.approved = True
    log_action(db, user=user, action="creative.approve", entity_type="creative", entity_id=creative_id)
    db.commit()
    db.refresh(creative)
    return creative


@router.delete("/creatives/{creative_id}", status_code=204)
def delete_creative(
    creative_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> None:
    creative = db.get(Creative, creative_id)
    if creative is None:
        raise HTTPException(status_code=404, detail="Creative not found.")
    log_action(db, user=user, action="creative.delete", entity_type="creative", entity_id=creative_id)
    db.delete(creative)
    db.commit()
