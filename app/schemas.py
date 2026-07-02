"""API request/response schemas for campaigns, ads, approvals, and audit.

Separate from `app.models` (which holds the generator's request/response types).
`*Out` models read directly from ORM objects (`from_attributes=True`).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    AutoPauseAction,
    AutoPauseRuleType,
    BudgetPeriod,
    CampaignStatus,
    CapType,
    ConnectionMode,
    CreativeType,
    LimitMetric,
    Scope,
    ScheduleStatus,
)
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


# ---------- Schedules ----------
class ScheduleCreate(BaseModel):
    ad_id: int
    scheduled_at: datetime
    note: str | None = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ad_id: int
    platform: str
    scheduled_at: datetime
    status: str
    posted_at: datetime | None
    external_post_id: str | None
    note: str | None
    created_by: str | None
    created_at: datetime


# ---------- Limits ----------
class LimitCreate(BaseModel):
    scope: Scope
    metric: LimitMetric
    value: float = Field(..., gt=0)
    scope_ref_id: int | None = None       # campaign id (scope=campaign)
    scope_ref_value: str | None = None    # platform (scope=platform)
    cap_type: CapType = CapType.hard


class LimitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    scope_ref_id: int | None
    scope_ref_value: str | None
    metric: str
    value: float
    cap_type: str
    created_at: datetime


# ---------- Budgets ----------
class BudgetCreate(BaseModel):
    scope: Scope
    period: BudgetPeriod
    amount: float = Field(..., gt=0)
    scope_ref_id: int | None = None
    scope_ref_value: str | None = None
    currency: str = "USD"
    cap_type: CapType = CapType.hard


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    scope_ref_id: int | None
    scope_ref_value: str | None
    period: str
    amount: float
    currency: str
    cap_type: str
    created_at: datetime


# ---------- Auto-pause rules ----------
class AutoPauseRuleCreate(BaseModel):
    rule_type: AutoPauseRuleType
    threshold: float = Field(..., gt=0)
    scope: Scope = Scope.global_
    scope_ref_id: int | None = None
    scope_ref_value: str | None = None
    window_hours: int = Field(24, ge=1, le=720)
    action: AutoPauseAction = AutoPauseAction.pause
    enabled: bool = True


class AutoPauseRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    scope_ref_id: int | None
    scope_ref_value: str | None
    rule_type: str
    threshold: float
    window_hours: int
    action: str
    enabled: bool
    created_at: datetime


# ---------- Blackout dates ----------
class BlackoutCreate(BaseModel):
    start_date: date
    end_date: date
    scope: Scope = Scope.global_
    scope_ref_id: int | None = None
    scope_ref_value: str | None = None
    reason: str | None = None


class BlackoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    scope_ref_id: int | None
    scope_ref_value: str | None
    start_date: date
    end_date: date
    reason: str | None
    created_at: datetime


# ---------- Audiences ----------
class AudienceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    source_type: str = "custom"
    geo: dict | None = None
    demographics: dict | None = None
    interests: list[str] | None = None
    platform_mappings: dict | None = None


class AudienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    source_type: str
    geo: dict | None
    demographics: dict | None
    interests: list[str] | None
    platform_mappings: dict | None
    created_by: str | None
    created_at: datetime


# ---------- Creatives ----------
class CreativeCreate(BaseModel):
    type: CreativeType
    name: str = Field(..., min_length=1, max_length=300)
    url: str | None = None
    body: str | None = None
    tags: list[str] = Field(default_factory=list)
    aspect_ratio: str | None = None


class CreativeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    name: str
    url: str | None
    body: str | None
    tags: list[str]
    aspect_ratio: str | None
    approved: bool
    created_by: str | None
    created_at: datetime


# ---------- Platform connections ----------
class ConnectionUpsert(BaseModel):
    platform: Platform
    account_name: str | None = None
    external_account_id: str | None = None
    access_token: str | None = None    # write-only; stored encrypted
    mode: ConnectionMode = ConnectionMode.sandbox
    scopes: list[str] = Field(default_factory=list)


class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    account_name: str | None
    external_account_id: str | None
    token_preview: str | None = None   # masked; never the real token
    mode: str
    status: str
    scopes: list[str]
    last_synced_at: datetime | None
    created_at: datetime


# ---------- Metrics / analytics ----------
class MetricIngest(BaseModel):
    ad_id: int
    date: date
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    spend: float = 0.0
    conversions: int = 0
    booked_calls: int = 0
    sales: int = 0
    revenue: float = 0.0
    frequency: float = 0.0


class KpiSummary(BaseModel):
    impressions: int
    clicks: int
    leads: int
    spend: float
    conversions: int
    booked_calls: int
    sales: int
    revenue: float
    ctr: float
    cpl: float
    conversion_rate: float
    roas: float


# ---------- Settings / notifications ----------
class EmergencyStopRequest(BaseModel):
    active: bool


class SettingsUpdate(BaseModel):
    company: dict | None = None
    notifications: dict | None = None


class SettingsOut(BaseModel):
    emergency_stop: bool
    company: dict
    notifications: dict
    api_keys: dict            # names -> masked previews
    updated_at: datetime


class ApiKeyUpsert(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    message: str
    entity_type: str | None
    entity_id: int | None
    read: bool
    created_at: datetime


class TickResult(BaseModel):
    poster: dict
    rule_engine: dict
