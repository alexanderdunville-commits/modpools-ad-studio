"""AI provider layer — one generation call, multiple back ends.

The ad copy is written by an LLM. This module decides *which* LLM and runs the
call, so the rest of the app never cares who the provider is. Two providers are
supported today:

- ``anthropic`` — Claude (the default, best quality; the app was designed for it)
- ``openai``    — GPT, for when Anthropic billing isn't available

A key can come from either the database (``Setting.api_keys_enc`` — set in the
dashboard's Settings screen, no redeploy needed) or the environment. The
database wins so a non-technical user can paste a key into the UI and go.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Provider preference when more than one key is available. Claude first.
_PROVIDER_ORDER = ("anthropic", "openai")

# DB key names (Setting.api_keys_enc) and their env-var fallbacks.
_KEY_NAMES = {
    "anthropic": ("anthropic", "ANTHROPIC_API_KEY"),
    "openai": ("openai", "OPENAI_API_KEY"),
}

_DEFAULT_MODELS = {
    "anthropic": os.environ.get("NESTLY_MODEL", "claude-opus-4-8"),
    "openai": os.environ.get("OPENAI_MODEL", "gpt-4o"),
}


class ProviderError(RuntimeError):
    """No usable provider, or the provider call failed."""


@dataclass(frozen=True)
class ProviderChoice:
    provider: str
    api_key: str
    model: str


def _db_keys(db: "Session | None") -> dict[str, str]:
    """Decrypted {provider: api_key} from the database settings, if any."""
    if db is None:
        return {}
    try:
        from .db_models import Setting
        from .security import decrypt

        setting = db.get(Setting, 1)
        if not setting or not setting.api_keys_enc:
            return {}
        out: dict[str, str] = {}
        for provider, (db_name, _env) in _KEY_NAMES.items():
            enc = setting.api_keys_enc.get(db_name)
            if enc:
                try:
                    out[provider] = decrypt(enc)
                except Exception:
                    pass  # a bad/rotated ciphertext shouldn't break generation
        return out
    except Exception:
        return {}


def _resolve_key(provider: str, db_keys: dict[str, str]) -> str | None:
    if db_keys.get(provider):
        return db_keys[provider]
    _db_name, env_var = _KEY_NAMES[provider]
    return os.environ.get(env_var) or None


def resolve_choices(db: "Session | None" = None) -> list[ProviderChoice]:
    """All usable providers, best first, to try in order.

    A key set in the dashboard (database) ranks **above** an environment key —
    if you paste an OpenAI key into Settings, it's used even when an old Claude
    key still lingers in the server environment. Within each tier the order is
    Claude then OpenAI, unless AI_PROVIDER forces one.
    """
    db_keys = _db_keys(db)

    forced = (os.environ.get("AI_PROVIDER") or "").strip().lower()
    order = (forced,) if forced in _KEY_NAMES else _PROVIDER_ORDER

    dashboard_tier: list[ProviderChoice] = []
    env_tier: list[ProviderChoice] = []
    for provider in order:
        if db_keys.get(provider):
            dashboard_tier.append(ProviderChoice(
                provider=provider, api_key=db_keys[provider],
                model=_DEFAULT_MODELS[provider]))
        else:
            _db_name, env_var = _KEY_NAMES[provider]
            env_key = os.environ.get(env_var)
            if env_key:
                env_tier.append(ProviderChoice(
                    provider=provider, api_key=env_key,
                    model=_DEFAULT_MODELS[provider]))
    return dashboard_tier + env_tier


def resolve_choice(db: "Session | None" = None) -> ProviderChoice | None:
    """The single best provider (see resolve_choices for ordering)."""
    choices = resolve_choices(db)
    return choices[0] if choices else None


def openai_key(db: "Session | None" = None) -> str | None:
    """The OpenAI key specifically (image generation is OpenAI-only), dashboard
    key first then environment."""
    return _resolve_key("openai", _db_keys(db))


def available_providers(db: "Session | None" = None) -> list[str]:
    db_keys = _db_keys(db)
    return [p for p in _PROVIDER_ORDER if _resolve_key(p, db_keys)]


# ---------------------------------------------------------------- generation
def generate_json(
    choice: ProviderChoice,
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    effort: str = "medium",
) -> dict:
    """Run one structured-output generation and return the parsed JSON object."""
    if choice.provider == "anthropic":
        return _anthropic(choice, system=system, user=user, schema=schema, effort=effort)
    if choice.provider == "openai":
        return _openai(choice, system=system, user=user, schema=schema)
    raise ProviderError(f"Unknown provider '{choice.provider}'.")


def _anthropic(choice: ProviderChoice, *, system: str, user: str,
               schema: dict, effort: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=choice.api_key)
    try:
        response = client.messages.create(
            model=choice.model,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            output_config={
                "effort": effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIStatusError as exc:
        raise ProviderError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ProviderError("Could not reach the Claude API. Check your network.") from exc

    if response.stop_reason == "refusal":
        raise ProviderError(
            "The model declined to generate copy for this brief. Try rephrasing it."
        )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise ProviderError("The model returned no copy. Try again.")
    return _parse(text)


def _openai(choice: ProviderChoice, *, system: str, user: str, schema: dict) -> dict:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ProviderError(
            "The 'openai' package isn't installed. Add openai>=1.40 to "
            "requirements.txt."
        ) from exc

    client = OpenAI(api_key=choice.api_key)
    try:
        response = client.chat.completions.create(
            model=choice.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "ad_variations", "strict": True,
                                "schema": schema},
            },
        )
    except Exception as exc:  # openai raises several error subclasses
        raise ProviderError(f"OpenAI API error: {exc}") from exc

    choice0 = response.choices[0]
    if choice0.finish_reason == "content_filter":
        raise ProviderError(
            "OpenAI declined to generate copy for this brief. Try rephrasing it."
        )
    text = choice0.message.content
    if not text:
        raise ProviderError("The model returned no copy. Try again.")
    return _parse(text)


def _parse(text: str) -> dict:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProviderError("Could not parse the model's response.") from exc
