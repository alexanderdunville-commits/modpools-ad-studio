"""AI photo generation — turns an ad concept into a real image file.

Uses OpenAI's image model (``gpt-image-1``). Image generation is OpenAI-only,
so it needs an OpenAI key even if copy is written by Claude. The result is a
PNG returned as base64, which the caller stores as a data URI on a Creative so
it is durable in the database (Render's disk is ephemeral) and directly
viewable/downloadable in the browser.
"""

from __future__ import annotations

from .brands import BrandProfile

_IMAGE_MODEL = "gpt-image-1"

# Platform → output aspect. Square for feeds, vertical for TikTok/Shorts/Stories.
_PLATFORM_SIZE = {
    "facebook": "1024x1024",
    "instagram": "1024x1024",
    "google_display": "1024x1024",
    "google_search": "1024x1024",
    "linkedin": "1024x1024",
    "tiktok": "1024x1536",
    "youtube": "1536x1024",
}
_VALID_SIZES = {"1024x1024", "1024x1536", "1536x1024"}


class ImageError(RuntimeError):
    """Raised when an image can't be generated."""


def size_for(platform: str, override: str | None = None) -> str:
    if override in _VALID_SIZES:
        return override
    return _PLATFORM_SIZE.get(platform, "1024x1024")


def build_image_prompt(
    brand: BrandProfile, *, visual_concept: str, headline: str, offer: str | None,
    has_reference: bool = False,
) -> str:
    """A photographic prompt for a scroll-stopping ad image.

    Image models render text poorly, so we explicitly ask for a clean photo with
    no words/logos baked in — the copy is added separately by the ad platform.
    When a real product photo is supplied as a reference, we tell the model to
    keep the actual product accurate rather than invent one.
    """
    parts = [f"A premium, photorealistic advertising photograph for {brand.name}."]
    if has_reference:
        parts.append(
            "IMPORTANT: the attached image is a real photo of the actual product. "
            "Keep the product's real look, shape, materials, and proportions "
            "faithful to it — do not invent a different-looking product. Restage "
            "it into a polished, aspirational advertising scene."
        )
    parts.append(f"Product context: {brand.description}")
    if offer:
        parts.append(f"This ad is about: {offer.strip()}")
    parts.append(f"Creative direction: {visual_concept.strip()}")
    parts.append(f"The mood should match the headline '{headline.strip()}'.")
    parts.append(
        "Ultra-realistic, high-end editorial lifestyle photography. Natural light, "
        "realistic residential/backyard setting, sharp focus, professional color "
        "grading, magazine-quality composition suitable for a paid social ad. "
        "Photorealism is essential — it must look like a real photograph, not a "
        "render or illustration."
    )
    parts.append(
        "Do NOT render any text, words, captions, watermarks, or logos in the "
        "image — leave clean space for copy to be added later."
    )
    return " ".join(parts)


def generate_image(
    openai_key: str, *, prompt: str, size: str = "1024x1024", quality: str = "high",
    reference: tuple[bytes, str] | None = None,
) -> str:
    """Generate one image and return a ``data:image/png;base64,...`` URI.

    If ``reference`` (image bytes + mime) is given, the real product photo guides
    the result via the image-edit endpoint; on any failure we fall back to plain
    text-to-image so generation never hard-fails on the reference step.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise ImageError("The 'openai' package isn't installed.") from exc

    client = OpenAI(api_key=openai_key)

    if reference is not None:
        ref_bytes, ref_mime = reference
        ext = "png" if "png" in ref_mime else ("webp" if "webp" in ref_mime else "jpg")
        try:
            result = client.images.edit(
                model=_IMAGE_MODEL, image=(f"reference.{ext}", ref_bytes, ref_mime),
                prompt=prompt, size=size, quality=quality, n=1,
            )
            if result.data and getattr(result.data[0], "b64_json", None):
                return f"data:image/png;base64,{result.data[0].b64_json}"
        except Exception:
            pass  # fall back to text-to-image below

    try:
        result = client.images.generate(
            model=_IMAGE_MODEL, prompt=prompt, size=size, quality=quality, n=1
        )
    except Exception as exc:  # openai raises several error subclasses
        raise ImageError(f"OpenAI image error: {exc}") from exc

    if not result.data or not getattr(result.data[0], "b64_json", None):
        raise ImageError("The image model returned no image. Try again.")
    return f"data:image/png;base64,{result.data[0].b64_json}"
