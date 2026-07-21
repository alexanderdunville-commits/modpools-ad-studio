"""Live brand assets — real product photos pulled from the brand's website.

To make generated ads look like the *actual* product (not a generic AI pool),
we fetch a real product photo from the brand's site and hand it to the image
model as a visual reference. Photos found live on the site are preferred; the
``reference_images`` baked into the brand profile are the reliable fallback.

Results are cached in-process so we don't hit the site on every generation.
"""

from __future__ import annotations

import re
import time

import httpx

from .brands import BrandProfile

_TIMEOUT = 15.0
_CACHE_TTL = 6 * 3600  # 6 hours
_MAX_BYTES = 8 * 1024 * 1024  # skip anything over 8 MB

# WordPress firewalls (Wordfence/Cloudflare) 403 unknown bot user-agents, so
# present a normal browser UA when fetching the brand's own public pages/images.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}

# brand_id -> (fetched_at, [image_url, ...])
_URL_CACHE: dict[str, tuple[float, list[str]]] = {}

# Skip logos, icons, and tiny thumbnails — we want big product photos.
_SKIP = re.compile(r"(logo|icon|favicon|sprite|badge|thumb|-\d{2,3}x\d{2,3}\.)", re.I)
_IMG_RE = re.compile(
    r"https://[^\"'\s>]+/wp-content/uploads/[^\"'\s>]+\.(?:jpg|jpeg|png|webp)", re.I
)
_OG_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I
)


def _discover_urls(website: str) -> list[str]:
    """Scrape likely product-photo URLs from the site's HTML."""
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True,
                          headers=_HEADERS) as client:
            html = client.get(website).text
    except httpx.HTTPError:
        return []

    urls: list[str] = []
    for m in _OG_RE.finditer(html):
        urls.append(m.group(1))
    urls.extend(_IMG_RE.findall(html) if False else _IMG_RE.findall(html))

    seen: set[str] = set()
    clean: list[str] = []
    for u in urls:
        if u in seen or _SKIP.search(u):
            continue
        seen.add(u)
        clean.append(u)
    return clean[:12]


def product_image_urls(brand: BrandProfile) -> list[str]:
    """Live product photos first (cached), then the brand's static fallbacks."""
    urls: list[str] = []
    if brand.website:
        cached = _URL_CACHE.get(brand.id)
        if cached and (time.time() - cached[0]) < _CACHE_TTL:
            urls = list(cached[1])
        else:
            urls = _discover_urls(brand.website)
            _URL_CACHE[brand.id] = (time.time(), urls)
    # Always append the vetted fallbacks (deduped) so we never come up empty.
    for u in brand.reference_images:
        if u not in urls:
            urls.append(u)
    return urls


def download_reference(brand: BrandProfile) -> tuple[bytes, str] | None:
    """Download the first usable product photo as (bytes, mime), or None."""
    for url in product_image_urls(brand):
        try:
            with httpx.Client(timeout=_TIMEOUT, follow_redirects=True,
                              headers=_HEADERS) as client:
                resp = client.get(url)
            if resp.status_code >= 400:
                continue
            ctype = resp.headers.get("content-type", "").split(";")[0].strip()
            if not ctype.startswith("image/"):
                continue
            data = resp.content
            if not data or len(data) > _MAX_BYTES:
                continue
            return data, ctype
        except httpx.HTTPError:
            continue
    return None
