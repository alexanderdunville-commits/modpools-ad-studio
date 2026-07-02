"""Campaign endpoints: create, list (filterable), get, update, archive, and
save AI-generated variations into a campaign as draft ads.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..db import get_db
from ..db_models import Ad, Campaign, User
from ..enums import AdStatus, CampaignStatus, Role
from ..schemas import (
    AdOut,
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    SaveGeneratedAdsRequest,
)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

_EDITORS = (Role.creator, Role.manager)  # + admin (added by require_roles)
_MANAGERS = (Role.manager,)


def _get_campaign(db: Session, campaign_id: int) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Campaign:
    campaign = Campaign(**body.model_dump(), created_by=user.email)
    db.add(campaign)
    db.flush()
    log_action(db, user=user, action="campaign.create",
               entity_type="campaign", entity_id=campaign.id,
               detail={"name": campaign.name})
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    status: CampaignStatus | None = None,
    brand: str | None = None,
    season: str | None = None,
    market: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Campaign]:
    q = db.query(Campaign)
    if status:
        q = q.filter(Campaign.status == status.value)
    if brand:
        q = q.filter(Campaign.brand == brand)
    if season:
        q = q.filter(Campaign.season == season)
    if market:
        q = q.filter(Campaign.market == market)
    return q.order_by(Campaign.created_at.desc()).all()


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Campaign:
    return _get_campaign(db, campaign_id)


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Campaign:
    campaign = _get_campaign(db, campaign_id)
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] is not None:
        changes["status"] = changes["status"].value
    for key, value in changes.items():
        setattr(campaign, key, value)
    log_action(db, user=user, action="campaign.update",
               entity_type="campaign", entity_id=campaign.id, detail=changes)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/archive", response_model=CampaignOut)
def archive_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> Campaign:
    campaign = _get_campaign(db, campaign_id)
    campaign.status = CampaignStatus.archived.value
    log_action(db, user=user, action="campaign.archive",
               entity_type="campaign", entity_id=campaign.id)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post(
    "/{campaign_id}/ads/from-generation",
    response_model=list[AdOut],
    status_code=201,
)
def save_generated_ads(
    campaign_id: int,
    body: SaveGeneratedAdsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> list[Ad]:
    """Persist AI-generated variations into this campaign as draft ads."""
    campaign = _get_campaign(db, campaign_id)
    ads: list[Ad] = []
    for v in body.variations:
        ad = Ad(
            campaign_id=campaign.id,
            platform=body.platform.value,
            headline=v.headline,
            primary_text=v.primary_text,
            description=v.description,
            call_to_action=v.call_to_action,
            hashtags=v.hashtags,
            visual_concept=v.visual_concept,
            rationale=v.rationale,
            status=AdStatus.draft.value,
            generated_by_ai=True,
            created_by=user.email,
        )
        db.add(ad)
        ads.append(ad)
    db.flush()
    log_action(db, user=user, action="ad.save_generated",
               entity_type="campaign", entity_id=campaign.id,
               detail={"count": len(ads), "platform": body.platform.value})
    db.commit()
    for ad in ads:
        db.refresh(ad)
    return ads
