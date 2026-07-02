# Modpools Ad Manager — Product Plan

> Internal advertising platform for **Modpools** (premium container swimming pools & spas).
> Generate ads with AI → save & organize → set hard limits & budgets → schedule → approve → post to ad platforms → track performance → pause/stop.
>
> This document is written to be built from. It defines the product, the data model, the automation rules, the workflows, and the exact developer steps to ship an MVP and grow it.

---

## 1. App Overview

**Modpools Ad Manager** is an internal, multi-user web application that gives the Modpools marketing/sales team one place to run paid advertising across seven platforms without touching each platform's native ad manager.

The core promise is **control**: AI produces the creative fast, but nothing spends money or goes live without passing the team's guardrails — posting limits, budget caps, an approval queue, and auto-pause rules. It is deliberately "review-first": AI drafts, humans approve, the system posts and enforces.

**Design principles**

- **Premium & calm.** The UI should feel like a high-end SaaS product (think Linear/Notion polish), matching the Modpools brand. Lots of whitespace, one clear action per screen, no clutter.
- **Simple for non-technical users.** A salesperson can generate and schedule an ad in under 2 minutes. Power/limits/config live behind Admin tabs.
- **Guardrails over trust.** Limits are enforced by the system, not by discipline. If a rule says "max $500/day," the system physically cannot exceed it.
- **Everything auditable.** Every generate/edit/approve/post/pause action is logged with who/when/what.

**Foundation that already exists.** This repo already contains **Modpools Ad Studio** — a FastAPI + Claude (`claude-opus-4-8`) ad *generator* with brand profiles for Modpools and Modpro, structured-output ad generation, and single/bulk modes. The Ad Manager is the productization of that: it keeps the generator as its "Create Ads" engine and wraps it with persistence, scheduling, limits, approvals, posting, and analytics.

---

## 2. Main Features

1. **AI ad generation** — on-brand copy + creative concepts per platform, audience, offer, and goal (powered by the existing Claude generator).
2. **Campaign management** — group ads by offer, market, product size, season, and audience.
3. **Posting limits** — hard caps on ads/day, /week, /month, per platform; min time between posts; blackout dates.
4. **Budget management** — daily / weekly / monthly / per-campaign / per-platform budgets with live spend tracking.
5. **Scheduling** — pick date/time/platform; visual calendar; recurring schedules.
6. **Approval queue** — required human sign-off before anything posts.
7. **Multi-platform posting** — push approved ads to Meta (FB/IG), Google (Search/Display/YouTube), TikTok, Pinterest, LinkedIn.
8. **Performance tracking** — impressions, clicks, leads, CPL, conversions, booked calls, sales, ROAS.
9. **Pause / stop** — per-ad pause, per-campaign pause, and a global **Emergency Stop**.
10. **Auto-pause automation** — rules that pause ads when CPL is too high, budget is reached, or frequency is too high.
11. **Audience & creative libraries** — reusable saved audiences and reusable creative assets.
12. **Roles & permissions** — who can generate, approve, post, and change limits.

---

## 3. User Roles

| Role | Can generate | Can edit | Can approve | Can post/publish | Can change limits & budgets | Can connect platforms | Notes |
|---|---|---|---|---|---|---|---|
| **Owner / Admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Full control incl. Emergency Stop, user management, API keys. |
| **Marketing Manager** | ✅ | ✅ | ✅ | ✅ | ✅ (within admin-set ceilings) | ✅ | Day-to-day operator. |
| **Ad Creator (Sales/Marketing)** | ✅ | ✅ (own drafts) | ❌ | ❌ | ❌ | ❌ | Generates and submits to Approval Queue. |
| **Approver / Reviewer** | ❌ | comment/request-changes | ✅ | ❌ | ❌ | ❌ | Brand/compliance gatekeeper. |
| **Analyst / Viewer** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Read-only dashboards & analytics. |

Roles are enforced server-side (not just hidden UI). A single user can hold multiple roles. The **Emergency Stop** is available to Admin and Marketing Manager only.

---

## 4. Tab-by-Tab Breakdown

