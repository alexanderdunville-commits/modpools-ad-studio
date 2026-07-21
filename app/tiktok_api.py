"""Live TikTok Marketing API adapter (v1.3).

Talks to https://business-api.tiktok.com. Requires a TikTok for Business
account with an approved Marketing API app. The connection provides:

- ``access_token``        — long-lived token from the approved app (encrypted at rest)
- ``external_account_id`` — the numeric TikTok **advertiser ID**
- ``config.adgroup_id``   — the ad group new ads are created inside (campaign
  + ad group are created once in TikTok Ads Manager; this app posts ads into it)
- ``config.identity_id``  — the posting identity (the TikTok account the ad
  appears to come from); ``config.identity_type`` defaults to CUSTOMIZED_USER
- ``config.landing_page_url`` — default click-through URL
- ``config.display_name`` — brand name shown on the ad

Each ad must carry a TikTok **video_id** in ``ad.media_ref`` — TikTok in-feed
ads are video-only, and the video must first be uploaded to the advertiser's
TikTok asset library (Ads Manager → Assets → Videos, or the video upload API).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from .publishing import PublishError, PublishingAdapter, PublishResult

if TYPE_CHECKING:
    from .db_models import Ad

_BASE = "https://business-api.tiktok.com/open_api/v1.3"
_TIMEOUT = 30.0

# TikTok wants an enum CTA, our ads store free text. Map the common phrasings;
# anything unrecognized falls back to LEARN_MORE.
_CTA_MAP = {
    "learn more": "LEARN_MORE",
    "shop now": "SHOP_NOW",
    "sign up": "SIGN_UP",
    "signup": "SIGN_UP",
    "contact us": "CONTACT_US",
    "contact": "CONTACT_US",
    "apply now": "APPLY_NOW",
    "book now": "BOOK_NOW",
    "get quote": "GET_QUOTE",
    "get a quote": "GET_QUOTE",
    "request a quote": "GET_QUOTE",
    "download": "DOWNLOAD_NOW",
    "download now": "DOWNLOAD_NOW",
    "subscribe": "SUBSCRIBE",
    "order now": "ORDER_NOW",
    "get started": "GET_STARTED",
    "visit store": "VISIT_STORE",
    "watch now": "WATCH_NOW",
}

# TikTok in-feed ad_text is limited (emoji/spec caveats aside, ~100 chars is
# the safe ceiling). Truncate on a word boundary rather than failing the post.
_AD_TEXT_MAX = 100


def map_cta(free_text: str | None) -> str:
    if not free_text:
        return "LEARN_MORE"
    return _CTA_MAP.get(free_text.strip().lower(), "LEARN_MORE")


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


class TikTokLiveAdapter(PublishingAdapter):
    """Real posting to TikTok. Raises ``PublishError`` with TikTok's own
    message when the API rejects a call, so the schedule row shows the true
    reason."""

    def __init__(
        self,
        *,
        access_token: str,
        advertiser_id: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not access_token:
            raise PublishError(
                "TikTok connection has no access token. Add it on the "
                "Connections screen."
            )
        if not advertiser_id:
            raise PublishError(
                "TikTok connection has no advertiser ID. Put your numeric "
                "TikTok advertiser ID in the Account ID field."
            )
        self._token = access_token
        self._advertiser_id = str(advertiser_id)
        self._config = config or {}

    # ------------------------------------------------------------- plumbing
    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        headers = {"Access-Token": self._token, "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                if method == "GET":
                    resp = client.get(f"{_BASE}{path}", headers=headers,
                                      params=payload or {})
                else:
                    resp = client.post(f"{_BASE}{path}", headers=headers,
                                       json=payload or {})
        except httpx.HTTPError as exc:
            raise PublishError(f"Could not reach the TikTok API: {exc}") from exc

        try:
            body = resp.json()
        except ValueError as exc:
            raise PublishError(
                f"TikTok API returned a non-JSON response (HTTP {resp.status_code})."
            ) from exc

        # TikTok wraps everything: code 0 = success, anything else is an error.
        if body.get("code") != 0:
            raise PublishError(
                f"TikTok API error {body.get('code')}: {body.get('message', 'unknown')}"
            )
        return body.get("data") or {}

    def _require(self, key: str, hint: str) -> str:
        value = str(self._config.get(key) or "").strip()
        if not value:
            raise PublishError(
                f"TikTok connection is missing '{key}'. {hint}"
            )
        return value

    # ------------------------------------------------------------- interface
    def publish(self, ad: "Ad") -> PublishResult:
        video_id = (getattr(ad, "media_ref", None) or "").strip()
        if not video_id:
            raise PublishError(
                "This ad has no TikTok video attached. Upload the video to "
                "your TikTok asset library, then paste its video ID into the "
                "ad's Video/Media ID field."
            )
        adgroup_id = self._require(
            "adgroup_id",
            "Create a campaign + ad group in TikTok Ads Manager and paste the "
            "ad group ID into the connection settings.",
        )
        identity_id = self._require(
            "identity_id",
            "Set the posting identity ID (TikTok Ads Manager → Assets → "
            "Identity) in the connection settings.",
        )
        identity_type = str(
            self._config.get("identity_type") or "CUSTOMIZED_USER"
        ).strip()
        landing = str(
            self._config.get("landing_page_url") or "https://modpools.com"
        ).strip()
        display_name = str(
            self._config.get("display_name") or "Modpools"
        ).strip()

        creative = {
            "ad_name": _clip(f"ad-{ad.id}-{ad.headline}", 100),
            "identity_type": identity_type,
            "identity_id": identity_id,
            "ad_format": "SINGLE_VIDEO",
            "video_id": video_id,
            "ad_text": _clip(ad.primary_text or ad.headline, _AD_TEXT_MAX),
            "call_to_action": map_cta(ad.call_to_action),
            "landing_page_url": landing,
            "display_name": display_name,
        }
        data = self._call("POST", "/ad/create/", {
            "advertiser_id": self._advertiser_id,
            "adgroup_id": adgroup_id,
            "creatives": [creative],
        })

        ad_ids = data.get("ad_ids") or [
            c.get("ad_id") for c in data.get("creatives", []) if c.get("ad_id")
        ]
        if not ad_ids:
            raise PublishError("TikTok accepted the call but returned no ad ID.")
        ext = str(ad_ids[0])
        return PublishResult(
            external_post_id=ext,
            external_url=f"https://ads.tiktok.com/i18n/perf/creative?aadvid={self._advertiser_id}",
        )

    def _set_status(self, external_post_id: str, operation: str) -> bool:
        self._call("POST", "/ad/status/update/", {
            "advertiser_id": self._advertiser_id,
            "ad_ids": [str(external_post_id)],
            "operation_status": operation,
        })
        return True

    def pause(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "DISABLE")

    def resume(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "ENABLE")

    # ------------------------------------------------------------- test
    def test(self) -> dict:
        """Verify the token + advertiser ID by fetching advertiser info."""
        data = self._call("GET", "/advertiser/info/", {
            "advertiser_ids": json.dumps([self._advertiser_id]),
        })
        rows = data.get("list") or []
        if not rows:
            raise PublishError(
                "Token works but advertiser ID was not found on this account."
            )
        info = rows[0]
        return {
            "advertiser_id": str(info.get("advertiser_id", self._advertiser_id)),
            "name": info.get("name") or info.get("advertiser_name"),
            "status": info.get("status"),
            "currency": info.get("currency"),
            "timezone": info.get("timezone"),
        }
