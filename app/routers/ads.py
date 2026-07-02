"""Ad endpoints: manual create, list (filterable), get, edit, submit for
approval, and delete.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Ad, Campaign, User
from ..enums import SUBMITTABLE, AdStatus, Role
from ..models import Platform
from ..schemas import AdCreate, AdOut, AdUpdate

router = APIRouter(prefix="/api/ads", tags=["ads"])

_EDITORS = (Role.creator, Role.manager)
_MANAGERS = (Role.manager,)


def _get_ad(db: Session, ad_id: int) -> Ad:
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found.")
    return ad


@router.post("", response_model=AdOut, status_code=201)
def create_ad(
    body: AdCreate,
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Ad:
    if db.get(Campaign, campaign_id) is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    ad = Ad(
        campaign_id=campaign_id,
        platform=body.platform.value,
        headline=body.headline,
        primary_text=body.primary_text,
        description=body.description,
        call_to_action=body.call_to_action,
        hashtags=body.hashtags,
        visual_concept=body.visual_concept,
        rationale=body.rationale,
        status=AdStatus.draft.value,
        generated_by_ai=False,
        created_by=user.email,
    )
    db.add(ad)
    db.flush()
    log_action(db, user=user, action="ad.create", entity_type="ad", entity_id=ad.id)
    db.commit()
    db.refresh(ad)
    return ad


@router.get("", response_model=list[AdOut])
def list_ads(
    campaign_id: int | None = None,
    status: AdStatus | None = None,
    platform: Platform | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Ad]:
    q = db.query(Ad)
    if campaign_id is not None:
        q = q.filter(Ad.campaign_id == campaign_id)
    if status:
        q = q.filter(Ad.status == status.value)
    if platform:
        q = q.filter(Ad.platform == platform.value)
    return q.order_by(Ad.created_at.desc()).all()


@router.get("/{ad_id}", response_model=AdOut)
def get_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Ad:
    return _get_ad(db, ad_id)


@router.patch("/{ad_id}", response_model=AdOut)
def update_ad(
    ad_id: int,
    body: AdUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Ad:
    ad = _get_ad(db, ad_id)
    if ad.status not in {AdStatus.draft.value, AdStatus.changes_requested.value}:
        raise HTTPException(
            status_code=409,
            detail=f"Only draft or changes-requested ads can be edited (status: {ad.status}).",
        )
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(ad, key, value)
    log_action(db, user=user, action="ad.update", entity_type="ad",
               entity_id=ad.id, detail={"fields": list(changes)})
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/submit", response_model=AdOut)
def submit_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Ad:
    """Send a draft into the approval queue (status -> pending)."""
    ad = _get_ad(db, ad_id)
    if AdStatus(ad.status) not in SUBMITTABLE:
        raise HTTPException(
            status_code=409,
            detail=f"Ad cannot be submitted from status '{ad.status}'.",
        )
    ad.status = AdStatus.pending.value
    log_action(db, user=user, action="ad.submit", entity_type="ad", entity_id=ad.id)
    db.commit()
    db.refresh(ad)
    return ad


@router.delete("/{ad_id}", status_code=204)
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    ad = _get_ad(db, ad_id)
    log_action(db, user=user, action="ad.delete", entity_type="ad", entity_id=ad.id)
    db.delete(ad)
    db.commit()
