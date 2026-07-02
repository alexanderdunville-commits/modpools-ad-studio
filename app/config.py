"""Model + settings, loaded from the environment.

Reads `.env` automatically (see `.env.example`). The only required value is
`ANTHROPIC_API_KEY`; everything else has a sensible default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Load .env on import so every consumer of get_settings() sees the same values.
load_dotenv()

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_EFFORT = "medium"
VALID_EFFORTS = ("low", "medium", "high")


DEFAULT_DATABASE_URL = "sqlite:///./modpools.db"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    model: str
    effort: str
    database_url: str
    app_password: str | None

    @property
    def api_key_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    effort = os.environ.get("NESTLY_EFFORT", DEFAULT_EFFORT).strip().lower()
    if effort not in VALID_EFFORTS:
        effort = DEFAULT_EFFORT

    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        model=os.environ.get("NESTLY_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        effort=effort,
        database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
        or DEFAULT_DATABASE_URL,
        # When set, the whole app is behind an HTTP Basic password (for hosting).
        app_password=os.environ.get("APP_PASSWORD") or None,
    )
