"""Phase 3 — performance analysis (stub).

Scaffolding for pulling campaign metrics from your ad accounts and having Claude
recommend budget/copy changes. Feed `CampaignMetrics` into `analyze_campaigns`
and send them to the model with an analyst prompt.

See the Roadmap in the README.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Platform


@dataclass
class CampaignMetrics:
    """A single campaign's performance over a reporting window."""

    campaign_id: str
    platform: Platform
    impressions: int
    clicks: int
    spend: float
    conversions: int

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def cpa(self) -> float:
        return self.spend / self.conversions if self.conversions else 0.0


@dataclass
class Recommendation:
    """A written suggestion the model produced from the metrics."""

    campaign_id: str
    summary: str
    suggested_action: str


def analyze_campaigns(metrics: list[CampaignMetrics]) -> list[Recommendation]:
    """Send metrics to Claude with an analyst prompt and return recommendations.

    Not implemented yet. The intended flow: build a prompt summarizing the
    metrics, call the Claude API (reuse the client/settings from
    `app.config`), and parse structured budget/copy recommendations back out.
    """
    raise NotImplementedError(
        "analyze_campaigns is not implemented yet. Wire CampaignMetrics from your "
        "ad accounts into a Claude analyst prompt (see app/generator.py for the "
        "structured-output pattern)."
    )
