"""Live Google Ads adapter — covers Search, Display, and YouTube.

Google Ads is the most involved of the ad APIs. Authentication is OAuth2 with a
long-lived **refresh token** (exchanged for a short-lived access token on each
call) plus a Google-approved **developer token**. Because that's several
secrets, the connection's encrypted token field holds a small JSON bundle:

    {"refresh_token": "...", "client_id": "...",
     "client_secret": "...", "developer_token": "..."}

Non-secret ids live in ``connection.config``:

- ``customer_id``       — the Google Ads account the ads are created in (digits only)
- ``login_customer_id`` — the manager (MCC) account id, if you access through one
- ``ad_group_id``       — the ad group new ads are created inside (built once in
  the Google Ads UI; this app posts ads into it)
- ``landing_page_url``  — the final URL for the ad

Search ads (``google_search``) are fully text-driven and need no media. Display
(``google_display``) needs an image asset and YouTube (``youtube``) needs a
YouTube video — set ``ad.media_ref`` to the asset resource name / video id.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

from .publishing import PublishError, PublishingAdapter, PublishResult

if TYPE_CHECKING:
    from .db_models import Ad

_API_VERSION = "v17"
_ADS_BASE = f"https://googleads.googleapis.com/{_API_VERSION}"
_OAUTH_URL = "https://oauth2.googleapis.com/token"
_TIMEOUT = 30.0

_HEADLINE_MAX = 30
_DESC_MAX = 90


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    for chunk in (text or "").replace("!", ".").replace("?", ".").split("."):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def build_headlines(ad: "Ad") -> list[dict]:
    """Responsive search ads need 3–15 headlines, each ≤30 chars."""
    candidates = [ad.headline, ad.call_to_action, *_sentences(ad.primary_text),
                  ad.description]
    seen: set[str] = set()
    headlines: list[str] = []
    for c in candidates:
        h = _clip(c or "", _HEADLINE_MAX)
        key = h.lower()
        if h and key not in seen:
            seen.add(key)
            headlines.append(h)
    # Pad to the minimum of 3 with safe brand fallbacks.
    for fallback in ("Modpools", "Get a Modpool", "Backyard pool, fast"):
        if len(headlines) >= 3:
            break
        if fallback.lower() not in seen:
            seen.add(fallback.lower())
            headlines.append(fallback)
    return [{"text": h} for h in headlines[:15]]


def build_descriptions(ad: "Ad") -> list[dict]:
    """Responsive search ads need 2–4 descriptions, each ≤90 chars."""
    candidates = [ad.description, ad.primary_text, ad.headline]
    seen: set[str] = set()
    descs: list[str] = []
    for c in candidates:
        d = _clip(c or "", _DESC_MAX)
        if d and d.lower() not in seen:
            seen.add(d.lower())
            descs.append(d)
    for fallback in ("Container pools delivered and installed fast.",
                     "A real pool without the year-long build."):
        if len(descs) >= 2:
            break
        if fallback.lower() not in seen:
            seen.add(fallback.lower())
            descs.append(fallback)
    return [{"text": d} for d in descs[:4]]


class GoogleAdsLiveAdapter(PublishingAdapter):
    """Real posting to Google Ads (Search/Display/YouTube)."""

    def __init__(
        self,
        *,
        credentials_json: str,
        platform: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        try:
            creds = json.loads(credentials_json) if credentials_json else {}
        except (json.JSONDecodeError, TypeError) as exc:
            raise PublishError(
                "Google connection credentials are malformed. Re-enter the "
                "refresh token, client id/secret and developer token."
            ) from exc
        self._refresh_token = creds.get("refresh_token", "")
        self._client_id = creds.get("client_id", "")
        self._client_secret = creds.get("client_secret", "")
        self._developer_token = creds.get("developer_token", "")
        for label, value in (
            ("refresh token", self._refresh_token),
            ("client id", self._client_id),
            ("client secret", self._client_secret),
            ("developer token", self._developer_token),
        ):
            if not value:
                raise PublishError(
                    f"Google connection is missing its {label}. Re-enter the "
                    "Google credentials on the Connections screen."
                )
        self._platform = platform
        self._config = config or {}
        self._customer_id = str(self._config.get("customer_id") or "").replace("-", "").strip()
        if not self._customer_id:
            raise PublishError(
                "Google connection is missing the customer ID (your Google Ads "
                "account number). Add it in the connection settings."
            )
        self._access_token: str | None = None

    # ------------------------------------------------------------- auth
    def _token(self) -> str:
        if self._access_token:
            return self._access_token
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(_OAUTH_URL, data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                })
        except httpx.HTTPError as exc:
            raise PublishError(f"Could not reach Google OAuth: {exc}") from exc
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400 or "access_token" not in data:
            raise PublishError(
                f"Google OAuth error: {data.get('error_description') or data.get('error') or resp.status_code}"
            )
        self._access_token = data["access_token"]
        return self._access_token

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "developer-token": self._developer_token,
            "Content-Type": "application/json",
        }
        login_cid = str(self._config.get("login_customer_id") or "").replace("-", "").strip()
        if login_cid:
            headers["login-customer-id"] = login_cid
        return headers

    def _call(self, path: str, payload: dict) -> dict:
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(f"{_ADS_BASE}{path}", headers=self._headers(),
                                   json=payload)
        except httpx.HTTPError as exc:
            raise PublishError(f"Could not reach the Google Ads API: {exc}") from exc
        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            # Google returns a detailed error object; surface the first message.
            msg = _first_google_error(body) or f"HTTP {resp.status_code}"
            raise PublishError(f"Google Ads API error: {msg}")
        return body

    # ------------------------------------------------------------- interface
    def _ad_group(self) -> str:
        ag = str(self._config.get("ad_group_id") or "").strip()
        if not ag:
            raise PublishError(
                "Google connection is missing the ad group ID. Create a campaign "
                "+ ad group in Google Ads and paste the ad group ID into the "
                "connection settings."
            )
        return f"customers/{self._customer_id}/adGroups/{ag}"

    def _ad_spec(self, ad: "Ad", final_url: str) -> dict:
        if self._platform == "google_search":
            return {
                "finalUrls": [final_url],
                "responsiveSearchAd": {
                    "headlines": build_headlines(ad),
                    "descriptions": build_descriptions(ad),
                },
            }
        media = (getattr(ad, "media_ref", None) or "").strip()
        if self._platform == "youtube":
            if not media:
                raise PublishError(
                    "This YouTube ad has no video attached. Upload the video to "
                    "YouTube and paste its video ID into the ad's Video/Media ID "
                    "field."
                )
            return {
                "finalUrls": [final_url],
                "videoResponsiveAd": {
                    "videos": [{"asset": media}],
                    "headlines": build_headlines(ad)[:1],
                    "longHeadlines": build_headlines(ad)[:1],
                    "descriptions": build_descriptions(ad)[:1],
                    "callToActions": [{"text": _clip(ad.call_to_action, 20)}],
                },
            }
        # google_display — responsive display ad needs an image asset resource name.
        if not media:
            raise PublishError(
                "This Display ad has no image attached. Upload an image asset in "
                "Google Ads and paste its asset resource name into the ad's "
                "Media ID field."
            )
        return {
            "finalUrls": [final_url],
            "responsiveDisplayAd": {
                "marketingImages": [{"asset": media}],
                "headlines": build_headlines(ad)[:1],
                "longHeadline": {"text": _clip(ad.headline, 90)},
                "descriptions": build_descriptions(ad)[:1],
                "businessName": str(self._config.get("business_name") or "Modpools"),
            },
        }

    def publish(self, ad: "Ad") -> PublishResult:
        final_url = str(self._config.get("landing_page_url") or "https://modpools.com").strip()
        payload = {
            "operations": [{
                "create": {
                    "adGroup": self._ad_group(),
                    "status": "ENABLED",
                    "ad": self._ad_spec(ad, final_url),
                }
            }]
        }
        data = self._call(f"/customers/{self._customer_id}/adGroupAds:mutate", payload)
        results = data.get("results") or []
        resource = results[0].get("resourceName") if results else None
        if not resource:
            raise PublishError("Google accepted the call but returned no ad resource.")
        return PublishResult(
            external_post_id=resource,
            external_url=f"https://ads.google.com/aw/ads?ocid={self._customer_id}",
        )

    def _set_status(self, resource_name: str, status: str) -> bool:
        payload = {
            "operations": [{
                "update": {"resourceName": resource_name, "status": status},
                "updateMask": "status",
            }]
        }
        self._call(f"/customers/{self._customer_id}/adGroupAds:mutate", payload)
        return True

    def pause(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "PAUSED")

    def resume(self, external_post_id: str) -> bool:
        return self._set_status(external_post_id, "ENABLED")

    # ------------------------------------------------------------- test
    def test(self) -> dict:
        """Verify credentials by reading the account's basic info."""
        payload = {
            "query": "SELECT customer.id, customer.descriptive_name, "
                     "customer.currency_code, customer.time_zone FROM customer LIMIT 1"
        }
        data = self._call(f"/customers/{self._customer_id}/googleAds:search", payload)
        rows = data.get("results") or []
        cust = (rows[0].get("customer") if rows else {}) or {}
        return {
            "customer_id": self._customer_id,
            "name": cust.get("descriptiveName"),
            "currency": cust.get("currencyCode"),
            "timezone": cust.get("timeZone"),
            "status": "active",
        }


def _first_google_error(body: dict) -> str | None:
    if not isinstance(body, dict):
        return None
    err = body.get("error")
    if isinstance(err, dict):
        details = err.get("details") or []
        for d in details:
            for e in (d.get("errors") or []):
                if e.get("message"):
                    return e["message"]
        if err.get("message"):
            return err["message"]
    return None
