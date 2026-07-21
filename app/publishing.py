"""Ad-platform publishing adapters.

One interface, one implementation per network. The **sandbox** adapter
(`MockAdapter`) simulates posting so the whole pipeline — scheduling, limit and
budget enforcement, posting, pausing — runs end-to-end without real ad accounts.
The real adapters (Meta, Google, TikTok, Pinterest, LinkedIn) are stubs behind
the same interface: implement each against its marketing API when you connect a
live account (each needs OAuth credentials + an ad-account ID).

`get_adapter(platform, mode)` returns the sandbox adapter for `mode="sandbox"`
and the real adapter for `mode="live"`.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .enums import ConnectionMode

if TYPE_CHECKING:  # avoid import cycle (db_models imports nothing from here)
    from .db_models import Ad, PlatformConnection


class PublishError(RuntimeError):
    """A live platform rejected or couldn't complete a publish/pause call.
    The message is safe to show in the schedule note / notifications."""


@dataclass
class PublishResult:
    external_post_id: str
    external_url: str | None = None


class PublishingAdapter(ABC):
    """Common interface every ad-platform adapter implements."""

    @abstractmethod
    def publish(self, ad: "Ad") -> PublishResult:
        """Create the ad on the platform. Returns the external post id."""

    @abstractmethod
    def pause(self, external_post_id: str) -> bool:
        """Pause a live ad on the platform."""

    @abstractmethod
    def resume(self, external_post_id: str) -> bool:
        """Resume a paused ad on the platform."""


class MockAdapter(PublishingAdapter):
    """Sandbox adapter — simulates posting/pausing. No real spend, no network."""

    def publish(self, ad: "Ad") -> PublishResult:
        ext = f"mock_{ad.platform}_{ad.id}_{uuid.uuid4().hex[:8]}"
        return PublishResult(external_post_id=ext, external_url=f"https://sandbox.local/{ext}")

    def pause(self, external_post_id: str) -> bool:
        return True

    def resume(self, external_post_id: str) -> bool:
        return True


class _RealAdapterStub(PublishingAdapter):
    """Base for not-yet-implemented live adapters."""

    api_name = "the platform"
    docs_url = ""

    def publish(self, ad: "Ad") -> PublishResult:
        raise NotImplementedError(
            f"Live posting for this platform is not implemented yet. Implement "
            f"against {self.api_name} ({self.docs_url}). Until then, keep the "
            f"connection in sandbox mode."
        )

    def pause(self, external_post_id: str) -> bool:
        raise NotImplementedError

    def resume(self, external_post_id: str) -> bool:
        raise NotImplementedError


class MetaAdapter(_RealAdapterStub):
    api_name = "the Meta Marketing API"
    docs_url = "https://developers.facebook.com/docs/marketing-apis/"


class GoogleAdsAdapter(_RealAdapterStub):
    api_name = "the Google Ads API (covers Search, Display, and YouTube)"
    docs_url = "https://developers.google.com/google-ads/api/docs"


# TikTok has a real implementation — see app/tiktok_api.py (imported lazily in
# get_adapter to avoid a circular import). This stub remains only as the
# fallback when no credentials are configured.
class TikTokAdapter(_RealAdapterStub):
    api_name = "the TikTok Marketing API"
    docs_url = "https://business-api.tiktok.com/portal/docs"


class PinterestAdapter(_RealAdapterStub):
    api_name = "the Pinterest Ads API"
    docs_url = "https://developers.pinterest.com/docs/api/v5/"


class LinkedInAdapter(_RealAdapterStub):
    api_name = "the LinkedIn Marketing API"
    docs_url = "https://learn.microsoft.com/linkedin/marketing/"


# platform value -> real adapter. YouTube is served by Google Ads (video campaigns).
_REAL_ADAPTERS: dict[str, type[PublishingAdapter]] = {
    "facebook": MetaAdapter,
    "instagram": MetaAdapter,
    "google_search": GoogleAdsAdapter,
    "google_display": GoogleAdsAdapter,
    "youtube": GoogleAdsAdapter,
    "tiktok": TikTokAdapter,
    "linkedin": LinkedInAdapter,
}


def get_adapter(
    platform: str,
    mode: str = ConnectionMode.sandbox.value,
    connection: "PlatformConnection | None" = None,
) -> PublishingAdapter:
    """Return the adapter for a platform. Sandbox mode always uses the mock.

    In live mode, platforms with a real implementation are constructed from the
    stored connection (decrypted token + account id + config). Platforms without
    one fall back to their stub, which fails with a clear "not implemented" note.
    """
    if mode != ConnectionMode.live.value:
        return MockAdapter()

    if connection is not None and connection.access_token_enc:
        from .security import decrypt  # local import: security has no deps on us

        if platform == "tiktok":
            from .tiktok_api import TikTokLiveAdapter  # lazy: avoid circular import

            return TikTokLiveAdapter(
                access_token=decrypt(connection.access_token_enc),
                advertiser_id=connection.external_account_id or "",
                config=connection.config or {},
            )
        if platform in ("facebook", "instagram"):
            from .meta_api import MetaLiveAdapter  # lazy: avoid circular import

            return MetaLiveAdapter(
                access_token=decrypt(connection.access_token_enc),
                ad_account_id=connection.external_account_id or "",
                config=connection.config or {},
            )

    adapter_cls = _REAL_ADAPTERS.get(platform)
    if adapter_cls is None:
        raise ValueError(f"No live adapter registered for platform '{platform}'.")
    return adapter_cls()