### 4.1 Dashboard
The at-a-glance command center.
- **KPI row:** Active campaigns, Spend (today / MTD), Leads, CTR, CPL, ROAS — each with trend vs. previous period.
- **Spend vs. budget** progress bars (day / month) with color states (green/amber/red).
- **Scheduled next 7 days** mini-calendar strip.
- **Approval queue count** with a jump-in button.
- **Alerts feed:** auto-pauses triggered, budgets near cap, platform token expiring, rejected ads.
- **Top & bottom performers** (by ROAS / CPL) with quick pause/boost actions.

### 4.2 Create Ads
The AI generator (existing engine).
- Inputs: **Brand** (Modpools), **Platform**, **Offer/product/angle**, **Audience** (pick a saved audience or free-text), **Goal** (awareness/traffic/leads/sales/engagement), **Tone**, **# variations**.
- **Single** and **Bulk** modes (paste many offers → batch generate).
- Output cards per variation: headline, primary text, description, CTA, hashtags, **visual concept** (brief for designer or image-gen), rationale.
- Per card: **Copy**, **Edit**, **Save to campaign**, **Send to Approval**, **Add creative** (attach an image/video from Creative Library or generate one).
- Enforces brand `must_avoid` rules (no fixed prices, no install-time guarantees, no safety guarantees).

### 4.3 Campaigns
Organize the book of work.
- List/grid of campaigns filterable by **offer, market, product size (e.g. 12ft/16ft/20ft), season, audience, platform, status**.
- Campaign detail: attached ads, budget, schedule, limits inherited/overridden, spend, performance rollup.
- Actions: create/duplicate/archive campaign, bulk-assign ads, pause whole campaign.

### 4.4 Ad Calendar
When things post.
- Month / week / day views. Each entry = a scheduled ad (color-coded by platform, icon by status).
- Drag-to-reschedule (re-validates limits & blackout dates on drop).
- Overlays: **blackout dates** (shaded), **budget pacing** per day, **limit ceilings** (e.g. "3/5 daily slots used").
- Click a slot → quick-schedule an approved ad.

### 4.5 Ad Limits
The guardrail control panel — **detailed in §5**.

### 4.6 Budget Manager
- Set budgets at **daily / weekly / monthly / per-campaign / per-platform** levels.
- Live **spend vs. budget** with pacing (are we ahead/behind projected burn?).
- Allocation view: how today's budget is split across platforms/campaigns.
- Alerts at configurable thresholds (e.g. 80%, 100%).
- Currency, timezone, and "budget reset" boundaries (calendar day vs. rolling 24h).

### 4.7 Approval Queue
- Kanban or list: **Pending → Approved → Rejected / Changes requested**.
- Each item shows full ad preview (platform-accurate mock), target audience, schedule, budget, and the brand-rule check result.
- Approver actions: **Approve**, **Reject** (reason required), **Request changes** (comment back to creator), **Approve & schedule**.
- Bulk approve for trusted creators (Admin-configurable).
- SLA indicator (how long an ad has waited).

### 4.8 Platform Connections
- Connect/disconnect each ad account via **OAuth**: Meta (FB+IG), Google Ads (Search/Display/YouTube), TikTok, Pinterest, LinkedIn.
- Per connection: account name/ID, status (connected / token-expiring / error), scopes granted, last sync time, **Reconnect** button.
- Sandbox/live toggle for safe testing.
- Health checks and token auto-refresh status.

