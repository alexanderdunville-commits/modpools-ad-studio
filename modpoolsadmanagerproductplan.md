# Modpools Ad Manager — Complete Product Plan

**Version:** 1.0 · **Prepared for:** Modpools Marketing
**Builds on:** the existing `modpools-ad-studio` codebase (FastAPI + Claude API). Nothing in that repo is throwaway — the current app becomes the **Create Ads** tab, and its publishing/analytics scaffolds become the posting and analytics engines.

---

## 1. App Overview

**Modpools Ad Manager** is an internal advertising operations platform for the Modpools marketing team. It closes the full loop:

> **Generate (AI) → Organize → Approve → Schedule → Post (within limits) → Measure → Auto-protect (pause) → Learn → Generate again.**

One place to create on-brand ads with AI, hold them behind an approval gate, schedule them across seven platforms (Facebook, Instagram, Google, YouTube, TikTok, Pinterest, LinkedIn), enforce hard spending and posting limits so nothing runs away, and see performance in one dashboard instead of seven ad managers.

**Design principles**
1. **Nothing posts without passing the limit chain.** Every post attempt runs the same server-side checks — no UI path around them.
2. **Humans approve, machines enforce.** AI generates and recommends; a person approves; automation enforces budgets, caps, and pauses.
3. **Premium but simple.** A salesperson should be able to read the dashboard; a coordinator should be able to ship an ad in under five minutes.
4. **Platform-agnostic core.** Ads, budgets, and limits live in *our* database; platforms are adapters. Adding platform #8 never requires a schema change.

---

## 2. Main Features

| Area | Features |
|---|---|
| **AI Creation** | Brand-grounded ad generation (copy + visual concepts) per platform/audience/angle; variation-on-winner; compliance pre-check; brand voice locked in profiles |
| **Organization** | Campaigns tagged by offer, market, product size, season, audience; creative library; saved audiences |
| **Control** | Post-count limits (day/week/month, per platform), spend limits (day/campaign/platform), approval gate, minimum gap between posts, blackout dates, emergency stop |
| **Automation** | Scheduler that posts within limits; auto-pause on CPL, budget, and frequency thresholds; token refresh; metrics sync |
| **Workflow** | Approval queue with approve/reject/request-changes + notes; audit trail of every action |
| **Distribution** | One-click posting to connected platforms via adapters; retry + idempotency; dry-run mode |
| **Measurement** | Unified metrics (impressions, clicks, leads, CPL, conversions, booked calls, sales, ROAS); per-campaign/platform/audience breakdowns; AI weekly insights |
| **Administration** | Roles & permissions, brand voice settings, notifications (email/Slack), encrypted API credentials |

---

## 3. User Roles

| Role | Can do | Cannot do |
|---|---|---|
| **Admin** | Everything: settings, platform connections, limits, budgets, users, emergency stop | — |
| **Manager** | Approve/reject ads, edit budgets & limits (within admin-set ceilings), pause/stop ads, manage campaigns, view analytics | Manage users, edit API connections |
| **Creator** | Generate/edit ads, build audiences, upload creatives, submit for approval, schedule *approved* ads | Approve ads (including their own), change limits/budgets, connect platforms |
| **Viewer** | Read-only dashboard, analytics, calendar | Any write action |

Rules enforced server-side: creators can never approve their own ads; only Admin can clear an emergency stop; every privileged action writes to the audit log.

---

## 4. Tab-by-Tab Breakdown

### 4.1 Dashboard
The morning-coffee view. Top row of stat cards: **Active campaigns · Spend today / this month vs budget · Leads (7d) · CTR (7d) · CPL (7d) · ROAS (30d)**. Below: "Scheduled next 7 days" list (ad, platform, time, status), "Needs attention" panel (pending approvals, auto-paused ads with reasons, failed posts, expiring tokens), and a spend-by-platform bar. A thin banner turns red app-wide when the **emergency stop** is active.

