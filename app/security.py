"""Encryption + masking for sensitive values (platform tokens, API keys).

Tokens are encrypted at rest (Fernet) and never returned to clients — reads
return a masked preview. Set `SECRET_ENCRYPTION_KEY` (a Fernet key) in
production; a stable dev key is derived otherwise so local tokens round-trip.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _load_key() -> bytes:
    env = os.environ.get("SECRET_ENCRYPTION_KEY")
    if env:
        return env.encode()
    # Dev fallback: deterministic key so encrypted values survive restarts.
    # NOT for production — set SECRET_ENCRYPTION_KEY there.
    digest = hashlib.sha256(b"modpools-ad-manager-dev-key").digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_load_key())


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet.decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def mask(value: str | None) -> str | None:
    """Show only the last 4 chars, e.g. '••••••3f9a'. Never the full secret."""
    if not value:
        return None
    tail = value[-4:] if len(value) >= 4 else value
    return "••••••" + tail