### 4.9 Audience Builder
- Create/save reusable audiences: **luxury homeowners, Airbnb/short-term-rental owners, vacation-home owners, compact-backyard buyers, people who requested pricing, past leads (retargeting), lookalikes.**
- Fields: name, description, platform mapping (how it maps to each network's targeting), geo, demographics, interests, custom/retargeting source.
- Audiences are referenced by ads and by the AI generator (so copy is written for the right person).

### 4.10 Creative Library
- Store & tag: **images, videos, headlines, captions, CTAs, testimonials, before/after visuals**.
- Filter by type, campaign, platform, aspect ratio, season.
- Version history; mark "approved for use." Attach assets to ads in Create Ads.
- (Advanced) AI image generation slot — see §14 note on image models.

### 4.11 Analytics
- Funnel: **impressions → clicks → leads → booked calls → sales**, with CPL, conversion rate, ROAS.
- Breakdowns by platform, campaign, audience, offer, creative, time.
- Comparisons (period over period, platform vs. platform, A/B variations).
- Exports (CSV/PDF) and scheduled email reports.

### 4.12 Settings
- **Users & permissions** (roles from §3).
- **Brand voice & profiles** (edit Modpools voice, differentiators, `must_avoid`).
- **Company details** (name, site, contact, legal disclaimers).
- **Notifications** (email/Slack: approvals, auto-pauses, budget alerts).
- **API keys & integrations** (Claude/AI key, image provider, ad-platform apps, webhook secrets) — stored encrypted, masked in UI.
- **Defaults** (timezone, currency, default limits, default approval requirement).

---

## 5. Ad Limits Tab (Detailed)

This is the heart of "control." Limits can be set **globally**, and **overridden per campaign or per platform** (most-specific wins). All limits are **enforced server-side by the scheduler/poster before any spend occurs**.

### 5.1 Posting-volume limits
- **Max ads per day** (global / per platform / per campaign)
- **Max ads per week**
- **Max ads per month**
- **Max number of active ads per platform**
- **Minimum time between posts** (e.g. ≥ 2 hours) — prevents burst posting
- **Max posts per audience per week** — anti-fatigue

### 5.2 Spend limits
- **Max spend per day** (global / per platform / per campaign)
- **Max spend per campaign** (lifetime)
- **Max spend per platform** (per period)
- **Hard cap vs. soft cap:** soft cap = alert + require re-approval to continue; hard cap = auto-pause, cannot exceed.

### 5.3 Approval & control
- **Approval required before posting** (on/off, and per-role — e.g. Managers auto-approved, Creators not)
- **Emergency Stop** — one button that immediately pauses **all** ads on **all** platforms and blocks new posting until manually cleared. Requires confirmation; logged; sends notifications.

### 5.4 Auto-pause rules (evaluated continuously)
- **Pause if Cost-Per-Lead > threshold** (e.g. CPL > $80 over the last N leads/hours)
- **Pause if budget reached** (day/campaign/platform cap hit)
- **Pause if frequency too high** (e.g. avg frequency > 3.5 in 7 days → audience fatigue)
- **Pause if CTR collapses** (optional: CTR < X% after ≥ Y impressions)
- **Pause if spend with zero conversions** (e.g. spent > $150, 0 leads)
- Each rule: enable/disable, threshold, evaluation window, and **action** (pause vs. alert-only).

### 5.5 Timing controls
- **Blackout dates** — date ranges when ads cannot run (holidays, PR-sensitive periods, inventory gaps). Scheduler refuses to post and calendar shades them.
- **Allowed posting windows** (e.g. only 6am–9pm local).
- **Per-platform pacing** (spread today's posts evenly vs. front-load).

### 5.6 Rule precedence & UX
- Resolution order: **Ad override → Campaign limit → Platform limit → Global limit.**
- The UI shows the **effective limit** for any ad ("Blocked: would exceed Meta daily cap 5/5") with a plain-English reason.
- A **"why can't this post?"** explainer on every blocked ad.

```
Effective-limit resolver (pseudocode):
limit(metric, ad) =
    ad.override[metric]
    ?? campaign(ad).limit[metric]
    ?? platform(ad).limit[metric]
    ?? global.limit[metric]
```

---

## 6. Example User Flow

**Persona:** Dana, Marketing Manager. Goal: launch a spring "16ft container pool" lead campaign on Meta + Google.

1. **Create campaign** — Campaigns → New → "Spring 16ft Lead Push", offer = 16ft pool spring install, market = Pacific NW, season = Spring, audience = "Compact-backyard buyers."
2. **Generate ads** — Create Ads → Brand: Modpools, Platform: Facebook, pull offer/audience from the campaign, 4 variations. Repeat for Google Search. Reviews cards, edits one headline.
3. **Attach creative** — adds a before/after image from Creative Library to the top 2 variations.
4. **Save & submit** — saves the 6 best variations to the campaign, clicks **Send to Approval**.
5. **Set budget & limits** — Budget Manager: campaign budget $4,000; daily $400. Ad Limits: max 3 posts/day on Meta, auto-pause if CPL > $75, blackout on a store-closure weekend.
6. **Approve** — Approver opens the queue, sees platform-accurate previews + brand-rule pass, approves 5, requests a change on 1.
7. **Schedule** — approved ads dropped onto the Ad Calendar across the next 2 weeks; system validates limits/blackouts on each drop.
8. **Post** — at each scheduled time the poster re-checks limits/budget, then publishes via the platform API. Status → Live.
9. **Monitor** — Dashboard shows spend pacing and CPL. Day 3, Meta CPL crosses $75 → auto-pause fires, Dana gets a Slack alert.
10. **Adjust** — Dana pauses the weak variation, shifts budget to the winner, reschedules.

---

## 7. Database Structure

Relational (PostgreSQL). Core tables and key columns (FKs in *italics*):

**users** — id, name, email, password_hash/SSO_id, created_at
**roles** — id, name; **user_roles** — *user_id*, *role_id*

**brands** — id, name, description, voice, default_audience, differentiators (jsonb), must_avoid (jsonb)

**campaigns** — id, name, *brand_id*, offer, market, product_size, season, *audience_id*, status (draft/active/paused/archived), created_by, created_at

**ads** — id, *campaign_id*, platform (enum), headline, primary_text, description, cta, hashtags (jsonb), visual_concept, *creative_id* (nullable), rationale, status (draft/pending/approved/rejected/scheduled/live/paused/completed), generated_by_ai (bool), *created_by*, created_at, updated_at

**ad_variations** *(optional)* — id, *ad_id*, field-level A/B variants

**schedules** — id, *ad_id*, *platform_connection_id*, scheduled_at (tz-aware), recurrence (jsonb/null), status (queued/posting/posted/failed/canceled), posted_at, external_post_id

**budgets** — id, scope (global/campaign/platform/audience), *scope_ref_id*, period (daily/weekly/monthly/lifetime), amount, currency, reset_boundary

**spend_records** — id, *ad_id*/*campaign_id*/platform, date, amount, source (platform_sync), synced_at

**limits** — id, scope (global/platform/campaign/ad), *scope_ref_id*, metric (max_ads_day/…/min_gap_minutes/…), value, cap_type (soft/hard)

**auto_pause_rules** — id, scope, *scope_ref_id*, rule_type (cpl/budget/frequency/ctr/zero_conv), threshold, window, action (pause/alert), enabled

**blackout_dates** — id, scope, *scope_ref_id*, start_date, end_date, reason

**approvals** — id, *ad_id*, *reviewer_id*, decision (approved/rejected/changes), comment, decided_at

**platform_connections** — id, platform, account_name, external_account_id, access_token (encrypted), refresh_token (encrypted), token_expires_at, scopes (jsonb), status, last_synced_at

**audiences** — id, name, description, geo (jsonb), demographics (jsonb), interests (jsonb), source_type (custom/retargeting/lookalike), platform_mappings (jsonb)

**creatives** — id, type (image/video/headline/caption/cta/testimonial/before_after), url/storage_key, tags (jsonb), aspect_ratio, approved (bool), version, created_by

**metrics** — id, *ad_id*, date, impressions, clicks, leads, spend, conversions, booked_calls, sales, revenue (all daily rows; roll up in queries)

**audit_log** — id, *user_id*, action, entity_type, entity_id, before (jsonb), after (jsonb), created_at

**notifications** — id, *user_id*, type, payload (jsonb), read, created_at

Key relationships: a **campaign** has many **ads**; an **ad** has many **schedules**, **metrics**, and one current **approval**; **limits/budgets/auto_pause_rules/blackout_dates** attach to any scope via (scope, scope_ref_id).

---

## 8. Automation Logic

Three background workers (queue + scheduler), all driven off the DB:

**A) Scheduler/Poster (runs every minute)**
```
for each schedule where status=queued and scheduled_at <= now:
    ad = schedule.ad
    if global.emergency_stop: skip (leave queued, log)
    if today in blackout(ad): mark skipped, notify
    if not passes_limits(ad):        # volume + min-gap + max-active
        reschedule or mark blocked; notify
        continue
    if not within_budget(ad):        # day/campaign/platform caps
        if hard cap: auto-pause + notify; else require re-approval
        continue
    if ad.status != approved: skip
    result = platform_adapter(ad.platform).publish(ad)
    schedule.external_post_id = result.id; status = posted; ad.status = live
    write audit_log
```

**B) Metrics Sync (every 15–30 min)**
```
for each live ad with a connected platform:
    data = platform_adapter.fetch_insights(ad.external_post_id)
    upsert metrics row (impressions, clicks, spend, leads, conv, revenue)
    upsert spend_records
```

