"""AI video generation — turns an ad concept into a real short video clip.

Uses OpenAI's Sora video model. Unlike images, video renders asynchronously
(it takes minutes), so this module speaks the Sora REST API's job lifecycle:

    create_job()  → returns a job id, status "queued"
    job_status()  → "queued" / "in_progress" (with % progress) / "completed" / "failed"
    download()    → the finished MP4 bytes, once completed

The router stores the job on a Creative row and the UI polls status until the
clip is ready, then the MP4 is saved as a data URI (durable in the DB; Render's
disk is ephemeral). Clips are short and cost real money per render, so keep
``seconds`` low by default.
"""

from __future__ import annotations

import base64

import httpx

from .brands import BrandProfile

_BASE = "https://api.openai.com/v1"
_MODEL = "sora-2"
_TIMEOUT = 60.0

# Platform → Sora frame size. Vertical for TikTok/Shorts/Reels, wide for YouTube.
_PLATFORM_SIZE = {
    "tiktok": "720x1280",
    "instagram": "720x1280",
    "facebook": "1280x720",
    "youtube": "1280x720",
    "google_display": "1280x720",
    "linkedin": "1280x720",
    "google_search": "1280x720",
}
_VALID_SIZES = {"720x1280", "1280x720", "1024x1808", "1808x1024"}
_VALID_SECONDS = {"4", "8", "12"}


class VideoError(RuntimeError):
    """Raised when a video job can't be created or fetched."""


def size_for(platform: str, override: str | None = None) -> str:
    if override in _VALID_SIZES:
        return override
    return _PLATFORM_SIZE.get(platform, "720x1280")


def seconds_for(override: str | None) -> str:
    return override if override in _VALID_SECONDS else "4"


def build_video_prompt(
    brand: BrandProfile, *, visual_concept: str, headline: str, offer: str | None
) -> str:
    parts = [
        f"A short, scroll-stopping social-video ad for {brand.name}.",
        f"Product context: {brand.description}",
    ]
    if offer:
        parts.append(f"This ad is about: {offer.strip()}")
    parts.append(f"Shot direction: {visual_concept.strip()}")
    parts.append(f"The energy should match the headline '{headline.strip()}'.")
    parts.append(
        "Bright, aspirational, realistic lifestyle footage in a residential "
        "backyard setting. Smooth camera movement, natural daylight, an "
        "authentic hook in the first second. No on-screen text or captions — "
        "leave that for the platform to add."
    )
    return " ".join(parts)


def _headers(openai_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {openai_key}"}


def _error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return err["message"]
    except ValueError:
        pass
    return f"HTTP {resp.status_code}"


def create_job(
    openai_key: str, *, prompt: str, size: str = "720x1280", seconds: str = "4"
) -> dict:
    """Start a Sora render. Returns {'id', 'status'}."""
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_BASE}/videos", headers=_headers(openai_key),
                               json={"model": _MODEL, "prompt": prompt,
                                     "size": size, "seconds": seconds})
    except httpx.HTTPError as exc:
        raise VideoError(f"Could not reach the OpenAI video API: {exc}") from exc
    if resp.status_code >= 400:
        raise VideoError(f"OpenAI video error: {_error_message(resp)}")
    data = resp.json()
    return {"id": data.get("id"), "status": data.get("status", "queued")}


def job_status(openai_key: str, job_id: str) -> dict:
    """Return {'status', 'progress', 'error'} for a render job."""
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_BASE}/videos/{job_id}", headers=_headers(openai_key))
    except httpx.HTTPError as exc:
        raise VideoError(f"Could not reach the OpenAI video API: {exc}") from exc
    if resp.status_code >= 400:
        raise VideoError(f"OpenAI video error: {_error_message(resp)}")
    data = resp.json()
    err = data.get("error")
    return {
        "status": data.get("status", "unknown"),
        "progress": data.get("progress", 0),
        "error": (err.get("message") if isinstance(err, dict) else err),
    }


def download_data_uri(openai_key: str, job_id: str) -> str:
    """Download the finished MP4 and return it as a data URI."""
    try:
        with httpx.Client(timeout=_TIMEOUT * 3) as client:
            resp = client.get(f"{_BASE}/videos/{job_id}/content",
                              headers=_headers(openai_key))
    except httpx.HTTPError as exc:
        raise VideoError(f"Could not download the video: {exc}") from exc
    if resp.status_code >= 400:
        raise VideoError(f"OpenAI video download error: {_error_message(resp)}")
    b64 = base64.b64encode(resp.content).decode()
    return f"data:video/mp4;base64,{b64}"
