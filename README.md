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
| `DATABASE_URL` | No | `sqlite:///./modpools.db` | Ad Manager database. Use a Postgres URL in production (also `pip install psycopg[binary]`). |

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

### Single vs. bulk

The UI has two modes:

- **Single offer** — one brief in, several variations out.
- **Bulk (many offers)** — paste a list of offers (one per line, up to 25), share
  the same brand/platform/goal/tone, and generate a full batch in one click. Each
  offer gets its own set of variations, and you can **Download CSV** to pull the
  whole batch into a spreadsheet. One offer failing doesn't stop the rest.

---

## Project structure

```
app/
  main.py        FastAPI app + API routes, serves the web UI
  generator.py   Claude ad generation (the working core)
  brands.py      Brand profiles (edit these!)
  models.py      Generator request/response schemas
  publishing.py  Ad-platform publishing (stub adapters)
  analytics.py   Performance analysis (stub)
  config.py      Model + settings from the environment
  db.py          Database engine/session + startup (SQLAlchemy)
  db_models.py   ORM models (users, campaigns, ads, schedules, limits,
                 budgets, auto-pause rules, blackouts, metrics, …)
  enums.py       Status/role/scope enums
  auth.py        Current-user + role-based access control
  audit.py       Audit-log helper
  security.py    Token encryption + masking
  engine.py      Enforcement engine: poster + rule engine + emergency stop
  schemas.py     Ad Manager API schemas
  routers/
    dashboard.py   Dashboard rollup
    campaigns.py   Campaigns + save AI ads into a campaign
    ads.py         Ad CRUD + submit for approval
    approvals.py   Approval queue + audit endpoint
    schedules.py   Scheduling / calendar feed
    controls.py    Ad Limits: limits, blackout dates, auto-pause rules
    budgets.py     Budgets + spend-vs-budget summary
    connections.py Platform connections (encrypted tokens)
    library.py     Audiences + creative library
    analytics.py   Metrics ingest + KPI rollups
    settings.py    Settings, emergency stop, API keys, engine tick
  static/
    index.html   The web UI (single page, no build step)
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Status + whether the API key is configured |
| `GET`  | `/api/brands` | Available brand profiles |
| `POST` | `/api/generate` | Generate ad variations for one offer (JSON body — see `GenerateRequest` in `app/models.py`) |
| `POST` | `/api/generate/bulk` | Generate ads for many offers at once (JSON body — see `BulkGenerateRequest` in `app/models.py`) |
| `POST` | `/api/campaigns` · `GET` `/api/campaigns` | Create / list campaigns |
| `GET` `PATCH` | `/api/campaigns/{id}` | Get / update a campaign (`POST /archive` to archive) |
| `POST` | `/api/campaigns/{id}/ads/from-generation` | Save AI-generated variations into a campaign as draft ads |
| `POST` `GET` | `/api/ads` | Create / list ads (filter by `campaign_id`, `status`, `platform`) |
| `GET` `PATCH` `DELETE` | `/api/ads/{id}` | Get / edit / delete an ad (`POST /submit` sends it to the approval queue) |
| `GET` | `/api/approvals` | The pending-approval queue |
| `POST` | `/api/ads/{id}/approve` · `/reject` · `/request-changes` | Approve, reject (reason required), or request changes |
| `GET` | `/api/audit` | Recent audit-log entries |
| `POST` `GET` | `/api/schedules` | Schedule an approved ad / calendar feed (`POST /{id}/cancel`) |
| `POST` `GET` `DELETE` | `/api/limits` | Posting/spend limits |
| `POST` `GET` `DELETE` | `/api/blackouts` | Blackout dates |
| `POST` `GET` `DELETE` | `/api/auto-pause-rules` | Auto-pause rules (CPL, budget, frequency, CTR, zero-conversions) |
| `POST` `GET` `DELETE` | `/api/budgets` | Budgets (`GET /summary` for spend-vs-budget) |
| `PUT` `GET` `DELETE` | `/api/connections` | Platform connections (tokens encrypted, returned masked) |
| `POST` `GET` `DELETE` | `/api/audiences` · `/api/creatives` | Audience Builder + Creative Library |
| `POST` | `/api/metrics` | Ingest daily ad metrics (platform sync / CRM webhook) |
| `GET` | `/api/analytics/summary` | KPI rollup (CTR, CPL, ROAS, funnel) |
| `GET` `PATCH` | `/api/settings` | App settings (`PUT /api/settings/api-keys` to store a key) |
| `POST` | `/api/settings/emergency-stop` | Activate / clear the global Emergency Stop |
| `POST` | `/api/engine/tick` | Run the poster + rule engine once (admin) |
| `GET` | `/api/dashboard` · `/api/notifications` | Dashboard rollup / alerts feed |

---

## Ad Manager

The app is the **Modpools Ad Manager** — generate → organize → limit → schedule
→ approve → post → track, review-first throughout (full plan in
[`docs/modpools-ad-manager-product-plan.md`](docs/modpools-ad-manager-product-plan.md)).

- **Campaigns / ads / approvals** — organize ads by offer, market, product size,
  season, audience; nothing is "approved" until an approver signs off (rejects
  require a reason). Every action is written to an **audit log**.
- **Ad Limits** — posting caps (per day/week/month, max active per platform,
  min gap between posts), spend caps, blackout dates, and **auto-pause rules**
  (CPL too high, budget reached, frequency, CTR, zero-conversions). Limits
  resolve most-specific-first: campaign → platform → global.
- **Budgets** — daily/weekly/monthly/campaign/platform budgets with live
  spend-vs-budget; hard caps are enforced before posting *and* pause live ads
  when reached.
- **Scheduling** — queue approved ads; the calendar feed drives the Ad Calendar.
- **Emergency Stop** — one switch pauses every live ad and blocks new posting.
- **Enforcement engine** (`app/engine.py`) — a poster and a rule engine run the
  guardrails. In production they run on a schedule (Celery/cron); locally,
  `POST /api/engine/tick` runs them once so you can drive/verify the pipeline.
- **Roles** — `admin`, `manager`, `creator`, `approver`, `analyst`, enforced
  server-side. In local dev, choose who you're acting as with an `X-User-Email`
  header (e.g. `creator@modpools.local`); default is the seeded admin.
  Production plugs real SSO into `app/auth.py`.
- **Storage** — SQLAlchemy; SQLite by default, Postgres via `DATABASE_URL`.
  Tables + dev users seed on startup.

### Posting: sandbox vs. live

Every platform connection has a **mode**. `sandbox` (default) uses a mock
adapter that simulates posting/pausing — the whole pipeline (limits, budgets,
auto-pause, emergency stop) runs end-to-end with no real spend. `live` uses the
real platform adapter; those are **stubs** today (`app/publishing.py`) — implement
each against its marketing API and add credentials to go live. Note: YouTube ads
run through the Google Ads adapter (video campaigns), not a separate connection.

---

## Roadmap

- **Live platform adapters:** implement `publish()/pause()/resume()` in
  `app/publishing.py` for Meta, Google (Search/Display/YouTube), TikTok,
  Pinterest, and LinkedIn against their marketing APIs (OAuth + ad-account IDs).
- **Real metrics sync:** replace manual `/api/metrics` ingest with a scheduled
  pull from each connected platform (write into the same `metrics` table).
- **AI image creative:** turn each ad's `visual_concept` into a generated image
  (requires a dedicated image model — Claude generates text, not images).
- **Background workers:** run `app/engine.py`'s poster + rule engine on a
  schedule (Celery beat / cron) instead of the manual tick.
- **Manager UI:** browser screens for campaigns, approvals, limits, budgets,
  and the calendar (the current web page is the AI generator).

---

## Notes

- Private, internal marketing tool. Don't commit your `.env` or API key — it's
  already covered by `.gitignore`.
- Generated copy is a starting point: always review claims and pricing before
  anything goes live.
