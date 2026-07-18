"""Request/response schemas for the API.

`GenerateRequest` is the JSON body for `POST /api/generate`; `GenerateResponse`
is what comes back. `AdVariation` is a single generated ad.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Platform(str, Enum):
    facebook = "facebook"
    instagram = "instagram"
    google_search = "google_search"
    google_display = "google_display"
    youtube = "youtube"
    tiktok = "tiktok"
    linkedin = "linkedin"

    @property
    def label(self) -> str:
        return {
            Platform.facebook: "Facebook",
            Platform.instagram: "Instagram",
            Platform.google_search: "Google Search",
            Platform.google_display: "Google Display",
            Platform.youtube: "YouTube",
            Platform.tiktok: "TikTok",
            Platform.linkedin: "LinkedIn",
        }[self]


class Goal(str, Enum):
    awareness = "awareness"
    traffic = "traffic"
    leads = "leads"
    sales = "sales"
    engagement = "engagement"

    @property
    def label(self) -> str:
        return {
            Goal.awareness: "Brand awareness",
            Goal.traffic: "Website traffic",
            Goal.leads: "Lead generation",
            Goal.sales: "Sales / conversions",
            Goal.engagement: "Engagement",
        }[self]


class GenerateRequest(BaseModel):
    brand: str = Field(..., description="Brand profile id (see GET /api/brands)")
    platform: Platform = Field(..., description="Target ad platform")
    product: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The product, offer, or angle to advertise",
    )
    audience: str | None = Field(
        None,
        max_length=500,
        description="Override the brand's default audience for this campaign",
    )
    goal: Goal = Field(Goal.leads, description="Campaign objective")
    tone: str | None = Field(
        None, max_length=200, description="Optional tone override, e.g. 'playful'"
    )
    count: int = Field(4, ge=1, le=6, description="How many variations to generate")


class AdVariation(BaseModel):
    headline: str
    primary_text: str
    description: str
    call_to_action: str
    visual_concept: str
    hashtags: list[str]
    rationale: str


class GenerateResponse(BaseModel):
    brand: str
    platform: Platform
    variations: list[AdVariation]


class BulkGenerateRequest(BaseModel):
    """Generate ads for many offers in one go.

    Brand/platform/goal/tone/count apply to every offer in `products`; each
    string in `products` is a separate offer/angle to advertise.
    """

    brand: str = Field(..., description="Brand profile id (see GET /api/brands)")
    platform: Platform = Field(..., description="Target ad platform")
    products: list[str] = Field(
        ...,
        min_length=1,
        max_length=25,
        description="One offer/angle per item (max 25 per batch)",
    )
    audience: str | None = Field(None, max_length=500)
    goal: Goal = Field(Goal.leads)
    tone: str | None = Field(None, max_length=200)
    count: int = Field(3, ge=1, le=6, description="Variations per offer")


class BulkResultItem(BaseModel):
    """Result for a single offer in a batch. `error` is set if that offer failed
    (the rest of the batch still succeeds)."""

    product: str
    variations: list[AdVariation] = Field(default_factory=list)
    error: str | None = None


class BulkGenerateResponse(BaseModel):
    brand: str
    platform: Platform
    items: list[BulkResultItem]
