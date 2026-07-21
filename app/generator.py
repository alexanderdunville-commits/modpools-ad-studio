"""Phase 1 — Claude ad generation (the working core).

Builds a brand- and platform-aware prompt, calls the Claude API with structured
outputs so the response is guaranteed-parseable JSON, and returns typed
`AdVariation`s.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .ai_providers import ProviderChoice, ProviderError, generate_json, resolve_choice
from .brands import BrandProfile, get_brand
from .config import get_settings
from .models import (
    AdVariation,
    BulkGenerateRequest,
    BulkGenerateResponse,
    BulkResultItem,
    GenerateRequest,
    GenerateResponse,
    Platform,
)

# How many offers to generate at once. Small enough to stay well under API rate
# limits; the SDK retries 429s automatically on top of this.
_BULK_CONCURRENCY = 4

# Per-channel norms the model should respect. Keep these short — they're hints,
# not hard limits the model has to count characters against.
PLATFORM_GUIDANCE: dict[Platform, str] = {
    Platform.facebook: (
        "Facebook feed ad. Headline ~40 chars, primary text 1-3 short sentences, "
        "description ~30 chars. Conversational, scroll-stopping first line. "
        "Hashtags optional and minimal (0-2)."
    ),
    Platform.instagram: (
        "Instagram ad. Visual-first and punchy. Primary text short and energetic "
        "with line breaks welcome. Use 3-6 relevant, on-brand hashtags."
    ),
    Platform.google_search: (
        "Google Search responsive ad. Headline <= 30 chars and keyword-forward. "
        "Description <= 90 chars, benefit-led with a clear CTA. No hashtags — "
        "return an empty hashtags list."
    ),
    Platform.google_display: (
        "Google Display ad. Short headline <= 30 chars, longer description <= 90 "
        "chars, strong visual concept since the creative carries the message. "
        "No hashtags — return an empty hashtags list."
    ),
    Platform.youtube: (
        "YouTube video ad (bought through Google Ads). The primary_text is a short "
        "voiceover/script for a 15-30 second spot — hook the viewer in the first 5 "
        "seconds, before the skip button. Headline <= 30 chars. Description is the "
        "companion banner line. The visual_concept is a brief shot list for the "
        "video. No hashtags — return an empty hashtags list."
    ),
    Platform.tiktok: (
        "TikTok in-feed video ad. Native, fast, and authentic — not polished "
        "ad-speak. The primary_text is a short spoken/on-screen script that leads "
        "with a 1-2 second hook. The visual_concept describes a vertical (9:16) "
        "video, ideally UGC-style. Use 3-5 relevant, trend-aware hashtags."
    ),
    Platform.linkedin: (
        "LinkedIn sponsored content. Professional, credibility-led tone. Primary "
        "text can be a couple of sentences focused on business value. Hashtags "
        "optional and professional (0-3)."
    ),
}

# Structured-output schema. Array length is steered by the prompt, not the
# schema (structured outputs doesn't support minItems/maxItems).
_AD_SCHEMA = {
    "type": "object",
    "properties": {
        "variations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "primary_text": {"type": "string"},
                    "description": {"type": "string"},
                    "call_to_action": {"type": "string"},
                    "visual_concept": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "headline",
                    "primary_text",
                    "description",
                    "call_to_action",
                    "visual_concept",
                    "hashtags",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["variations"],
    "additionalProperties": False,
}


class GeneratorError(RuntimeError):
    """Raised when generation can't proceed or the model declines."""


# GeneratorError wraps ProviderError so callers keep one exception type.
def _as_generator_error(exc: ProviderError) -> GeneratorError:
    return GeneratorError(str(exc))


def _system_prompt(brand: BrandProfile) -> str:
    differentiators = "\n".join(f"- {d}" for d in brand.differentiators)
    must_avoid = "\n".join(f"- {m}" for m in brand.must_avoid)
    return (
        "You are a senior performance-marketing copywriter for "
        f"{brand.name}. You write distinct, on-brand ad variations that respect "
        "the brand voice and the claims the brand is allowed to make.\n\n"
        f"# Brand: {brand.name}\n{brand.description}\n\n"
        f"# Voice\n{brand.voice}\n\n"
        f"# Default audience\n{brand.default_audience}\n\n"
        f"# Differentiators\n{differentiators}\n\n"
        f"# Rules you MUST follow (do not violate these)\n{must_avoid}\n\n"
        "Each variation must take a genuinely different angle — don't reword the "
        "same idea. Write copy a human marketer would be happy to ship. The "
        "rationale is one short line explaining the angle for the internal team."
    )


