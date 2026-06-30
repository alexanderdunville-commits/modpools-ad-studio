"""FastAPI app + API routes; serves the web UI.

Run with: uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .generator import GeneratorError, generate_ads
from .models import GenerateRequest, GenerateResponse
from .brands import list_brands

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Modpools Ad Studio", version="1.0.0")


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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Serve remaining static assets (the UI is a single file today, but this keeps
# room for css/js/images later).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
