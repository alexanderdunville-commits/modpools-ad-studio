"""API request/response schemas for campaigns, ads, approvals, and audit.

Separate from `app.models` (which holds the generator's request/response types).
`*Out` models read directly from ORM objects (`from_attributes=True`).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import AdStatus, CampaignStatus
from .models import AdVariation, Platform


# ---------- Campaigns ----------
class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    brand: str = Field("modpools", max_length=100)
    offer: str | None = None
    market: str | None = Field(None, max_length=200)
    product_size: str | None = Field(None, max_length=100)
    season: str | None = Field(None, max_length=100)
    audience: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    offer: str | None = None
    market: str | None = Field(None, max_length=200)
    product_size: str | None = Field(None, max_length=100)
    season: str | None = Field(None, max_length=100)
    audience: str | None = None
    status: CampaignStatus | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str
    offer: str | None
    market: str | None
    product_size: str | None
    season: str | None
    audience: str | None
    status: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime


# ---------- Ads ----------
class AdCreate(BaseModel):
    platform: Platform
    headline: str
    primary_text: str
    description: str
    call_to_action: str
    hashtags: list[str] = Field(default_factory=list)
    visual_concept: str
    rationale: str | None = None


class AdUpdate(BaseModel):
    headline: str | None = None
    primary_text: str | None = None
    description: str | None = None
    call_to_action: str | None = None
    hashtags: list[str] | None = None
    visual_concept: str | None = None
    rationale: str | None = None


class SaveGeneratedAdsRequest(BaseModel):
    """Persist variations produced by the AI generator into a campaign."""

    platform: Platform
    variations: list[AdVariation] = Field(..., min_length=1, max_length=25)


class AdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    platform: str
    headline: str
    primary_text: str
    description: str
    call_to_action: str
    hashtags: list[str]
    visual_concept: str
    rationale: str | None
    status: str
    generated_by_ai: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime


# ---------- Approvals ----------
class ApprovalAction(BaseModel):
    comment: str | None = Field(None, max_length=2000)


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ad_id: int
    reviewer_email: str
    decision: str
    comment: str | None
    decided_at: datetime


# ---------- Audit ----------
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_email: str | None
    action: str
    entity_type: str
    entity_id: int | None
    detail: dict | None
    created_at: datetime