### 4.2 Create Ads
The existing AI generator, expanded. Pick brand → platform (now all seven) → product/offer → audience (from Audience Builder or free text) → goal → tone → variation count. Output cards show headline, primary text, description, CTA, hashtags, visual concept, and rationale — with per-card actions: **Save to campaign · Edit · Regenerate this one · Submit for approval**. A "Generate variations of a winner" mode takes an existing high-performing ad as the seed. Every generation is logged (prompt, model, cost) for later analysis.

### 4.3 Campaigns
Table + kanban of campaigns. Fields: name, brand, **offer** (e.g. "Spring install window"), **market** (region), **product size** (e.g. 8×20, 8×40), **season**, primary audience, status (draft/active/paused/completed), date range, budget snapshot, ad count by status. Campaign detail page shows its ads, spend vs budget, schedule, and performance. Filters and saved views for every tag dimension.

### 4.4 Ad Calendar
Month/week views of every scheduled and posted ad. Color = platform; icon = status (pending approval ⏳, approved & scheduled ✅, posted 📤, blocked 🚫, paused ⏸). Blackout dates render as striped days. Drag-to-reschedule (re-runs the limit check on drop). Clicking a day opens its queue; a "capacity" ribbon shows posts-remaining-today against the daily limit.

### 4.5 Ad Limits
The control room — full detail in **Section 5**.

### 4.6 Budget Manager
Hierarchy view: **Account → Platform → Campaign**, each with daily / weekly / monthly / lifetime budget rows, amount spent (live from metrics sync), remaining, and a projected-end-of-month line. Editing a budget requires Manager+; lowering a budget below current spend prompts an immediate pause decision. Currency fixed per account (CAD/USD setting).

### 4.7 Approval Queue
A reviewable feed of ads in `pending_approval`, newest first, filterable by platform/campaign/creator. Each card shows the full ad exactly as it will appear (copy, creative, audience, schedule, budget impact) plus AI compliance-check flags. Actions: **Approve** (moves to `approved`), **Reject** (requires a note), **Request changes** (returns to `draft` with a note). Bulk approve for trusted batches. Mobile-friendly — managers approve from a phone.

### 4.8 Platform Connections
One card per platform: connection status, account name/ID, token health (expires in X days), granted scopes, last successful sync, and a **Test connection** button. OAuth connect/reconnect flows. Per-platform toggle: *enabled for posting* (lets you connect an account but keep it read-only for metrics first). Shows which limits reference the platform.

### 4.9 Audience Builder
Create and save named audiences: **Luxury Homeowners · Airbnb & STR Hosts · Vacation-Home Owners · Compact-Backyard Buyers · Requested Pricing (retargeting)** ship as starters. Each audience stores: description (used by the AI generator for targeting-aware copy), demographic/interest criteria, and per-platform mapping (e.g. Meta interest IDs, Google audience segments) filled in as platforms are connected. Audiences attach to ads and campaigns; performance is reportable by audience.

### 4.10 Creative Library
Asset manager for **images, videos, headlines, captions, CTAs, testimonials, before/after visuals**. Each asset: type, tags (product size, season, campaign angle), usage count, and performance rollup ("this hero video appears in 6 ads, avg CTR 2.1%"). Text assets (winning headlines/CTAs) are first-class so the AI can be pointed at proven copy. Upload, search, filter; storage on S3-compatible object store.

### 4.11 Analytics
Unified reporting across platforms: impressions, clicks, CTR, spend, **leads, CPL, conversions, booked calls, sales value, ROAS**. Breakdowns by campaign, platform, audience, offer, and creative. Time-series charts with period comparison. A funnel view (impressions → clicks → leads → booked calls → sales). "AI Insights" panel: weekly Claude-written summary of what to scale, pause, and test next. CSV export for everything.

### 4.12 Settings
- **Users & roles** (invite, deactivate, role changes)
- **Brand voice** (the brand profiles — description, voice, differentiators, proven angles, must-avoid rules — editable here instead of in code)
- **Company details** (name, site, UTM defaults, timezone, currency)
- **Notifications** (email/Slack per event: approval needed, auto-pause fired, budget 80%/100%, post failed, token expiring)
- **API keys** (Anthropic key, platform app credentials — write-only fields, never displayed after save)

