"""Status/role enums shared across the persistence and API layers.

Platform and Goal live in `app.models` (used by the generator); the enums here
describe the *lifecycle* of campaigns, ads, approvals, and users.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    creator = "creator"
    approver = "approver"
    analyst = "analyst"


class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class AdStatus(str, Enum):
    draft = "draft"
    pending = "pending"           # in the approval queue
    approved = "approved"
    rejected = "rejected"
    changes_requested = "changes_requested"
    scheduled = "scheduled"       # (Phase 2)
    live = "live"                 # (Phase 4)
    paused = "paused"
    completed = "completed"


class ApprovalDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"
    changes_requested = "changes_requested"


# Which ad statuses may transition to `pending` when a creator submits for review.
SUBMITTABLE = {AdStatus.draft, AdStatus.changes_requested, AdStatus.rejected}


class ScheduleStatus(str, Enum):
    queued = "queued"
    posting = "posting"
    posted = "posted"
    failed = "failed"
    canceled = "canceled"
    skipped = "skipped"       # blocked by a limit/budget/blackout at post time


class Scope(str, Enum):
    global_ = "global"
    platform = "platform"
    campaign = "campaign"
    ad = "ad"


class LimitMetric(str, Enum):
    max_ads_day = "max_ads_day"
    max_ads_week = "max_ads_week"
    max_ads_month = "max_ads_month"
    max_active_per_platform = "max_active_per_platform"
    min_gap_minutes = "min_gap_minutes"
    max_spend_day = "max_spend_day"
    max_spend_campaign = "max_spend_campaign"
    max_spend_platform = "max_spend_platform"


class CapType(str, Enum):
    soft = "soft"     # alert only
    hard = "hard"     # enforced — cannot exceed


class BudgetPeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    lifetime = "lifetime"


class AutoPauseRuleType(str, Enum):
    cpl = "cpl"                       # cost per lead too high
    budget = "budget"                # period spend reached budget
    frequency = "frequency"          # audience fatigue
    ctr = "ctr"                      # click-through collapsed
    zero_conversions = "zero_conversions"  # spend with no conversions


class AutoPauseAction(str, Enum):
    pause = "pause"
    alert = "alert"


class ConnectionMode(str, Enum):
    sandbox = "sandbox"   # uses the mock adapter — safe, no real spend
    live = "live"         # uses the real platform adapter (needs credentials)


class ConnectionStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    token_expiring = "token_expiring"
    error = "error"


class CreativeType(str, Enum):
    image = "image"
    video = "video"
    headline = "headline"
    caption = "caption"
    cta = "cta"
    testimonial = "testimonial"
    before_after = "before_after"