def _user_prompt(req: GenerateRequest, brand: BrandProfile) -> str:
    audience = req.audience.strip() if req.audience else brand.default_audience
    tone = f"\nTone to aim for: {req.tone.strip()}" if req.tone else ""
    guidance = PLATFORM_GUIDANCE[req.platform]
    return (
        f"Write {req.count} distinct ad variation(s) for {brand.name}.\n\n"
        f"Platform: {req.platform.label}\n"
        f"Platform formatting guidance: {guidance}\n\n"
        f"Campaign goal: {req.goal.label}\n"
        f"Audience: {audience}{tone}\n\n"
        f"Product / offer / angle to advertise:\n{req.product.strip()}\n\n"
        f"Return exactly {req.count} variation(s). Each needs a headline, primary "
        "text, description, a call_to_action, a visual_concept describing the image "
        "or video for a designer, hashtags (an empty list when the platform "
        "guidance says no hashtags), and a one-line rationale."
    )


def generate_ads(
    req: GenerateRequest, choice: ProviderChoice | None = None
) -> GenerateResponse:
    brand = get_brand(req.brand)
    if brand is None:
        raise GeneratorError(f"Unknown brand '{req.brand}'.")

    if choice is None:
        choice = resolve_choice()
    if choice is None:
        raise GeneratorError(
            "No AI provider is configured. Add an Anthropic (Claude) or OpenAI "
            "API key on the Settings screen."
        )

    settings = get_settings()
    try:
        data = generate_json(
            choice,
            system=_system_prompt(brand),
            user=_user_prompt(req, brand),
            schema=_AD_SCHEMA,
            effort=settings.effort,
        )
    except ProviderError as exc:
        raise _as_generator_error(exc) from exc

    raw_variations = data.get("variations") if isinstance(data, dict) else None
    if not isinstance(raw_variations, list):
        raise GeneratorError("The model's response was missing variations.")

    variations = [AdVariation(**v) for v in raw_variations][: req.count]
    if not variations:
        raise GeneratorError("The model returned zero variations. Try again.")

    return GenerateResponse(
        brand=brand.id, platform=req.platform, variations=variations
    )


def generate_bulk(
    req: BulkGenerateRequest, choice: ProviderChoice | None = None
) -> BulkGenerateResponse:
    """Generate ads for every offer in `req.products`.

    Offers run concurrently; one failing offer is captured as an `error` on its
    item and does not abort the rest of the batch.
    """
    brand = get_brand(req.brand)
    if brand is None:
        raise GeneratorError(f"Unknown brand '{req.brand}'.")

    if choice is None:
        choice = resolve_choice()
    if choice is None:
        raise GeneratorError(
            "No AI provider is configured. Add an Anthropic (Claude) or OpenAI "
            "API key on the Settings screen."
        )

    # Skip blank lines, keep order, de-dupe accidental repeats.
    seen: set[str] = set()
    products: list[str] = []
    for raw in req.products:
        product = raw.strip()
        if product and product.lower() not in seen:
            seen.add(product.lower())
            products.append(product)

    if not products:
        raise GeneratorError("No offers to generate. Add at least one offer line.")

    def _one(product: str) -> BulkResultItem:
        single = GenerateRequest(
            brand=req.brand,
            platform=req.platform,
            product=product,
            audience=req.audience,
            goal=req.goal,
            tone=req.tone,
            count=req.count,
        )
        try:
            result = generate_ads(single, choice)
            return BulkResultItem(product=product, variations=result.variations)
        except GeneratorError as exc:
            return BulkResultItem(product=product, error=str(exc))

    with ThreadPoolExecutor(max_workers=_BULK_CONCURRENCY) as pool:
        items = list(pool.map(_one, products))

    return BulkGenerateResponse(brand=brand.id, platform=req.platform, items=items)