---
## 5. Ad Limits Tab — Detailed Design

This tab is the app's safety system. Every rule here is enforced **server-side in one function** (`check_limits`) that runs before *any* post attempt, whether triggered by the scheduler, a manual "post now," or an API call.

### 5.1 Limit types

| Group | Rule | Example | Blocks / triggers |
|---|---|---|---|
| **Volume** | Max ads posted per day | 5/day | Post attempt blocked, rescheduled to next slot |
| | Max ads posted per week | 20/week | Same |
| | Max ads posted per month | 60/month | Same |
| | Max ads per platform (concurrent live) | 10 live on Meta | Blocks new posts to that platform |
| | Minimum time between posts | 90 min (global and/or per platform) | Delays post to next eligible time |
| **Spend** | Max spend per day (account) | $500/day | New posts blocked; optional auto-pause of live ads |
| | Max spend per campaign | $3,000 lifetime | Campaign's ads auto-paused at 100% |
| | Max spend per platform | $2,000/mo on TikTok | Platform posts blocked / paused |
| **Governance** | Approval required before posting | ON (default) | Unapproved ads can be scheduled but never posted |
| | Blackout dates | Dec 24–26; site-maintenance days | No posts on those dates; calendar shows striped |
| | **Emergency stop** | Big red button | Immediately pauses all live ads on all platforms + halts scheduler until an Admin clears it |
| **Auto-pause** | CPL too high | Pause ad if CPL > $80 after ≥ $150 spend | Pauses the ad, notifies |
| | Budget reached | Pause scope at 100% of its budget | Pauses campaign/platform scope |
| | Frequency too high | Pause ad if frequency > 3.5 (7-day) | Pauses the ad, notifies |

### 5.2 Evaluation order (the limit chain)

```
1. EMERGENCY STOP active?            → block everything
2. Blackout date (account tz)?       → block, reschedule next allowed day
3. Ad approved? (if gate ON)         → block, notify creator
4. Platform connected + enabled?     → block, notify admin
5. Volume: day/week/month counts     → block, auto-reschedule
6. Volume: per-platform live count   → block
7. Spend: day / campaign / platform  → block (projected spend incl. this ad's budget)
8. Min-gap since last post           → delay to earliest eligible minute
   → ALL PASS → dispatch to platform adapter
```

Every blocked attempt writes `post_log` with the failing rule and a human-readable reason ("Blocked: daily post limit 5/5 reached — rescheduled to tomorrow 9:00"), and surfaces in Dashboard → Needs attention.

### 5.3 Auto-pause rules — safeguards against false triggers

