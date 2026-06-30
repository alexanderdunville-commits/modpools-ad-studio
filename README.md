# Modpools Ad Studio

**An AI ad studio for Modpools & Modpro.** Describe a product or offer, pick a
brand and a platform, and it generates several distinct, on-brand ad variations —
headline, primary text, description, call-to-action, a visual concept for your
designer, and hashtags — in seconds. Built on the Claude API (`claude-opus-4-8`).

It runs as a simple web page (no build step): fill in a short brief, click
**Generate ads**, review the variations, and copy the ones you want.

---

## Why it exists

Writing fresh, on-brand ad copy for every campaign, platform, and audience is
slow and repetitive. This tool does the first 80% instantly so your team spends
its time choosing and refining, not staring at a blank page — while staying
inside the brand voice and the claims you're allowed to make.

---

## What it does today (and where it's headed)

This is built as a **phased pipeline** so it can grow from "write copy" into a
full "generate → publish → analyze" loop without a rewrite:

| Phase | What it does | Status |
|-------|--------------|--------|
| **1. Generate** | AI writes ad copy + creative concepts per brand, platform, audience, and goal | ✅ Working |
| **2. Publish** | Push campaigns to Facebook/Instagram (Meta) and Google Ads | 🔌 Scaffolded (`app/publishing.py`) |
| **3. Analyze** | Pull metrics and have AI recommend budget/copy changes | 🔌 Scaffolded (`app/analytics.py`) |

---

## Quick start

You'll need Python 3.10+ and a Claude API key.

1. **Add your API key.** Get one at <https://console.anthropic.com/>, then:
   ```bash
   cp .env.example .env
   # open .env and paste your key into ANTHROPIC_API_KEY
   ```

2. **Run it:**
   ```bash
   ./run.sh
   ```
   (or manually)
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

3. Open <http://localhost:8000>, fill in the brief, and click **Generate ads**.

---

## Make it yours — edit the brand profiles

The most important file is **`app/brands.py`**. The model writes copy from the
brand description, voice, differentiators, and `must_avoid` rules defined there.
The profiles ship with sensible defaults for Modpools and Modpro, but you should
review and edit them so they match how you actually talk about each product —
your real positioning, your current offers, and any claims you can't legally
make. **Better brand context = better ads.**

---

## Configuration

Set these in `.env` (see `.env.example`):

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `ANTHROPIC_API_KEY` | Yes | — | Your Claude API key |
| `NESTLY_MODEL` | No | `claude-opus-4-8` | Model used for generation |
| `NESTLY_EFFORT` | No | `medium` | `low` \| `medium` \| `high` — higher means better copy, slower and pricier |

---

## How to use it

1. **Brand** — Modpools or Modpro.
2. **Platform** — Facebook, Instagram, Google Search, Google Display, or
   LinkedIn. Copy is formatted to each channel's norms (character limits,
   hashtags, tone).
3. **Product / offer / angle** — the thing you're advertising, e.g. *"Summer
   install special on the 20ft container pool with the acrylic window."*
4. **Audience** *(optional)* — override the brand's default audience for this
   campaign.
5. **Goal, tone, count** — objective, optional tone, and how many variations.

Each result includes a headline, primary text, description, CTA, hashtags, a
visual concept for your designer, and a one-line rationale for the angle. Hit
**Copy** on any card to grab it.

---

## Project structure

```
app/
  main.py        FastAPI app + API routes, serves the web UI
  generator.py   Phase 1 — Claude ad generation (the working core)
  brands.py      Brand profiles (edit these!)
  models.py      Request/response schemas
  publishing.py  Phase 2 — ad-platform publishing (stub adapters)
  analytics.py   Phase 3 — performance analysis (stub)
  config.py      Model + settings from the environment
  static/
    index.html   The web UI (single page, no build step)
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Status + whether the API key is configured |
| `GET`  | `/api/brands` | Available brand profiles |
| `POST` | `/api/generate` | Generate ad variations (JSON body — see `GenerateRequest` in `app/models.py`) |

---

## Roadmap

- **Phase 2 — Publishing:** implement the `publish()` methods in
  `app/publishing.py` against the Meta Marketing API and Google Ads API. Each
  needs OAuth credentials and an ad-account ID; the adapter interface is already
  defined.
- **Phase 3 — Analytics:** feed `CampaignMetrics` from your ad accounts into
  `app/analytics.py` and send them to Claude with an analyst prompt for written
  budget/copy recommendations.

---

## Notes

- Private, internal marketing tool. Don't commit your `.env` or API key — it's
  already covered by `.gitignore`.
- Generated copy is a starting point: always review claims and pricing before
  anything goes live.
