"""Ad endpoints: manual create, list (filterable), get, edit, submit for
approval, and delete.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai_providers import openai_key
from ..audit import log_action
from ..auth import get_current_user, require_roles
from ..brand_assets import download_reference
from ..brands import get_brand
from ..db import get_db
from ..db_models import Ad, Campaign, Creative, User
from ..enums import SUBMITTABLE, AdStatus, Role
from ..image_gen import ImageError, build_image_prompt, generate_image, size_for
from ..models import Platform
from ..schemas import (
    AdCreate,
    AdOut,
    AdUpdate,
    CreativeOut,
    GenerateImageRequest,
    GenerateVideoRequest,
)
from ..video_gen import (
    VideoError,
    build_video_prompt,
    create_job,
    download_data_uri,
    job_status,
)
from ..video_gen import seconds_for as video_seconds
from ..video_gen import size_for as video_size

router = APIRouter(prefix="/api/ads", tags=["ads"])

_EDITORS = (Role.creator, Role.manager)
_MANAGERS = (Role.manager,)


def _get_ad(db: Session, ad_id: int) -> Ad:
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found.")
    return ad


@router.post("", response_model=AdOut, status_code=201)
def create_ad(
    body: AdCreate,
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Ad:
    if db.get(Campaign, campaign_id) is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    ad = Ad(
        campaign_id=campaign_id,
        platform=body.platform.value,
        headline=body.headline,
        primary_text=body.primary_text,
        description=body.description,
        call_to_action=body.call_to_action,
        hashtags=body.hashtags,
        visual_concept=body.visual_concept,
        rationale=body.rationale,
        status=AdStatus.draft.value,
        generated_by_ai=False,
        created_by=user.email,
    )
    db.add(ad)
    db.flush()
    log_action(db, user=user, action="ad.create", entity_type="ad", entity_id=ad.id)
    db.commit()
    db.refresh(ad)
    return ad


@router.get("", response_model=list[AdOut])
def list_ads(
    campaign_id: int | None = None,
    status: AdStatus | None = None,
    platform: Platform | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Ad]:
    q = db.query(Ad)
    if campaign_id is not None:
        q = q.filter(Ad.campaign_id == campaign_id)
    if status:
        q = q.filter(Ad.status == status.value)
    if platform:
        q = q.filter(Ad.platform == platform.value)
    return q.order_by(Ad.created_at.desc()).all()


@router.get("/{ad_id}", response_model=AdOut)
def get_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Ad:
    return _get_ad(db, ad_id)


@router.patch("/{ad_id}", response_model=AdOut)
def update_ad(
    ad_id: int,
    body: AdUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Ad:
    ad = _get_ad(db, ad_id)
    if ad.status not in {AdStatus.draft.value, AdStatus.changes_requested.value}:
        raise HTTPException(
            status_code=409,
            detail=f"Only draft or changes-requested ads can be edited (status: {ad.status}).",
        )
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(ad, key, value)
    log_action(db, user=user, action="ad.update", entity_type="ad",
               entity_id=ad.id, detail={"fields": list(changes)})
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/generate-image", response_model=CreativeOut, status_code=201)
def generate_ad_image(
    ad_id: int,
    body: GenerateImageRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Creative:
    """Generate a real photo for this ad from its visual concept, save it to the
    Creative Library, and return it. Photo generation is OpenAI-only."""
    ad = _get_ad(db, ad_id)
    key = openai_key(db)
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Photo generation needs an OpenAI key. Add one in Settings.",
        )
    campaign = db.get(Campaign, ad.campaign_id)
    brand = get_brand(campaign.brand if campaign else "modpools") or get_brand("modpools")
    # Pull a real product photo from the brand's site to ground the image in the
    # actual product (best-effort — falls back to text-to-image if unavailable).
    reference = download_reference(brand)
    prompt = build_image_prompt(
        brand, visual_concept=ad.visual_concept, headline=ad.headline,
        offer=(campaign.offer if campaign else None),
        has_reference=reference is not None,
    )
    size = size_for(ad.platform, (body.size if body else None))
    try:
        data_uri = generate_image(key, prompt=prompt, size=size, reference=reference)
    except ImageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    creative = Creative(
        type="image", name=f"AI photo · {ad.headline[:60]}", url=data_uri,
        body=None, tags=["ai-generated", ad.platform, f"ad-{ad.id}"],
        aspect_ratio=size, created_by=user.email,
    )
    db.add(creative)
    db.flush()
    log_action(db, user=user, action="ad.generate_image", entity_type="ad",
               entity_id=ad.id, detail={"creative_id": creative.id, "size": size})
    db.commit()
    db.refresh(creative)
    return creative


@router.post("/{ad_id}/generate-video", response_model=CreativeOut, status_code=201)
def generate_ad_video(
    ad_id: int,
    body: GenerateVideoRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Creative:
    """Start an AI video render for this ad. Video renders take minutes, so this
    returns immediately with a 'processing' creative; poll the status endpoint
    until the clip is ready. Video generation is OpenAI (Sora) only."""
    ad = _get_ad(db, ad_id)
    key = openai_key(db)
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Video generation needs an OpenAI key. Add one in Settings.",
        )
    campaign = db.get(Campaign, ad.campaign_id)
    brand = get_brand(campaign.brand if campaign else "modpools") or get_brand("modpools")
    prompt = build_video_prompt(
        brand, visual_concept=ad.visual_concept, headline=ad.headline,
        offer=(campaign.offer if campaign else None),
    )
    size = video_size(ad.platform, (body.size if body else None))
    seconds = video_seconds(body.seconds if body else None)
    try:
        job = create_job(key, prompt=prompt, size=size, seconds=seconds)
    except VideoError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    creative = Creative(
        type="video", name=f"AI video · {ad.headline[:56]}", url=None,
        body=json.dumps({"video_job": job["id"], "status": job["status"]}),
        tags=["ai-generated", ad.platform, f"ad-{ad.id}"],
        aspect_ratio=size, created_by=user.email,
    )
    db.add(creative)
    db.flush()
    log_action(db, user=user, action="ad.generate_video", entity_type="ad",
               entity_id=ad.id, detail={"creative_id": creative.id, "job": job["id"]})
    db.commit()
    db.refresh(creative)
    return creative


@router.get("/video/{creative_id}/status")
def video_status(
    creative_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> dict:
    """Poll an in-progress AI video. When the render completes, the MP4 is saved
    onto the creative and returned as a data URI."""
    creative = db.get(Creative, creative_id)
    if creative is None or creative.type != "video":
        raise HTTPException(status_code=404, detail="Video creative not found.")
    if creative.url:  # already downloaded
        return {"status": "completed", "progress": 100, "url": creative.url}

    try:
        meta = json.loads(creative.body or "{}")
    except (json.JSONDecodeError, TypeError):
        meta = {}
    job_id = meta.get("video_job")
    if not job_id:
        raise HTTPException(status_code=400, detail="No render job on this creative.")

    key = openai_key(db)
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI key missing.")
    try:
        st = job_status(key, job_id)
        if st["status"] == "completed":
            creative.url = download_data_uri(key, job_id)
            creative.body = None
            db.commit()
            return {"status": "completed", "progress": 100, "url": creative.url}
        if st["status"] == "failed":
            return {"status": "failed", "progress": st.get("progress", 0),
                    "error": st.get("error") or "The render failed."}
        return {"status": st["status"], "progress": st.get("progress", 0)}
    except VideoError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{ad_id}/submit", response_model=AdOut)
def submit_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_EDITORS)),
) -> Ad:
    """Send a draft into the approval queue (status -> pending)."""
    ad = _get_ad(db, ad_id)
    if AdStatus(ad.status) not in SUBMITTABLE:
        raise HTTPException(
            status_code=409,
            detail=f"Ad cannot be submitted from status '{ad.status}'.",
        )
    ad.status = AdStatus.pending.value
    log_action(db, user=user, action="ad.submit", entity_type="ad", entity_id=ad.id)
    db.commit()
    db.refresh(ad)
    return ad


@router.delete("/{ad_id}", status_code=204)
def delete_ad(
    ad_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_MANAGERS)),
) -> None:
    ad = _get_ad(db, ad_id)
    log_action(db, user=user, action="ad.delete", entity_type="ad", entity_id=ad.id)
    db.delete(ad)
    db.commit()
