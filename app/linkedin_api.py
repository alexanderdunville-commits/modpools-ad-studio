"""Live LinkedIn Marketing API adapter.

LinkedIn sponsored content. Auth is a bearer access token from an approved
LinkedIn Marketing Developer app. The connection provides:

- ``access_token``        — OAuth access token (encrypted at rest)
- ``external_account_id`` — the sponsored ad account id (digits only)
- ``config.organization_id`` — the LinkedIn organization (Page) that authors the
  post, digits only
- ``config.campaign_id``     — the campaign new creatives are created inside
- ``config.landing_page_url`` — the article link the ad points to

LinkedIn posts sponsored content in two steps: create a post authored by the
organization, then create a creative that references it under the campaign.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

from .publishing import PublishError, PublishingAdapter, PublishResult

if TYPE_CHECKING:
    from .db_models import Ad

_BASE = "https://api.linkedin.com"
# LinkedIn's versioned API requires a YYYYMM version header.
_VERSION = "202406"
_TIMEOUT = 30.0


class LinkedInLiveAdapter(PublishingAdapter):
    """Real posting to LinkedIn sponsored content."""

    def __init__(
        self,
        *,
        access_token: str,
        ad_account_id: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not access_token:
            raise PublishError(
                "LinkedIn connection has no access token. Add it on the "
                "Connections screen."
            )
        if not ad_account_id:
            raise PublishError(
                "LinkedIn connection has no ad account ID. Add your sponsored "
                "ad account id (digits) in the Account ID field."
            )
        self._token = access_token
        self._account = str(ad_account_id).strip()
        self._config = config or {}

    # ------------------------------------------------------------- plumbing
    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "LinkedIn-Version": _VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, path: str, *, json_body: dict | None = None,
                 headers: dict | None = None) -> httpx.Response:
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.request(method, f"{_BASE}{path}",
                                      headers=self._headers(headers), json=json_body)
        except httpx.HTTPError as exc:
            raise PublishError(f"Could not reach the LinkedIn API: {exc}") from exc
        if resp.status_code >= 400:
            msg = None
            try:
                msg = resp.json().get("message")
            except Exception:
                msg = resp.text[:200]
            raise PublishError(f"LinkedIn API error {resp.status_code}: {msg}")
        return resp

    def _require(self, key: str, hint: str) -> str:
        value = str(self._config.get(key) or "").strip()
        if not value:
            raise PublishError(f"LinkedIn connection is missing '{key}'. {hint}")
        return value

    # ------------------------------------------------------------- interface
    def publish(self, ad: "Ad", media: tuple[bytes, str] | None = None) -> PublishResult:
        # LinkedIn article ads are text+link; uploaded media isn't wired yet.
        org_id = self._require(
            "organization_id",
            "Set the LinkedIn organization (Page) ID that authors the ad.",
        )
        campaign_id = self._require(
            "campaign_id",
            "Create a campaign in Campaign Manager and paste its ID into the "
            "connection settings.",
        )
        landing = str(self._config.get("landing_page_url") or "https://modpools.com").strip()
        org_urn = f"urn:li:organization:{org_id}"

        # 1) Create the sponsored post authored by the organization.
        commentary = ad.primary_text or ad.headline
        tags = " ".join(t for t in (ad.hashtags or []) if t)
        if tags:
            commentary = f"{commentary}\n\n{tags}"
        post_body = {
            "author": org_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "article": {
                    "source": landing,
                    "title": ad.headline,
                    "description": ad.description or "",
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        post_resp = self._request("POST", "/rest/posts", json_body=post_body)
        post_urn = post_resp.headers.get("x-restli-id") or post_resp.headers.get("x-linkedin-id")
        if not post_urn:
            raise PublishError("LinkedIn created the post but returned no post ID.")

        # 2) Create the creative referencing the post under the campaign.
        creative_body = {
            "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
            "content": {"reference": post_urn},
            "intendedStatus": "ACTIVE",
        }
        cr_resp = self._request("POST", "/rest/creatives", json_body=creative_body)
        creative_urn = cr_resp.headers.get("x-restli-id") or cr_resp.headers.get("x-linkedin-id")
        if not creative_urn:
            raise PublishError("LinkedIn created the post but no creative ID came back.")
        return PublishResult(
            external_post_id=creative_urn,
            external_url="https://www.linkedin.com/campaignmanager/accounts",
        )

    def _set_status(self, creative_urn: str, status: str) -> bool:
        path = f"/rest/creatives/{quote(creative_urn, safe='')}"
        self._request("POST", path,
                      json_body={"patch": {"$set": {"intendedStatus": status}}},
                      headers={"X-RestLi-Method": "PARTIAL_UPDATE"})
        return True

    def pause(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "PAUSED")

    def resume(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "ACTIVE")

    # ------------------------------------------------------------- test
    def test(self) -> dict:
        resp = self._request("GET", f"/rest/adAccounts/{self._account}")
        data = resp.json() if resp.content else {}
        return {
            "ad_account_id": self._account,
            "name": data.get("name"),
            "status": data.get("status"),
            "currency": data.get("currency"),
        }
