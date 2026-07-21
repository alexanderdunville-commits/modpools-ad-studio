"""FastAPI app + API routes; serves the web UI.

Run with: uvicorn app.main:app --reload --port 8000

Phase 1 of the Modpools Ad Manager adds persistence (campaigns, ads, approvals,
audit log) and role-based access on top of the AI generator.
"""

from __future__ import annotations

import base64
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .ai_providers import available_providers, resolve_choice, resolve_choices
from .brands import list_brands
from .config import get_settings
from .db import get_db, init_db
from .generator import GeneratorError, generate_ads, generate_bulk
from .models import (
    BulkGenerateRequest,
    BulkGenerateResponse,
    GenerateRequest,
    GenerateResponse,
)
from .routers import (
    ads,
    analytics,
    approvals,
    budgets,
    campaigns,
    connections,
    controls,
    dashboard,
    library,
    schedules,
    settings,
)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Modpools Ad Manager", version="1.6.0", lifespan=lifespan)


@app.middleware("http")
async def password_gate(request: Request, call_next):
    """When APP_PASSWORD is set (e.g. on a hosted deployment), require an HTTP
    Basic password for the whole app. `/api/health` stays open for uptime checks.
    With no APP_PASSWORD (local dev), the app is open."""
    password = get_settings().app_password
    if password and request.url.path != "/api/health":
        supplied = None
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                _, _, supplied = base64.b64decode(header[6:]).decode().partition(":")
            except Exception:
                supplied = None
        if supplied is None or not secrets.compare_digest(supplied, password):
            return Response(
                "Password required.",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Modpools Ad Manager"'},
            )
    return await call_next(request)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    providers = available_providers(db)
    return {
        "status": "ok",
        "model": settings.model,
        "effort": settings.effort,
        # True if any provider (Claude or OpenAI, via env or the dashboard) is set.
        "api_key_configured": bool(providers),
        "ai_providers": providers,
    }


@app.get("/api/brands")
def brands() -> dict:
    return {
        "brands": [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "default_audience": b.default_audience,
            }
            for b in list_brands()
        ]
    }


_NO_PROVIDER = (
    "No AI provider is configured. Open Settings and add an Anthropic (Claude) "
    "or OpenAI API key — whichever you can fund."
)


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, db: Session = Depends(get_db)) -> GenerateResponse:
    choices = resolve_choices(db)
    if not choices:
        raise HTTPException(status_code=503, detail=_NO_PROVIDER)
    # Try each configured provider in order; if one errors (bad/unfunded key),
    # fall through to the next instead of failing outright. Report the primary
    # provider's error — that's the one the user configured and can act on.
    first_exc: GeneratorError | None = None
    for choice in choices:
        try:
            return generate_ads(req, choice)
        except GeneratorError as exc:
            first_exc = first_exc or exc
    raise HTTPException(status_code=502, detail=str(first_exc))


@app.post("/api/generate/bulk", response_model=BulkGenerateResponse)
def generate_bulk_route(
    req: BulkGenerateRequest, db: Session = Depends(get_db)
) -> BulkGenerateResponse:
    choices = resolve_choices(db)
    if not choices:
        raise HTTPException(status_code=503, detail=_NO_PROVIDER)
    first_exc: GeneratorError | None = None
    for choice in choices:
        try:
            return generate_bulk(req, choice)
        except GeneratorError as exc:
            first_exc = first_exc or exc
    raise HTTPException(status_code=502, detail=str(first_exc))


# Ad Manager resources
app.include_router(campaigns.router)
app.include_router(ads.router)
app.include_router(approvals.router)
app.include_router(schedules.router)
app.include_router(controls.router)
app.include_router(budgets.router)
app.include_router(connections.router)
app.include_router(library.router)
app.include_router(analytics.router)
app.include_router(settings.router)
app.include_router(dashboard.router)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Serve remaining static assets (room for css/js/images later).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