- **Learning floor:** CPL rule ignores ads below a minimum spend (default $150) so a $12 ad with one bad morning doesn't get killed.
- **Cool-down:** an auto-paused ad can't be auto-resumed; a human resumes it (the pause reason is shown on the ad).
- **Scope clarity:** budget pauses act on the scope that breached (campaign budget → that campaign's ads only).
- **Notification always:** every auto-pause sends email/Slack with the metric, threshold, and a one-click link to the ad.

### 5.4 UI layout

Three columns of grouped cards — **Volume · Spend · Protection** — each rule a row: toggle, value input, scope selector (global / platform / campaign), "last triggered" timestamp. Emergency stop is a separate full-width red card at top with confirmation modal ("This pauses N live ads across M platforms"). Blackout dates managed on an inline mini-calendar. A right-rail "simulator": pick a hypothetical ad + time, see which rule would block it.

---

## 6. Example User Flow

**Monday, 9:00 — Jess (Creator)** opens **Create Ads**: brand Modpools, platform Facebook + Instagram + Pinterest, offer "Spring install window — swim by summer," audience "Compact-Backyard Buyers," 4 variations each. Reviews 12 cards, edits two headlines, saves all to campaign **"Spring 2027 — Small Yards"**, schedules them across the next two weeks (calendar shows capacity remaining per day), and submits for approval.

**Monday, 12:30 — Marco (Manager)** gets a Slack ping: *"12 ads pending approval."* On his phone he approves 10, rejects one ("price implied — remove 'fraction of the cost'"), requests changes on one ("swap hero image to the window shot"). Approved ads flip to `approved`; their schedule slots turn green on the calendar.

**Tuesday, 9:00 — Scheduler** wakes, finds 2 ads due, runs the limit chain: daily cap 5 (0 used ✓), spend caps ✓, min-gap ✓ → posts both via the Meta adapter, records external IDs, marks them `live`.

**Thursday, 14:00 — Auto-pause** monitor syncs metrics and finds one ad at CPL $96 after $180 spend (threshold $80/$150) → pauses it on Meta, logs the reason, notifies Marco. He opens **Analytics**, sees the sibling variation at CPL $41, and shifts the remaining budget to it.

**Friday — Dana (Admin)** checks **Dashboard**: spend pacing 62% of monthly budget, ROAS 4.1. The AI weekly insight suggests scaling the "small yards" angle on Pinterest, where CPL is lowest. She bumps the Pinterest platform budget in **Budget Manager**.

---

## 7. Database Structure (PostgreSQL)

```
users            (id, email, name, role, is_active, created_at)
brands           (id, key, name, tagline, description, audience, voice,
                  differentiators jsonb, proven_angles jsonb, must_avoid jsonb)
platform_connections
                 (id, platform, account_external_id, account_name, status,
                  access_token_enc, refresh_token_enc, token_expires_at,
                  scopes jsonb, posting_enabled bool, last_sync_at, connected_by)
campaigns        (id, name, brand_id, offer, market, product_size, season,
                  status, start_date, end_date, primary_audience_id, created_by)
audiences        (id, name, description, criteria jsonb,
                  platform_mappings jsonb, created_by)
creatives        (id, type, file_url, text_content, tags jsonb, brand_id,
                  uploaded_by, created_at)
ads              (id, campaign_id, platform, status, headline, primary_text,
                  description, cta, hashtags jsonb, visual_concept,
                  audience_id, creative_ids jsonb, source, generation_id,
                  external_ad_id, budget_amount, budget_period,
                  created_by, approved_by, approved_at, paused_reason)
generations      (id, brand_id, prompt_snapshot, model, input_tokens,
                  output_tokens, created_by, created_at)
schedules        (id, ad_id, scheduled_at, timezone, status,
                  blocked_reason, posted_at)
limit_rules      (id, rule_type, scope, scope_ref, value_num, active,
                  last_triggered_at, updated_by)
blackout_dates   (id, start_date, end_date, reason, created_by)
budgets          (id, scope, scope_ref, period, amount, currency, updated_by)
approvals        (id, ad_id, action, actor_id, note, created_at)
post_log         (id, ad_id, schedule_id, platform, attempted_at, result,
                  external_id, error, limits_snapshot jsonb)
metrics_daily    (id, ad_id, date, impressions, clicks, spend, leads,
                  conversions, booked_calls, sales_value, frequency,
                  synced_at)  UNIQUE(ad_id, date)
system_state     (id=1, emergency_stop bool, stopped_by, stopped_at, note)
audit_log        (id, actor_id, action, entity, entity_id,
                  before jsonb, after jsonb, created_at)
notification_prefs (id, user_id, event_type, channel, enabled)
```

**Ad status enum:** `draft → pending_approval → approved → scheduled → live → paused | stopped | completed`, plus `rejected` and `failed`. Only the server transitions statuses; the audit log records every transition.

---

## 8. Automation Logic

### 8.1 Scheduler tick (every minute)

```python
def scheduler_tick():
    if system_state.emergency_stop:
        return
    due = Schedule.where(status="pending", scheduled_at <= now())
    for s in due:
        verdict = check_limits(s.ad, at=now())        # Section 5.2 chain
        if verdict.blocked:
            s.mark_blocked(verdict.reason)
            if verdict.reschedulable:
                s.reschedule(verdict.next_eligible_at)
            notify_if_needed(verdict)
        else:
            result = adapters[s.ad.platform].publish(s.ad,
                        idempotency_key=f"ad-{s.ad.id}-sched-{s.id}")
            record_post_log(s, result)
            s.mark_posted() if result.ok else s.mark_failed(result.error)
```

### 8.2 Metrics sync (hourly per connected platform)

Pull yesterday+today insights per external ad ID → upsert `metrics_daily` → recompute derived rollups (campaign/platform/day spend) used by the limit chain and Budget Manager.

### 8.3 Auto-pause monitor (every 30 min, after sync)

```python
for ad in Ad.where(status="live"):
    m = ad.metrics_window(days=7)
    if m.spend >= learning_floor and m.cpl > rule(cpl_pause_threshold):
        pause(ad, reason=f"CPL ${m.cpl:.0f} > ${threshold} after ${m.spend:.0f} spend")
    if m.frequency > rule(frequency_pause_threshold):
        pause(ad, reason=f"Frequency {m.frequency:.1f} > {threshold}")
for scope in budget_scopes():           # campaign / platform / account-day
    if scope.spend >= scope.budget:
        pause_scope(scope, reason="Budget reached")
```

`pause()` calls the platform adapter, sets `paused_reason`, writes audit + notification. Auto-paused ads require human resume.

### 8.4 Housekeeping jobs

Token refresh (daily, warn at 14 days to expiry) · schedule health (flag `approved` ads with past-due slots) · weekly AI insights generation · audit-log retention.

---

## 9. AI Ad Generation Workflow

1. **Input:** brand profile (from Settings → Brand voice — the current `brands.py` data, moved to the DB), platform, product/offer, audience (saved audience description or free text), goal, tone, count.
2. **Prompt assembly:** system prompt = brand context + differentiators + proven angles + hard rules (`must_avoid`); user prompt = campaign brief + platform format guidance (already implemented in `generator.py`).
3. **Call:** Claude API (`claude-opus-4-8`), adaptive thinking, **structured outputs** (JSON schema) so responses are always parseable. Effort configurable (Settings).
4. **Post-check (AI compliance pass):** a second, cheap call reviews the drafts against `must_avoid` and platform policy basics (e.g., no prohibited claims), flagging rather than blocking.
5. **Persist:** save drafts as `ads` in `draft`, plus a `generations` row (prompt snapshot, token usage → cost tracking).
6. **Human loop:** creator edits, attaches creatives from the Library, submits → `pending_approval`.
7. **Learning loop (advanced):** "generate variations of a winner" seeds the prompt with the top ad's copy + its metrics; weekly insights feed angle recommendations back into Create Ads.

## 10. Approval Workflow

```
draft ──submit──▶ pending_approval ──approve──▶ approved ──schedule──▶ scheduled
   ▲                    │  │                                          │
   │◀──request changes──┘  └──reject──▶ rejected (terminal, note      └─▶ live
   └───────── creator edits and resubmits ────────┘        required)
```

- Approval gate is a **limit rule** (ON by default). Even with it OFF, rejected ads never post.
- Approvers see exactly what will run: rendered copy, creative, audience, schedule, budget impact, compliance flags.
- Creators cannot approve their own ads. All actions require a note on reject/request-changes. Everything lands in `approvals` + `audit_log`.

## 11. Posting Workflow

- **Adapter interface** (one per platform): `publish(ad) · pause(ad) · resume(ad) · stop(ad) · fetch_metrics(range) · test_connection()`. The existing `publishing.py` stubs grow into these.
- **Idempotency:** every publish carries an idempotency key (`ad-{id}-sched-{id}`); retries can't double-post.
- **Retries:** transient failures retry 3× with backoff; hard failures mark the schedule `failed` and notify.
- **Dry-run mode:** per-platform toggle logs what *would* post without calling the API — used during rollout and for testing limits.
- **Mapping note:** "posting an ad" on Meta/Google means creating campaign → ad set/ad group → ad via their APIs; the adapter owns that ceremony and stores the external IDs for metrics and pause calls. YouTube ads run through the Google Ads adapter.

## 12. Analytics Workflow

1. Hourly sync writes `metrics_daily` per ad (Section 8.2).
2. **Leads** come from platform lead objectives *or* UTM-tagged site conversions (every posted ad gets auto-UTMs: `utm_campaign={campaign}`, `utm_content={ad_id}`).
3. **Booked calls & sales** enter via CRM webhook (HubSpot/Salesforce/etc.) or manual entry in MVP, matched on lead → ad UTM.
4. Derived metrics computed at query time: CTR, CPL, cost/conversion, **ROAS = sales_value ÷ spend**.
5. Dashboards read pre-aggregated rollups (campaign/platform/audience/day) refreshed after each sync.
6. **Weekly AI insight:** metrics tables → Claude with an analyst prompt (Section 19) → written summary stored + notified.

---
## 13. Suggested Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12 + FastAPI** | Continuity with the existing codebase; async-friendly; typed |
| ORM / migrations | SQLAlchemy 2 + Alembic | Standard, boring, reliable |
| Database | **PostgreSQL 16** | jsonb for flexible fields; rock-solid aggregates |
| Jobs | **APScheduler** (MVP) → **Celery + Redis** (advanced) | Start in-process, one dependency; graduate when volume demands workers |
| AI | **Anthropic SDK, `claude-opus-4-8`** | Already integrated with structured outputs + adaptive thinking |
| Frontend | **React + TypeScript (Vite) + Tailwind + shadcn/ui**, TanStack Query | 13 tabs outgrow the current single HTML page; shadcn gives the premium-clean look fast |
| Charts | Recharts | Simple, good-looking defaults |
| Auth | Session-based with server roles (or Clerk/Auth0 to move faster) | Small internal team |
| Storage | S3-compatible (S3 / R2) | Creative Library assets |
| Notifications | Email (Resend/SES) + Slack webhook | The two channels the team lives in |
| Hosting | Railway / Render / Fly.io + managed Postgres | Internal tool scale; easy deploys |
| Errors/logs | Sentry + structured JSON logs | Debugging failed posts is the #1 support task |

## 14. API Integrations Required

| Platform | API | Auth | Notes / lead time |
|---|---|---|---|
| Facebook + Instagram | **Meta Marketing API** | OAuth2 (business system user) | One adapter covers both; `ads_management` + `ads_read` need Meta app review — **apply early (weeks)** |
| Google + YouTube | **Google Ads API** | OAuth2 + developer token | Developer token approval process; YouTube video campaigns run through this same API |
| TikTok | **TikTok Marketing API** | OAuth2 | Business account + app approval |
| Pinterest | **Pinterest Ads API** | OAuth2 | Straightforward; good docs |
| LinkedIn | **LinkedIn Marketing API** | OAuth2 | Requires Marketing Developer Platform access — longest approval; schedule last |
| CRM (leads/sales) | HubSpot/Salesforce webhook or CSV | API key | Feeds booked calls + sales for ROAS |
| AI | Anthropic API | API key | Already in place |

**Reality check for planning:** platform app reviews are the long pole — file Meta and Google applications during MVP week 1, not when the adapter is ready.

## 15. Security Considerations

- **Token storage:** platform OAuth tokens encrypted at rest (Fernet key from env / cloud KMS); never returned by any API; masked in UI.
- **RBAC on the server:** every route checks role; approval, limits, budgets, emergency stop, and connections are privileged endpoints. The UI hiding a button is not the control.
- **No approval bypass:** posting goes through the single `check_limits` + dispatch path. There is deliberately no "force post" endpoint.
- **Audit everything:** approvals, limit edits, budget edits, manual pauses, emergency stops, connection changes — actor, before/after, timestamp.
- **Secrets hygiene:** `.env`/secret manager only; write-only key fields in Settings; separate staging vs production platform apps.
- **Webhooks:** CRM webhook signed (HMAC) and verified.
- **Least privilege on platforms:** request only ads scopes; use dedicated ad accounts; posting toggle OFF by default on new connections.
- **Sessions:** HTTPS-only cookies, CSRF protection, short-lived sessions for Admin actions.

## 16. MVP Version (build this first — 4–6 dev-weeks)

**Goal: one platform, full loop, all safety rails.**

- Tabs: **Dashboard (basic) · Create Ads · Campaigns · Approval Queue · Ad Limits (core) · Ad Calendar (view + reschedule) · Platform Connections (Meta only) · Settings (users, brand voice, keys)**
- AI generation: already built — port `generator.py`/`brands.py`, add save-to-campaign + submit-for-approval
- Limits: daily/weekly/monthly post caps, daily spend cap, approval gate, min-gap, blackout dates, **emergency stop**
- Posting: **Meta adapter only** (Facebook + Instagram), with dry-run mode; manual "post now" + scheduler
- Metrics: daily Meta insights sync → Dashboard cards + simple per-campaign table; leads via Meta lead objective; CPL computed
- Roles: Admin / Manager / Creator
- Out of scope for MVP: auto-pause rules (manual pause exists), Budget Manager tab (single account-level caps in Ad Limits instead), Creative Library, Audience Builder (free-text audiences), other platforms, ROAS (needs sales data)

## 17. Advanced Version (the full app in this document)

Adds: all seven platforms · **auto-pause engine** (CPL / budget / frequency) · full **Budget Manager** hierarchy · **Creative Library** with performance rollups · **Audience Builder** with per-platform mappings · **Analytics** with funnel, booked calls + sales via CRM webhook, ROAS · AI weekly insights + variation-on-winner · bulk approvals · Slack notifications · Celery workers · Viewer role · audit-log UI.

## 18. Wireframe-Style Layout Descriptions

**Global shell:** left sidebar (logo, 13 tab icons+labels, user chip at bottom) · top bar (page title, global search, notification bell, red EMERGENCY STOP banner slot) · content area, max-width 1440, generous whitespace, card-based. Dark-on-light, one accent color (Modpools teal), rounded-2xl cards, subtle shadows.

- **Dashboard:** 6 stat cards in a row → 2-col row: "Scheduled next 7 days" list (left, 2/3) + "Needs attention" stack (right, 1/3) → full-width spend-by-platform bar chart.
- **Create Ads:** left form panel (~380px, sticky) with brand/platform/offer/audience/goal/tone/count + Generate button; right result grid of ad cards, each with action row (Save · Edit · Regenerate · Submit).
- **Campaigns:** filter bar (offer, market, size, season, audience, status) → table with status pills and spend bars; row click → detail page: header stats, tabs (Ads / Schedule / Performance).
- **Ad Calendar:** month grid, platform-colored chips per day, striped blackout days, capacity ribbon under each day header; right drawer opens on chip click with ad preview + reschedule.
- **Ad Limits:** full-width red Emergency Stop card → three columns (Volume / Spend / Protection) of rule rows (toggle · value · scope · last triggered) → blackout mini-calendar → right-rail limit simulator.
- **Budget Manager:** indented tree table (Account ▸ Platform ▸ Campaign) with columns: period, budget, spent, remaining, projected, progress bar (green→amber→red).
- **Approval Queue:** vertical feed of full-preview cards; sticky action bar per card (Approve / Request changes / Reject); filter chips on top; count badge in sidebar.
- **Platform Connections:** 7 cards in a grid — logo, status dot, account, token expiry, Test / Reconnect buttons, "posting enabled" toggle.
- **Audience Builder:** left list of saved audiences; right editor: name, description, criteria builder rows, per-platform mapping accordion, "used by N ads" footer.
- **Creative Library:** masonry grid with type filter tabs (Images · Videos · Headlines · CTAs · Testimonials · Before/After); asset drawer shows usage + performance.
- **Analytics:** date-range + compare picker → KPI row → line chart (metric selector) → breakdown table with dimension switcher (Campaign / Platform / Audience / Offer / Creative) → funnel strip → AI Insights panel.
- **Settings:** left vertical sub-nav (Users · Brand voice · Company · Notifications · API keys); brand-voice editor mirrors the brand profile fields with helper text.

## 19. Example Prompts Used Inside the App

**A) Ad generation — system prompt (already live in `generator.py`):** brand context + differentiators + proven angles + hard rules; user prompt carries the campaign brief and platform format guidance. (See repo.)

