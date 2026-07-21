"""Live Meta (Facebook + Instagram) Marketing API adapter.

Talks to the Facebook Graph API. Facebook and Instagram are the same
integration — one Meta ad account serves both; Instagram placement is added
when an Instagram actor id is configured. Requires a Meta Business account with
an approved Marketing API app. The connection provides:

- ``access_token``        — a long-lived System User / page token (encrypted)
- ``external_account_id`` — the ad account id (``act_1234`` or just ``1234``)
- ``config.page_id``      — the Facebook Page the ad is published from (required)
- ``config.adset_id``     — the ad set new ads are created inside (campaign +
  ad set are built once in Ads Manager; this app posts ads into the ad set)
- ``config.instagram_actor_id`` — optional, to also run on Instagram
- ``config.landing_page_url``   — default click-through URL

An image is optional: set ``ad.media_ref`` to a Meta **image hash** (uploaded
to the ad account's image library) to control the creative; without one Meta
pulls a preview image from the landing page.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from .publishing import PublishError, PublishingAdapter, PublishResult

if TYPE_CHECKING:
    from .db_models import Ad

_API_VERSION = "v21.0"
_BASE = f"https://graph.facebook.com/{_API_VERSION}"
_TIMEOUT = 30.0

# Meta call_to_action is an enum; our ads store free text.
_CTA_MAP = {
    "learn more": "LEARN_MORE",
    "shop now": "SHOP_NOW",
    "sign up": "SIGN_UP",
    "signup": "SIGN_UP",
    "contact us": "CONTACT_US",
    "contact": "CONTACT_US",
    "get quote": "GET_QUOTE",
    "get a quote": "GET_QUOTE",
    "request a quote": "GET_QUOTE",
    "book now": "BOOK_TRAVEL",
    "apply now": "APPLY_NOW",
    "download": "DOWNLOAD",
    "subscribe": "SUBSCRIBE",
    "order now": "ORDER_NOW",
    "get offer": "GET_OFFER",
    "get started": "GET_STARTED",
    "call now": "CALL_NOW",
    "message": "MESSAGE_PAGE",
}


def map_cta(free_text: str | None) -> str:
    if not free_text:
        return "LEARN_MORE"
    return _CTA_MAP.get(free_text.strip().lower(), "LEARN_MORE")


def _normalize_account(raw: str) -> str:
    raw = str(raw).strip()
    return raw if raw.startswith("act_") else f"act_{raw}"


class MetaLiveAdapter(PublishingAdapter):
    """Real posting to Facebook + Instagram. Raises ``PublishError`` with
    Meta's own message when the Graph API rejects a call."""

    def __init__(
        self,
        *,
        access_token: str,
        ad_account_id: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not access_token:
            raise PublishError(
                "Meta connection has no access token. Add it on the "
                "Connections screen."
            )
        if not ad_account_id:
            raise PublishError(
                "Meta connection has no ad account ID. Put your ad account ID "
                "(act_… or the number) in the Account ID field."
            )
        self._token = access_token
        self._account = _normalize_account(ad_account_id)
        self._config = config or {}

    # ------------------------------------------------------------- plumbing
    def _call(self, method: str, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["access_token"] = self._token
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                if method == "GET":
                    resp = client.get(f"{_BASE}{path}", params=params)
                else:
                    resp = client.post(f"{_BASE}{path}", data=params)
        except httpx.HTTPError as exc:
            raise PublishError(f"Could not reach the Meta API: {exc}") from exc

        try:
            body = resp.json()
        except ValueError as exc:
            raise PublishError(
                f"Meta API returned a non-JSON response (HTTP {resp.status_code})."
            ) from exc

        if isinstance(body, dict) and body.get("error"):
            err = body["error"]
            raise PublishError(
                f"Meta API error {err.get('code')}: {err.get('message', 'unknown')}"
            )
        if resp.status_code >= 400:
            raise PublishError(f"Meta API HTTP {resp.status_code}.")
        return body

    def _require(self, key: str, hint: str) -> str:
        value = str(self._config.get(key) or "").strip()
        if not value:
            raise PublishError(f"Meta connection is missing '{key}'. {hint}")
        return value

    # ------------------------------------------------------------- interface
    def publish(self, ad: "Ad") -> PublishResult:
        page_id = self._require(
            "page_id",
            "Set the Facebook Page ID the ads publish from in the connection "
            "settings.",
        )
        adset_id = self._require(
            "adset_id",
            "Create a campaign + ad set in Meta Ads Manager and paste the ad "
            "set ID into the connection settings.",
        )
        landing = str(
            self._config.get("landing_page_url") or "https://modpools.com"
        ).strip()

        link_data: dict[str, Any] = {
            "message": ad.primary_text or ad.headline,
            "link": landing,
            "name": ad.headline,
            "description": ad.description or "",
            "call_to_action": {
                "type": map_cta(ad.call_to_action),
                "value": {"link": landing},
            },
        }
        image_hash = (getattr(ad, "media_ref", None) or "").strip()
        if image_hash:
            link_data["image_hash"] = image_hash

        story_spec: dict[str, Any] = {"page_id": page_id, "link_data": link_data}
        ig_actor = str(self._config.get("instagram_actor_id") or "").strip()
        if ig_actor:
            story_spec["instagram_actor_id"] = ig_actor

        creative = self._call("POST", f"/{self._account}/adcreatives", {
            "name": f"modpools-ad-{ad.id}",
            "object_story_spec": json.dumps(story_spec),
        })
        creative_id = creative.get("id")
        if not creative_id:
            raise PublishError("Meta did not return a creative ID.")

        result = self._call("POST", f"/{self._account}/ads", {
            "name": f"modpools-ad-{ad.id}",
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "ACTIVE",
        })
        ad_id = result.get("id")
        if not ad_id:
            raise PublishError("Meta accepted the creative but returned no ad ID.")
        return PublishResult(
            external_post_id=str(ad_id),
            external_url=f"https://business.facebook.com/adsmanager/manage/ads?act={self._account[4:]}",
        )

    def _set_status(self, external_post_id: str, status: str) -> bool:
        self._call("POST", f"/{external_post_id}", {"status": status})
        return True

    def pause(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "PAUSED")

    def resume(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "ACTIVE")

    # ------------------------------------------------------------- test
    def test(self) -> dict:
        """Verify the token + ad account by reading the account info."""
        data = self._call("GET", f"/{self._account}", {
            "fields": "name,account_status,currency,timezone_name",
        })
        # account_status 1 = active; anything else means the account can't run ads.
        status_map = {1: "active", 2: "disabled", 3: "unsettled", 7: "pending_review",
                      9: "in_grace_period", 101: "closed"}
        return {
            "ad_account_id": self._account,
            "name": data.get("name"),
            "status": status_map.get(data.get("account_status"), data.get("account_status")),
            "currency": data.get("currency"),
            "timezone": data.get("timezone_name"),
        }
