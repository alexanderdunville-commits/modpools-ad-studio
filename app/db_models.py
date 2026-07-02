"""SQLAlchemy ORM models — Phase 1 subset of the product-plan schema.

Covers users, campaigns, ads, approvals, and the audit log. Later phases add
schedules, budgets, limits, auto_pause_rules, metrics, etc. (see docs plan §7).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .enums import AdStatus, CampaignStatus


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
