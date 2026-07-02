"""FastAPI app + API routes; serves the web UI.

Run with: uvicorn app.main:app --reload --port 8000

Phase 1 of the Modpools Ad Manager adds persistence (campaigns, ads, approvals,
audit log) and role-based access on top of the AI generator.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .brands import list_brands
from .config import get_settings
from .db import init_db
from .generator import GeneratorError, generate_ads, generate_bulk
from .models import (
    BulkGenerateRequest,
    BulkGenerateResponse,
    GenerateRequest,
    GenerateResponse,
)
from .routers import ads, approvals, campaigns

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Modpools Ad Manager", version="1.1.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.model,
        "effort": settings.effort,
        "api_key_configured": settings.api_key_configured,
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


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    settings = get_settings()
    if not settings.api_key_configured:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured. Add it to your .env file.",
        )
    try:
        return generate_ads(req)
    except GeneratorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/generate/bulk", response_model=BulkGenerateResponse)
def generate_bulk_route(req: BulkGenerateRequest) -> BulkGenerateResponse:
    settings = get_settings()
    if not settings.api_key_configured:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured. Add it to your .env file.",
        )
    try:
        return generate_bulk(req)
    except GeneratorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Ad Manager resources
app.include_router(campaigns.router)
app.include_router(ads.router)
app.include_router(approvals.router)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Serve remaining static assets (room for css/js/images later).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
