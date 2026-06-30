"""Brand profiles — THE file to edit.

The model writes copy from the description, voice, differentiators, and
`must_avoid` rules below. The defaults are a reasonable starting point for
Modpools and Modpro, but you should review and edit them so they match how you
actually talk about each product — your real positioning, your current offers,
and any claims you can't legally make. Better brand context = better ads.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BrandProfile:
    id: str
    name: str
    description: str
    voice: str
    default_audience: str
    differentiators: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)


BRANDS: dict[str, BrandProfile] = {
    "modpools": BrandProfile(
        id="modpools",
        name="Modpools",
        description=(
            "Modpools makes modular, shipping-container swimming pools that arrive "
            "pre-plumbed and pre-wired and are installed in about a day. Each pool "
            "ships ready to swim, with built-in heating, an optional acrylic viewing "
            "window, and remote-control jets, lighting, and temperature. They're a "
            "faster, lower-hassle alternative to a traditional in-ground pool."
        ),
        voice=(
            "Friendly, confident, and refreshingly straightforward. We sell ease and "
            "speed without overhyping. Warm and a little fun, never stuffy or "
            "salesy. We talk like a knowledgeable neighbor, not a billboard."
        ),
        default_audience=(
            "Homeowners 30-55 with a backyard who want a pool but dread the cost, "
            "mess, and months of construction a traditional pool requires."
        ),
        differentiators=[
            "Installed in roughly a day, not a whole summer",
            "Arrives pre-plumbed and pre-wired — ready to swim fast",
            "Optional acrylic window turns the pool into a backyard centerpiece",
            "Control heating, jets, and lighting from your phone",
            "Relocatable — it can move with you, unlike an in-ground pool",
        ],
        must_avoid=[
            "Do not promise an exact install time of 'one day' as a guarantee — "
            "say 'about a day' or 'as little as a day'",
            "Do not quote specific prices or financing terms",
            "Do not claim it is the cheapest pool option",
            "Do not make safety or health guarantees (e.g. 'completely child-safe')",
        ],
    ),
    "modpro": BrandProfile(
        id="modpro",
        name="Modpro",
        description=(
            "Modpro builds modular, container-based structures for business and "
            "work — pop-up offices, on-site jobsite spaces, retail and hospitality "
            "builds, and durable storage. Like Modpools, units arrive largely "
            "finished and are craned into place fast, giving businesses turnkey "
            "space without a ground-up construction project."
        ),
        voice=(
            "Practical, credible, and efficiency-minded. We speak to operators and "
            "decision-makers who care about timelines, durability, and ROI. Clear "
            "and grounded, with quiet confidence — competence over flash."
        ),
        default_audience=(
            "Business owners, contractors, and facilities/operations managers who "
            "need durable, flexible space quickly without committing to permanent "
            "construction."
        ),
        differentiators=[
            "Turnkey space delivered and installed in days, not months",
            "Built from steel containers — rugged and weather-tough",
            "Relocatable and reconfigurable as the business changes",
            "Lower disruption than ground-up construction on a working site",
            "Customizable for office, retail, hospitality, or storage use",
        ],
        must_avoid=[
            "Do not quote specific prices, lease terms, or delivery dates",
            "Do not make code-compliance or permitting guarantees — these vary by "
            "jurisdiction",
            "Do not claim structures are indestructible or fireproof",
            "Do not promise specific ROI figures or payback periods",
        ],
    ),
}


def get_brand(brand_id: str) -> BrandProfile | None:
    return BRANDS.get(brand_id.lower().strip())


def list_brands() -> list[BrandProfile]:
    return list(BRANDS.values())
