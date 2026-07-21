"""SQLAlchemy ORM models — Phase 1 subset of the product-plan schema.

Covers users, campaigns, ads, approvals, and the audit log. Later phases add
schedules, budgets, limits, auto_pause_rules, metrics, etc. (see docs plan §7).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .enums import (
    AdStatus,
    BudgetPeriod,
    CampaignStatus,
    CapType,
    ConnectionMode,
    ConnectionStatus,
    ScheduleStatus,
)


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    brand: Mapped[str] = mapped_column(String(100), default="modpools")
    offer: Mapped[str | None] = mapped_column(Text, default=None)
    market: Mapped[str | None] = mapped_column(String(200), default=None)
    product_size: Mapped[str | None] = mapped_column(String(100), default=None)
    season: Mapped[str | None] = mapped_column(String(100), default=None)
    audience: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(50), default=CampaignStatus.draft.value)
    created_by: Mapped[str | None] = mapped_column(String(320), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    ads: Mapped[list["Ad"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Ad(Base):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50))
    headline: Mapped[str] = mapped_column(Text)
    primary_text: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    call_to_action: Mapped[str] = mapped_column(String(200))
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    visual_concept: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, default=None)
    # Platform media asset reference — for TikTok this is the video_id from the
    # advertiser's asset library (in-feed TikTok ads must have a video).
    media_ref: Mapped[str | None] = mapped_column(String(200), default=None)
    status: Mapped[str] = mapped_column(String(50), default=AdStatus.draft.value)
    generated_by_ai: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[str | None] = mapped_column(String(320), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="ads")
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="ad", cascade="all, delete-orphan"
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), index=True
    )
    reviewer_email: Mapped[str] = mapped_column(String(320))
    decision: Mapped[str] = mapped_column(String(50))
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    ad: Mapped["Ad"] = relationship(back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str | None] = mapped_column(String(320), default=None)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(default=None)
    detail: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Audience(Base):
    __tablename__ = "audiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    source_type: Mapped[str] = mapped_column(String(50), default="custom")
    geo: Mapped[dict | None] = mapped_column(JSON, default=None)
    demographics: Mapped[dict | None] = mapped_column(JSON, default=None)
    interests: Mapped[list | None] = mapped_column(JSON, default=None)
    platform_mappings: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_by: Mapped[str | None] = mapped_column(String(320), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Creative(Base):
    __tablename__ = "creatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(Text, default=None)      # image/video asset
    body: Mapped[str | None] = mapped_column(Text, default=None)     # text asset
    tags: Mapped[list] = mapped_column(JSON, default=list)
    aspect_ratio: Mapped[str | None] = mapped_column(String(20), default=None)
    approved: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[str | None] = mapped_column(String(320), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PlatformConnection(Base):
    __tablename__ = "platform_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    account_name: Mapped[str | None] = mapped_column(String(200), default=None)
    external_account_id: Mapped[str | None] = mapped_column(String(200), default=None)
    access_token_enc: Mapped[str | None] = mapped_column(Text, default=None)
    mode: Mapped[str] = mapped_column(String(20), default=ConnectionMode.sandbox.value)
    status: Mapped[str] = mapped_column(
        String(30), default=ConnectionStatus.disconnected.value
    )
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    # Per-platform live-posting settings (non-secret). TikTok uses:
    # adgroup_id, identity_id, identity_type, landing_page_url, display_name.
    config: Mapped[dict | None] = mapped_column(JSON, default=None)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(50))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default=ScheduleStatus.queued.value
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    external_post_id: Mapped[str | None] = mapped_column(String(200), default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[str | None] = mapped_column(String(320), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Limit(Base):
    __tablename__ = "limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20))              # global/platform/campaign
    scope_ref_id: Mapped[int | None] = mapped_column(default=None)  # campaign id, or null
    scope_ref_value: Mapped[str | None] = mapped_column(String(50), default=None)  # platform name
    metric: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    cap_type: Mapped[str] = mapped_column(String(10), default=CapType.hard.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20))
    scope_ref_id: Mapped[int | None] = mapped_column(default=None)
    scope_ref_value: Mapped[str | None] = mapped_column(String(50), default=None)
    period: Mapped[str] = mapped_column(String(20), default=BudgetPeriod.daily.value)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    cap_type: Mapped[str] = mapped_column(String(10), default=CapType.hard.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AutoPauseRule(Base):
    __tablename__ = "auto_pause_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), default="global")
    scope_ref_id: Mapped[int | None] = mapped_column(default=None)
    scope_ref_value: Mapped[str | None] = mapped_column(String(50), default=None)
    rule_type: Mapped[str] = mapped_column(String(30))
    threshold: Mapped[float] = mapped_column(Float)
    window_hours: Mapped[int] = mapped_column(Integer, default=24)
    action: Mapped[str] = mapped_column(String(10), default="pause")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class BlackoutDate(Base):
    __tablename__ = "blackout_dates"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), default="global")
    scope_ref_id: Mapped[int | None] = mapped_column(default=None)
    scope_ref_value: Mapped[str | None] = mapped_column(String(50), default=None)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(300), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad_id: Mapped[int] = mapped_column(
        ForeignKey("ads.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    booked_calls: Mapped[int] = mapped_column(Integer, default=0)
    sales: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[float] = mapped_column(Float, default=0.0)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(50), default=None)
    entity_id: Mapped[int | None] = mapped_column(default=None)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Setting(Base):
    """Single-row app settings (id is always 1)."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    emergency_stop: Mapped[bool] = mapped_column(default=False)
    company: Mapped[dict] = mapped_column(JSON, default=dict)
    notifications: Mapped[dict] = mapped_column(JSON, default=dict)
    api_keys_enc: Mapped[dict] = mapped_column(JSON, default=dict)  # {name: encrypted}
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