**C) Rule Engine (every 5–15 min, after sync)**
```
for each enabled auto_pause_rule in scope:
    value = evaluate(rule, over rule.window)   # e.g. CPL last 24h
    if breach(value, rule.threshold):
        if rule.action == pause: pause matching ads via platform API; log; notify
        else: create alert notification
budget checks: if spend >= budget(cap_type=hard): pause; if soft: alert + flag re-approval
```

**Emergency Stop:** sets `global.emergency_stop=true`, immediately calls `pause` on every live ad across all connected platforms, blocks the poster, and notifies. Clearing it is a deliberate Admin action (logged).

**Idempotency & safety:** posting writes `external_post_id` and uses a per-schedule lock so a retry never double-posts. All money-affecting actions are transactional and audited.

---

## 9. AI Ad Generation Workflow

Reuses the existing Claude generator (`claude-opus-4-8`, structured outputs).

```
User (Create Ads) → POST /api/generate
  → build system prompt from brand (voice, differentiators, MUST-AVOID rules)
  → build user prompt from platform norms + offer + audience + goal + tone + count
  → Claude call (structured JSON schema: variations[])
  → validate against schema; enforce must_avoid; strip anything non-compliant
  → return typed variations to UI
User edits / selects → Save to campaign (status=draft) → Send to Approval (status=pending)
```

