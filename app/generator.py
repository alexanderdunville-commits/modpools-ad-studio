"""Phase 1 — Claude ad generation (the working core).

Builds a brand- and platform-aware prompt, calls the Claude API with structured
outputs so the response is guaranteed-parseable JSON, and returns typed
`AdVariation`s.
"""

from __future__ import annotations

import json

import anthropic

from .brands import BrandProfile, get_brand
from .config import get_settings
from .models import AdVariation, GenerateRequest, GenerateResponse, Platform

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


def _client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.api_key_configured:
        raise GeneratorError(
            "ANTHROPIC_API_KEY is not configured. Add it to your .env file."
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def generate_ads(req: GenerateRequest) -> GenerateResponse:
    brand = get_brand(req.brand)
    if brand is None:
        raise GeneratorError(f"Unknown brand '{req.brand}'.")

    settings = get_settings()
    client = _client()

    try:
        response = client.messages.create(
            model=settings.model,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            output_config={
                "effort": settings.effort,
                "format": {"type": "json_schema", "schema": _AD_SCHEMA},
            },
            system=_system_prompt(brand),
            messages=[{"role": "user", "content": _user_prompt(req, brand)}],
        )
    except anthropic.APIStatusError as exc:  # surface a clean message upstream
        raise GeneratorError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise GeneratorError("Could not reach the Claude API. Check your network.") from exc

    if response.stop_reason == "refusal":
        raise GeneratorError(
            "The model declined to generate copy for this brief. Try rephrasing it."
        )

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise GeneratorError("The model returned no copy. Try again.")

    try:
        data = json.loads(text)
        raw_variations = data["variations"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GeneratorError("Could not parse the model's response.") from exc

    variations = [AdVariation(**v) for v in raw_variations][: req.count]
    if not variations:
        raise GeneratorError("The model returned zero variations. Try again.")

    return GenerateResponse(
        brand=brand.id, platform=req.platform, variations=variations
    )