**B) Variation-on-winner:**
> Here is a live ad and its 30-day results: [ad JSON] — CTR {ctr}%, CPL ${cpl}. Write {n} new variations that keep the working elements (angle, offer framing) but vary the hook style: one curiosity-led, one pain-first, one identity-led ("become the house everyone swims at"). Same platform constraints and hard rules as above. For each, one sentence on what you changed and why it might beat the original.

**C) Compliance pre-check (runs after generation, flags only):**
> Review these ad drafts against the rules: no specific prices or financing terms, no permit/timeline guarantees, no zero-maintenance claims, no fabricated statistics or revenue claims, and no obvious ad-policy problems (personal attributes, before/after health claims). Return JSON: for each ad, {flags: [{rule, quote, severity}]} — empty list if clean.

**D) Weekly analytics insight:**
> You are a paid-media analyst for Modpools (premium container pools). Here are per-ad metrics for the last 14 days and the prior 14 days: [tables]. Write a 5-bullet summary for a marketing manager: (1) what to scale and why, (2) what to pause/fix, (3) best platform this period on CPL, (4) one audience or angle insight, (5) one test to run next week. Plain language, reference specific ads/campaigns by name, no metric dumps.

**E) Audience-aware brief helper (Create Ads assist):**
> Given the saved audience "{name}: {description}", suggest the 3 proven angles (from the brand profile) most likely to convert this audience, with a one-line reason each. Return JSON.