- **Platform-aware:** each platform gets tailored length/format/hashtag guidance (search vs. social vs. video script).
- **Audience-aware:** the chosen saved audience is injected so copy speaks to that buyer.
- **Bulk:** many offers → concurrent generation → one reviewable batch → CSV export.
- **Compliance:** the brand `must_avoid` list is part of the system prompt *and* re-checked after generation (belt and suspenders).
- **Images:** Claude writes the *visual concept* (a designer brief). Actual image generation requires a separate image model — see §14.

---

## 10. Approval Workflow

```
Ad (pending) → Approval Queue
  Approver views platform-accurate preview + audience + budget + schedule + brand-rule check
  → Approve → status=approved (eligible to schedule/post)
  → Approve & Schedule → approved + placed on calendar
  → Request changes → status=draft, comment routed to creator (notification)
  → Reject → status=rejected (reason required, logged)
Rules:
  - If Ad Limits "approval required" = ON, no ad can move to scheduled/live without an approval row.
  - Role gate: only Approver/Manager/Admin can decide.
  - Bulk-approve allowed only for creators/campaigns Admin has whitelisted.
  - Every decision writes to approvals + audit_log.
```

---

## 11. Posting Workflow

```
approved ad → scheduled (calendar) → poster picks it up at scheduled_at
  → re-validate: emergency_stop? blackout? limits? budget? still approved?
  → platform_adapter.publish(ad, audience_mapping, budget, schedule)
       Meta adapter        → Meta Marketing API (FB + IG)
       Google adapter      → Google Ads API (Search / Display / YouTube video)
       TikTok adapter      → TikTok Marketing API
       Pinterest adapter   → Pinterest Ads API
       LinkedIn adapter    → LinkedIn Marketing API
  → store external_post_id; status=live; audit_log
  → on failure: retry w/ backoff (max N), then status=failed + notify
```

- **Adapter pattern:** one interface (`publish`, `pause`, `resume`, `fetch_insights`), one implementation per network. (The repo already scaffolds `publishing.py` with a `PublishingAdapter` interface + Meta/Google stubs — extend it.)
- **Audience mapping:** each saved audience carries per-platform targeting so the adapter can translate it.
- **YouTube note:** YouTube ads are bought through **Google Ads** (video campaigns), not a separate account — one Google connection covers Search/Display/YouTube.

---

## 12. Analytics Workflow

```
Metrics Sync worker → pulls insights per live ad from each platform → metrics table (daily rows)
Derived metrics (query/computed):
   CTR = clicks / impressions
   CPL = spend / leads
   Conversion rate = conversions / clicks
   ROAS = revenue / spend
   Cost per booked call = spend / booked_calls
Dashboards & Analytics tab read rollups (by platform / campaign / audience / offer / creative / time).
Lead & sale attribution:
   - Leads/booked-calls/sales can be pushed in via webhook from CRM/landing pages,
     matched to ad by UTM / external_post_id, and written to metrics.
Exports: CSV/PDF; scheduled email/Slack summaries.
```

