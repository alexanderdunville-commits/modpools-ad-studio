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
