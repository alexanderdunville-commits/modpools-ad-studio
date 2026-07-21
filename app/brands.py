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
    # The brand's real website — used to pull live product photos (as visual
    # references for image/video generation) and to ground copy in reality.
    website: str = ""
    # Known-good real product photo URLs from the site, used as generation
    # references so AI images/videos look like the actual product, not a
    # generic stand-in. Live photos from the site are preferred at runtime;
    # these are the reliable fallback.
    reference_images: list[str] = field(default_factory=list)


BRANDS: dict[str, BrandProfile] = {
    "modpools": BrandProfile(
        id="modpools",
        name="Modpools",
        description=(
            "Modpools makes modular swimming pools built from real steel shipping "
            "containers (the classic corrugated-steel container look, often in a "
            "signature blue or custom color). They arrive factory-built and fully "
            "assembled with premium Pentair equipment already installed — a "
            "variable-speed pump, cartridge filter, MasterTemp heater, LED "
            "lighting, and app control — all hidden in an insulated equipment bay, "
            "so no separate pump house is needed. Installed in days, not the "
            "6–12 months a traditional pool takes. Popular options include a large "
            "acrylic viewing window on the side, spa seating, swim jets, a Baja "
            "ledge, and an infinity edge. They can go in-ground, semi in-ground, "
            "above ground, on slopes, into decks, or on rooftops, and work "
            "year-round in any climate thanks to the built-in heater."
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
        website="https://modpools.com",
        reference_images=[
            "https://modpools.com/wp-content/uploads/2021/06/ModPool-13-Web-1024x682.jpg",
            "https://modpools.com/wp-content/uploads/2023/12/1.jpg",
            "https://modpools.com/wp-content/uploads/2023/12/2.jpg",
        ],
    ),
    "modpro": BrandProfile(
        id="modpro",
        name="Modpro",
        description=(
            "Modpro modifies real steel shipping containers into custom structures "
            "for business and worksites, with 15+ years of container-modification "
            "experience. Core products: professional container offices and portable "
            "offices (with windows, electrical, insulation, and heating, finished "
            "like a real office inside); high-end executive portable washrooms "
            "(flush toilets, urinals, running-water sinks, separate stalls — an "
            "upscale alternative to porta-potties); and hazardous-waste containment "
            "units for safe on-site storage. The exterior keeps the rugged "
            "corrugated-steel container look; interiors are fully finished. Units "
            "arrive largely complete and are craned into place fast. Real projects "
            "include a Steve Nash Fitness World office, a 12+ container commercial "
            "kitchen, and an extra-wide container office at YVR (Vancouver airport)."
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
        website="https://modpro.ca",
        reference_images=[
            "https://modpro.ca/wp-content/uploads/2019/10/Modpro-Office1.jpg",
            "https://modpro.ca/wp-content/uploads/2025/03/Exterior-Front.jpg",
            "https://modpro.ca/wp-content/uploads/2019/10/Modpro-Containment1.jpg",
        ],
    ),
}


def get_brand(brand_id: str) -> BrandProfile | None:
    return BRANDS.get(brand_id.lower().strip())


def list_brands() -> list[BrandProfile]:
    return list(BRANDS.values())