---

## 13. Suggested Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | **React + Next.js + TypeScript**, Tailwind + shadcn/ui, Recharts | Premium, fast to build, great component ecosystem |
| Backend API | **FastAPI (Python)** | Already the repo's stack; async, typed, pairs with the Anthropic SDK |
| AI | **Claude API `claude-opus-4-8`** via Anthropic SDK (structured outputs) | Already integrated; on-brand, schema-guaranteed copy |
| Image gen (optional) | dedicated image model (see §14) | Claude does text, not images |
| DB | **PostgreSQL** | Relational integrity for money/limits/audit |
| Cache/queue | **Redis** | Locks, rate-limit counters, job broker |
| Workers/scheduler | **Celery** (or RQ/APScheduler) + beat | Scheduler/poster, metrics sync, rule engine |
| Auth | OAuth/SSO (Google Workspace) + app RBAC; JWT sessions | Internal team login |
| Secrets | Env + a vault/KMS; encrypt platform tokens at rest | Money-moving credentials |
| Hosting | Containers (Docker) on a cloud (Fly/Render/AWS); managed Postgres+Redis | Simple ops |
| Observability | Structured logs, Sentry, uptime checks | Catch posting/spend failures fast |

---

## 14. API Integrations Required

| Integration | Purpose | Notes |
|---|---|---|
| **Anthropic (Claude)** | AI ad copy generation | `claude-opus-4-8`, structured outputs; already wired |
| **Meta Marketing API** | Facebook + Instagram ads | One connection covers both; OAuth, ad-account ID |
| **Google Ads API** | Search + Display + **YouTube** video ads | Needs developer token + OAuth; YouTube = video campaigns here |
| **TikTok Marketing API** | TikTok ads | Business account + app review |
| **Pinterest Ads API** | Pinterest ads | OAuth, ad account |
| **LinkedIn Marketing API** | LinkedIn ads (B2B) | OAuth, ad account; stricter approval |
| **Image generation (choose one)** | Turn visual concepts into images | Claude can't generate images — integrate OpenAI `gpt-image`/DALL·E **or** Google Imagen; pick one, store key in Settings |
| **CRM / Landing page webhook** | Lead / booked-call / sale attribution | Inbound webhook keyed by UTM/external_post_id |
| **Slack/Email** | Notifications (approvals, auto-pause, budgets) | Outbound |

Each ad platform requires app registration, OAuth scopes for ad management, and (for some) app review before production posting — budget setup time for TikTok/Meta/Google approvals.

---

## 15. Security Considerations

- **Encrypt platform tokens at rest** (KMS/Fernet); never expose in API responses; mask in UI.
- **RBAC enforced server-side** on every endpoint — not just hidden buttons. Money/limit actions gated to Admin/Manager.
- **Audit log** for every generate/edit/approve/post/pause/limit-change (who, when, before/after).
- **Idempotent posting** with per-schedule locks → no double-spend on retries.
- **Hard budget caps enforced pre-post** — the poster checks budget/limits *before* calling any platform API.
- **Emergency Stop** is a first-class, always-reachable control.
- **Secrets** in a vault/env, never in the repo; `.env` gitignored (already is).
- **OAuth least privilege** — request only ad-management scopes; token refresh handled server-side.
- **Input validation** on all AI-influenced fields; brand `must_avoid` enforced before anything is publishable.
- **PII care** — audiences/leads may contain personal data; restrict access, retention policy, and comply with platform + privacy rules.
- **Rate limiting & backoff** against each platform API; alert on repeated failures.

---

## 16. MVP Version

Ship the smallest thing that is genuinely useful and safe.

