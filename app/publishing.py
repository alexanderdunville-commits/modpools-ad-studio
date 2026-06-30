"""Phase 2 — ad-platform publishing (stub adapters).

Scaffolding for pushing generated campaigns to Meta (Facebook/Instagram) and
Google Ads. The adapter interface is defined; the `publish()` methods are not
implemented yet. To build this out, implement each `publish()` against the
relevant marketing API — each needs OAuth credentials and an ad-account ID.

See the Roadmap in the README.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import AdVariation, Platform


@dataclass
class PublishResult:
    """Returned by a successful publish — what the platform created."""

    platform: Platform
    campaign_id: str
    external_url: str | None = None


class PublishingAdapter(ABC):
    """Common interface every ad-platform adapter implements."""

    #: Platforms this adapter can publish to.
    platforms: tuple[Platform, ...] = ()

    def __init__(self, *, access_token: str, ad_account_id: str) -> None:
        self.access_token = access_token
        self.ad_account_id = ad_account_id

    @abstractmethod
    def publish(
        self, *, variation: AdVariation, platform: Platform, campaign_name: str
    ) -> PublishResult:
        """Create a campaign/ad from a generated variation. Returns the result."""


class MetaAdapter(PublishingAdapter):
    """Facebook + Instagram via the Meta Marketing API."""

    platforms = (Platform.facebook, Platform.instagram)

    def publish(
        self, *, variation: AdVariation, platform: Platform, campaign_name: str
    ) -> PublishResult:
        raise NotImplementedError(
            "MetaAdapter.publish is not implemented yet. Implement it against the "
            "Meta Marketing API (https://developers.facebook.com/docs/marketing-apis/)."
        )


class GoogleAdsAdapter(PublishingAdapter):
    """Google Search + Display via the Google Ads API."""

    platforms = (Platform.google_search, Platform.google_display)

    def publish(
        self, *, variation: AdVariation, platform: Platform, campaign_name: str
    ) -> PublishResult:
        raise NotImplementedError(
            "GoogleAdsAdapter.publish is not implemented yet. Implement it against "
            "the Google Ads API (https://developers.google.com/google-ads/api/docs)."
        )


def adapter_for(platform: Platform, **credentials: str) -> PublishingAdapter:
    """Return the adapter that handles `platform`, constructed with credentials."""
    for adapter_cls in (MetaAdapter, GoogleAdsAdapter):
        if platform in adapter_cls.platforms:
            return adapter_cls(**credentials)  # type: ignore[arg-type]
    raise ValueError(f"No publishing adapter for platform '{platform}'.")