## 20. Developer Instructions

**Repo:** grow `modpools-ad-studio` — don't start over. Suggested layout:

```
app/
  api/            # FastAPI routers per tab (ads, campaigns, limits, budgets, ...)
  core/           # config, auth, rbac, audit
  db/             # SQLAlchemy models + Alembic migrations (Section 7)
  services/
    generator.py  # exists — AI generation
    limits.py     # check_limits() — the Section 5.2 chain (write FIRST, test HARD)
    scheduler.py  # tick loop (Section 8.1)
    autopause.py  # monitor (Section 8.3)
    insights.py   # weekly AI summary
  adapters/
    base.py       # publish/pause/resume/stop/fetch_metrics/test_connection
    meta.py       # M3
    google.py tiktok.py pinterest.py linkedin.py   # advanced
  web/            # React app (Vite) — or keep static/ until M4
docs/             # this plan, campaign deck
```

**Build order (each milestone is shippable):**
- **M0 (wk 1):** Postgres + models + migrations; auth + roles; audit log; file Meta & Google API applications **now**.
- **M1 (wk 2):** Port generator to DB-backed brands; Create Ads → save to Campaigns; Campaigns tab.
- **M2 (wk 3):** `limits.py` with unit tests for every rule + the chain order; Approval Queue; ad status state machine; Ad Limits tab; emergency stop; scheduler in **dry-run**.
- **M3 (wk 4–5):** Meta adapter (publish/pause/metrics); Platform Connections; go live behind daily caps; Dashboard v1; Calendar.
- **M4 (wk 6+):** Budget Manager; auto-pause engine; Analytics v1; notifications.
- **M5+:** Remaining platform adapters (as API approvals land); Creative Library; Audience Builder; AI insights; React shell if not already done.

**Ground rules:** the limit chain is one function with one call site — test it before anything can post; adapters never bypass it. Dry-run defaults ON for any new platform. Seed data: 2 brands, 3 campaigns, 20 ads across statuses, fake metrics — so every tab demos without live accounts. Write the Meta adapter against a sandbox ad account first.

---

*End of plan. Sections 5 (limits), 7 (schema), 8 (automation), and 20 (build order) are the developer-critical path; everything else is product context they can build against.*