**In:**
- Auth + roles (Admin, Creator, Approver).
- **Create Ads** (Claude generator, single + bulk) — already built.
- **Campaigns** (create/organize/save ads).
- **Approval Queue** (approve/reject/request changes).
- **Ad Limits (core):** max ads/day, max spend/day & per campaign, min time between posts, blackout dates, approval-required, **Emergency Stop**.
- **Budget Manager (core):** daily + per-campaign budgets with spend tracking.
- **Ad Calendar** (schedule + view).
- **Platform Connections + posting for ONE platform first (Meta)** via the adapter interface.
- **Analytics (core):** impressions, clicks, spend, leads, CPL, CTR, ROAS from Meta sync.
- Audit log + notifications (email/Slack).

**Deliberately deferred:** TikTok/Pinterest/LinkedIn/Google adapters, image generation, lookalike audience automation, advanced pacing, A/B automation.

**Why Meta first:** Facebook+Instagram in one API = fastest path to real end-to-end value; other adapters slot into the same interface.

---

## 17. Advanced Version

- **All 7 platforms** live (Meta, Google/YouTube, TikTok, Pinterest, LinkedIn).
- **Full auto-pause suite** (CPL, budget, frequency, CTR, zero-conversion) with per-scope tuning.
- **AI image/video creative** generation and auto-attachment.
- **A/B & multivariate testing** with automatic winner promotion and budget shifting.
- **Smart budget pacing & reallocation** (move spend to best ROAS automatically, within caps).
- **Lookalike & retargeting audience automation** synced from CRM.
- **Predictive suggestions:** "boost this," "your CPL will exceed cap in ~6h," "best time to post."
- **Multi-brand** (Modpools + Modpro + regions) with shared libraries.
- **Full attribution** (lead → booked call → sale → revenue → ROAS) via CRM integration.
- **Scheduled AI reports** and natural-language analytics ("how did spring 16ft do on Meta?").

---

## 18. Wireframe-Style Layout Descriptions

Global shell: **left sidebar nav** (tabs from §4), **top bar** (brand switcher, search, notifications bell, user menu, and a persistent **Emergency Stop** for Admin/Manager), **main content area**.

**Dashboard**
```
┌──────────────────────────────────────────────────────────────┐
│ [Active:12] [Spend $1.2k/$2k] [Leads 38] [CTR 2.1%] [CPL $61] [ROAS 3.4x] │
├───────────────────────────────┬──────────────────────────────┤
│ Spend vs Budget (bars, day/mo)│ Approval Queue: 5 pending  →  │
│ ▓▓▓▓▓▓░░ 60% today            │ Alerts: 2 auto-paused ⚠       │
├───────────────────────────────┴──────────────────────────────┤
│ Next 7 days ▸ [FB][IG][G]……  calendar strip                   │
│ Top performers ▲   |   Bottom performers ▼ (quick pause)      │
└──────────────────────────────────────────────────────────────┘
```

**Create Ads**
```
┌ Left: Brief form ─────────┐ ┌ Right: Results ───────────────┐
│ [Single | Bulk] tabs      │ │ Variation 1  [Copy][Edit]     │
│ Brand ▾  Platform ▾       │ │  Headline / Primary / Desc    │
│ Offer / angle  [textarea] │ │  CTA · #tags · Visual concept │
│ Audience ▾  Goal ▾  Tone  │ │  [Save to campaign][Approve]  │
│ Variations ▾  [Generate]  │ │ Variation 2 …                 │
└───────────────────────────┘ └───────────────────────────────┘
```

**Ad Limits**
```
Global | Per-Platform | Per-Campaign   (tabs)
Volume:  Max/day [ 5 ]  Max/week [25]  Max/month [80]  Min gap [120m]
Spend:   Max/day [$400]  Max/campaign [$4000]  Max/platform [$1500]  (soft/hard)
Control: [x] Approval required   [ EMERGENCY STOP ]
Auto-pause:  [x] CPL > [$75] over [24h]  [x] Budget reached  [x] Freq > [3.5]/7d
Blackout dates: [ Apr 12–14 · store closure ]  [+ add]
── Effective limits preview for a selected ad ──
```

**Approval Queue**
```
Pending (5) | Approved | Rejected
┌ Card: [FB preview] "Summer 16ft…"  Audience: Compact-backyard │
│  Budget $400/day · Sched Apr 9 9am · ✅ brand-rules pass       │
│  [Approve] [Approve & Schedule] [Request changes] [Reject]    │
```

**Ad Calendar**: month grid, platform-colored chips, shaded blackout days, "3/5 daily slots" badge per day, drag to reschedule.

**Analytics**: funnel bar (impr→click→lead→call→sale) up top; filter chips (platform/campaign/audience/offer/date); line + bar charts; table with export.

---

## 19. Example Prompts Used Inside the App

**Ad generation — system prompt (per brand):**
```
You are a senior performance-marketing copywriter for Modpools (premium
container swimming pools & spas). Write distinct, on-brand ad variations that
respect the brand voice and only make claims the brand is allowed to make.
VOICE: {brand.voice}
DIFFERENTIATORS: {brand.differentiators}
MUST NOT (never violate): {brand.must_avoid}   # no fixed prices, no install-time
                                               # guarantees, no safety guarantees
Each variation takes a genuinely different angle. Output only the requested JSON.
```

**Ad generation — user prompt (per request):**
```
Write {count} ad variations for Modpools.
Platform: {platform}  ({platform_format_guidance})
Goal: {goal}   Audience: {audience_description}   Tone: {tone}
Offer / angle: {offer}
Each variation: headline, primary_text, description, call_to_action,
hashtags (empty when platform has none), visual_concept (designer brief), rationale.
```

**Image concept → image model prompt (advanced):**
```
Premium lifestyle photo for Modpools. A {product_size} container pool with acrylic
window in an upscale {market} backyard at golden hour. Clean, aspirational, real —
no text overlays. Aspect {aspect_ratio}. Concept: {visual_concept}.
```

**Analytics assistant (advanced, natural-language):**
```
Given these campaign metrics {json}, summarize performance for a marketing manager:
best/worst by ROAS and CPL, what to scale, what to pause, and one concrete next step.
Be specific and brief; do not invent numbers not in the data.
```

**Auto-pause explanation (user-facing):**
```
Explain in one plain sentence why this ad was auto-paused, given rule {rule}
and observed {value} over {window}. No jargon.
```

---

## 20. Developer Instructions (How to Build It)

**Phase 0 — foundation (exists):** FastAPI + Claude generator, brand profiles, single/bulk generation, `publishing.py` adapter interface + Meta/Google stubs, `analytics.py` stub. Keep the model `claude-opus-4-8` and the brand profiles as-is.

**Phase 1 — persistence & auth**
1. Add PostgreSQL + migrations (Alembic). Create tables from §7.
2. Add auth (Google SSO or email) + RBAC middleware (§3). Gate every route by role.
3. Wrap the existing generator: on generate, persist `ads` (status=draft) tied to a `campaign`.

**Phase 2 — campaigns, approval, calendar**
4. Campaigns CRUD + organization filters.
5. Approval Queue: `approvals` table, endpoints, and the state machine (§10). Enforce "approval required."
6. Ad Calendar + `schedules` (create/reschedule with validation).

**Phase 3 — limits, budgets, safety**
7. `limits`, `budgets`, `auto_pause_rules`, `blackout_dates` + the effective-limit resolver (§5.6).
8. **Emergency Stop** flag + global pause action.
9. Redis counters for volume/min-gap enforcement.

**Phase 4 — posting (Meta first)**
10. Implement `MetaAdapter.publish/pause/resume/fetch_insights` against the Meta Marketing API. OAuth in Platform Connections; encrypt tokens.
11. Build the **Scheduler/Poster** worker (§8A) with idempotent posting + retries.

**Phase 5 — analytics & automation**
12. **Metrics Sync** worker (§8B) → `metrics`/`spend_records`. Derived metrics + Dashboard/Analytics UIs.
13. **Rule Engine** worker (§8C): auto-pause + budget enforcement + notifications.

**Phase 6 — expand**
14. Add remaining adapters (Google/YouTube, TikTok, Pinterest, LinkedIn) behind the same interface.
15. Image generation, A/B automation, budget reallocation, CRM attribution (§17).

**Cross-cutting (every phase):** write to `audit_log`, add tests around limit/budget enforcement (money-critical), keep secrets in env/vault, and keep the UI review-first (AI drafts → human approves → system posts).

**Definition of done for MVP:** a Creator can generate → save → submit; an Approver approves; the ad schedules and posts to Meta within limits/budget; the Dashboard shows real spend/CPL/ROAS; auto-pause and Emergency Stop both provably work.

---

*End of plan.*
