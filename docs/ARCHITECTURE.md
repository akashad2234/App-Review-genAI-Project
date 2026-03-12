# Phase-Wise Architecture: Groww Play Store Review Pulse

**LLM Provider:** Groq (core pipeline) + Gemini (Phase 3 themes)  
**Product Under Review:** Groww (Play Store)  
**Output:** Weekly one-page pulse (top themes, user quotes, action ideas) + draft email

---

## Problem Statement

Turn recent Play Store reviews into a weekly one-page pulse containing top themes, real user quotes, and three action ideas. Draft an email with the weekly note and send it to a configured recipient.

### Who This Serves

| Audience | Value |
|----------|-------|
| Product / Growth Teams | Understand what to fix next |
| Support Teams | Know what users are saying and acknowledging |
| Leadership | Quick weekly health pulse |

---

## Design Principles

- **DRY:** Single Groq client, shared utilities for PII scrubbing and data models.
- **Well-tested:** Unit tests at every phase; integration test for full pipeline.
- **Engineered enough:** No fragile scrapers, no premature abstraction.
- **Explicit over clever:** Clear data flow from reviews to email.
- **No PII:** Strip personally identifiable information before any LLM call or output.

---

## High-Level Data Flow

```
Web UI (Dashboard)
       │
       │  Triggers (Generate Pulse, Send Email)
       ▼
┌─────────────────┐
│  Pipeline API    │  ← HTTP endpoint, validates request, starts run
└────────┬────────┘
         │
         ▼
Play Store (Groww)
       │
       ▼
┌─────────────────┐
│  Review Ingestion │  ← google-play-scraper, last 8-12 weeks
│  + PII Scrubbing  │
└────────┬────────┘
         │  List[Review] (rating, title, text, date)
         ▼
┌─────────────────┐
│ Theme Generation │  ← Groq LLM generates 3-5 themes from review corpus
│ + Review Grouping│  ← Groq LLM assigns each review to a theme
└────────┬────────┘
         │  Dict[Theme → List[Review]]
         ▼
┌─────────────────┐
│  Pulse Note Gen  │  ← Groq LLM: top 3 themes, 3 quotes, 3 action ideas
└────────┬────────┘
         │  Markdown / structured note
         ▼
┌─────────────────┐
│  Email Drafting  │  ← Format note into email body
│  + Delivery      │  ← SMTP to self/alias
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Web UI Updates  │  ← Show latest run status, link to one-pager
└─────────────────┘
```

---

## LLM Integration Strategy

- **Groq (core pipeline):** All heavy content generation (weekly pulse, quotes, action ideas) continues to use the Groq client module.
- **Gemini (Phase 3 themes):** Theme discovery and review grouping in Phase 3 use Gemini (Google Generative AI) for stronger clustering and JSON tooling.
- **Secrets:** `GROQ_API_KEY` and `GEMINI_API_KEY` from environment; never committed.
- **Rate limits:** Design for batching and optional caching of expensive calls (e.g., research synthesis, long-form generation). Theme generation and grouping are batched through Gemini.
- **Structured output:** Use JSON-formatted prompts with Groq and Gemini to ensure parseable results.

---

## Phase 1: Foundation and Groq Client

**Goal:** Repo structure, dependency management, and a reusable Groq LLM layer.

| Deliverable | Description |
|------------|-------------|
| Project layout | `src/` (core modules), `tests/`, `output/`, `docs/`, `config/`, `.env.example` at root. |
| Dependency file | `requirements.txt` with pinned versions: `groq`, `google-play-scraper`, `python-dotenv`, `pytest`, `smtplib` (stdlib). |
| Groq client module | `src/llm/groq_client.py`: thin wrapper with `chat_completion(messages, model, max_tokens, temperature, response_format)`, env-based API key, retries with exponential backoff, error handling. |
| Config | `src/config.py`: model names, default params, app ID (`com.groww.v2`), review window (weeks), email settings. All overridable via env vars. |
| PII scrubber | `src/utils/pii_scrubber.py`: regex-based removal of emails, phone numbers, names patterns, and Aadhaar-like numbers from review text before any LLM call. |
| Tests | Unit tests for Groq client (mock HTTP, validate request shape, error paths). Unit tests for PII scrubber (known patterns). |

**Key Decisions:**
- Python as the language (best ecosystem for Play Store scraping and Groq SDK).
- PII scrubbing lives in Phase 1 because it is a cross-cutting concern used in every downstream phase.

**Outcome:** Any phase can call Groq via one module; PII is stripped before data leaves the system.

---

## Phase 2: Review Ingestion Pipeline

**Goal:** Import Groww Play Store reviews from the last 8-12 weeks, clean them, and persist locally.

| Deliverable | Description |
|------------|-------------|
| Scraper module | `src/ingestion/review_scraper.py`: uses `google-play-scraper` to fetch reviews for `com.groww.v2`. Params: count, language (`en`), sort order (newest first). |
| Date filtering | Filter reviews to the configured window (default: last 8 weeks, max 12). Configurable via `REVIEW_WINDOW_WEEKS` env var. |
| Data model | `src/models/review.py`: dataclass/Pydantic model with fields: `review_id`, `rating` (1-5), `title`, `text`, `date`, `thumbs_up_count`. |
| PII cleaning | Run every review through `pii_scrubber` before storage. |
| Persistence | Save cleaned reviews as JSON under `output/YYYY-MM-DD/reviews.json`. |
| Summary stats | Log basic stats: total reviews fetched, date range covered, rating distribution. |
| Tests | Unit tests with fixture data (mock scraper response). Test date filtering edge cases (no reviews in window, exactly at boundary). Test PII scrubbing integration. |

**Key Decisions:**
- `google-play-scraper` is an unofficial library; it scrapes publicly available data. No API key needed, but it can break if Google changes the page structure. Document this risk.
- Reviews are persisted as JSON so downstream phases can re-run without re-scraping.
- Language filter set to English by default; configurable for future expansion.

**Outcome:** Clean, PII-free review dataset ready for LLM analysis.

---

## Phase 3: Theme Generation and Review Grouping

**Goal:** Use Gemini to generate 3-5 themes from the review corpus, then assign each review to a theme.

| Deliverable | Description |
|------------|-------------|
| Theme generator | `src/phases/phase3/theme_generation.py`: sends all filtered reviews to Gemini and asks for 3-5 themes. Each theme has: `name`, `description`, `sentiment` (positive/negative/mixed). |
| Review grouper | Same module: second Gemini call that, given the themes and all review texts, returns a mapping of each `reviewId` to one `themeName`. |
| Batching strategy | For current scale (≤ 200 reviews) a single call per step is sufficient; for larger volumes, reviews can be split into chunks and merged later. |
| Data model | `themes.json` stores: `source`, `total_reviews`, `sampled_reviews`, and `themes` where each theme has `name`, `description`, `sentiment`, and a `reviews` array containing the reviews assigned to that theme. |
| Persistence | Save themes + grouped reviews under `data/reports/themes/themes.json`. |
| Tests | Unit tests with stubbed Gemini responses (run against `GeminiClient`), verifying: 3-5 themes, all reviews assigned exactly once, and correct JSON shapes. |

**Key Decisions:**
- Two-step LLM process: first generate themes (one Gemini call), then group reviews (second Gemini call). This is more reliable than asking a single prompt to do both, and it keeps themes consistent.
- A representative set of filtered reviews is used for theme generation (currently all filtered reviews).
- Theme count is bounded at 3-5 via the prompt; if the LLM returns more, they can be truncated by review count in a post-processing step if needed.

**Prompt Design (Theme Generation, conceptual):**
```
You are an expert product analyst. Given the following Play Store reviews for the Groww app,
identify up to {n} distinct themes that capture the major topics users discuss.

For each theme provide:
- name: short label (3-5 words)
- description: one sentence explaining this theme
- sentiment: "positive", "negative", or "mixed"

Return ONLY valid JSON:
[
  { "name": "...", "description": "...", "sentiment": "positive|negative|mixed" },
  ...
]

Reviews:
{all_review_texts}
```

**Prompt Design (Review Grouping, conceptual):**
```
We have these themes (JSON):
{themes_json}

Now assign each of the following reviews to exactly one theme by name.
Return ONLY valid JSON:
[
  { "reviewId": "…", "themeName": "User Friendly" },
  ...
]

Reviews (JSON):
{reviews_with_ids_and_text}
```

**Outcome:** A structured theme-to-review mapping stored in `themes.json`, ready for pulse generation.

---

## Phase 4: Weekly Pulse Note Generation

**Goal:** Generate a one-page weekly pulse note: top 3 themes, 3 user quotes, 3 action ideas.

| Deliverable | Description |
|------------|-------------|
| Pulse generator | `src/generation/pulse_generator.py`: takes themes + grouped reviews as input, calls Groq to produce the weekly note. |
| Quote selector | Select 3 impactful, PII-free quotes from reviews (one per top theme where possible). Prefer quotes with concrete feedback over vague complaints. LLM picks the best quotes from candidates. |
| Action idea generator | Part of the pulse prompt: given themes and quotes, suggest 3 concrete, actionable ideas for the product team. |
| Output format | Markdown file: `output/YYYY-MM-DD/weekly-pulse.md`. Structured sections: header (date range, review count), top 3 themes (with review counts and sentiment), 3 quotes (attributed to rating only, no usernames), 3 action ideas. |
| Data model | `src/models/pulse.py`: `WeeklyPulse` with fields for date_range, total_reviews, themes (top 3), quotes (list of 3), action_ideas (list of 3). |
| Tests | Unit tests with mock Groq. Validate output structure: exactly 3 themes, 3 quotes, 3 action ideas. No PII in output. |

**Pulse Note Template:**

```markdown
# Groww App: Weekly Review Pulse
**Period:** {start_date} to {end_date}
**Reviews analyzed:** {total_count}

---

## Top 3 Themes

### 1. {theme_name} ({review_count} reviews, {sentiment})
{theme_description}

### 2. {theme_name} ({review_count} reviews, {sentiment})
{theme_description}

### 3. {theme_name} ({review_count} reviews, {sentiment})
{theme_description}

---

## What Users Are Saying

> "{quote_1}"
> Rating: {star_rating}/5

> "{quote_2}"
> Rating: {star_rating}/5

> "{quote_3}"
> Rating: {star_rating}/5

---

## Action Ideas

1. **{action_title_1}:** {action_description_1}
2. **{action_title_2}:** {action_description_2}
3. **{action_title_3}:** {action_description_3}
```

**Key Decisions:**
- Top 3 themes are selected by review count (most discussed). Ties broken by negative sentiment first (fix-first priority).
- Quotes are attributed only to star rating, never to usernames or dates (PII safeguard).
- Action ideas are generated by the LLM based on the theme + quote context, not invented by the system.

**Outcome:** A polished, one-page weekly pulse note ready for email distribution.

---

## Phase 5: Email Drafting and Delivery

**Goal:** Format the weekly pulse into an email and send it to a configured recipient.

| Deliverable | Description |
|------------|-------------|
| Email formatter | `src/email/email_builder.py`: converts the markdown pulse note into a clean HTML email body (simple inline styles, no heavy templating). |
| Email sender | `src/email/email_sender.py`: uses Python `smtplib` + `email.mime` to send the email. SMTP config from env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`. Recipient: use `get_effective_recipient(recipient_email)` so the frontend can pass recipient per request; fallback is `EMAIL_TO` from env. |
| Draft mode | Default behavior: save the email as `.eml` file under `output/YYYY-MM-DD/weekly-pulse-email.eml` without sending. Actual send requires `--send` flag or `SEND_EMAIL=true` env var. |
| Markdown-to-HTML | Lightweight conversion using `markdown` library (or manual formatting for the simple template). |
| Tests | Unit tests for email builder (verify HTML structure, subject line, no PII). Mock SMTP for sender tests. |

**Key Decisions:**
- **Recipient from frontend:** The recipient email is taken from the frontend when sending from the Web UI. Config provides `RunConfig.recipient_email` and `get_effective_recipient(override)` so the API passes the UI-provided address; `EMAIL_TO` in env is only a fallback (e.g. for CLI).
- Draft-first approach: the default is to save the email locally, not send it. This prevents accidental sends during development and testing.
- SMTP is the delivery mechanism (works with Gmail, Outlook, or any provider). No third-party email API dependency.
- Gmail users: use App Passwords (not account password) with `smtp.gmail.com:587`.
- Subject line format: `Groww Weekly Review Pulse: {start_date} to {end_date}`.

**Outcome:** Email is drafted (and optionally sent) with the weekly pulse note.

---

## Phase 6: CLI, End-to-End Pipeline, and Hardening

**Goal:** Single programmatic entry point, robust error handling, and production-ready pipeline that can be invoked from CLI or Web UI.

| Deliverable | Description |
|------------|-------------|
| CLI entry point | `src/main.py` (or `python -m src.main`): runs the full pipeline: ingest → theme → pulse → email. Flags: `--weeks` (review window), `--send` (send email), `--output-dir` (custom output path). |
| Pipeline orchestrator | `src/pipeline.py`: coordinates all phases in sequence, passes data between them, handles per-phase failures gracefully. Exposes a function `run_pipeline(config: PipelineConfig) → RunResult` so that both CLI and Web UI can call it. |
| Logging | Structured logging with `logging` module: phase name, duration, review count, errors. Log to console and optionally to file. |
| Retry policy | Configurable retries for Groq API calls (default: 3 with exponential backoff). Separate retry for SMTP. |
| Idempotency | If `output/YYYY-MM-DD/` already has intermediate results (reviews, themes), skip those phases unless `--force` flag is set. |
| E2E test | Integration test: fixture reviews → theme generation → pulse → email draft. Assert: output files exist, structure is valid, no PII. |
| README | Setup instructions, env var documentation, usage examples, troubleshooting. Include documentation for both CLI usage and Web UI usage. |
| Weekly scheduler | A host-level scheduler (e.g., Windows Task Scheduler or cron) calls the CLI once a week to generate and send the pulse email automatically. The scheduled command is: `python -m src.main --weeks 8 --send --recipient-email akash7050075323@gmail.com` with the working directory set to the repo root. |

**Outcome:** One programmatic entry point runs the full pipeline. Safe to re-run. CLI and Web UI are just thin shells around this orchestrator. A thin external scheduler can invoke the CLI on a fixed cadence (e.g., every week at 15:35 IST) to keep the pulse and weekly email fully automated.

---

## Phase 7: Web UI and API Layer

**Goal:** Provide a simple web dashboard to trigger pulse generation and email sending, and to view the latest one-pager, without needing CLI access.

### 7.1 Architecture Overview

- **Backend API:** Lightweight HTTP server (e.g., FastAPI or Flask) that exposes endpoints to:
  - Trigger a new pipeline run for a given period.
  - Optionally send the email for the latest run.
  - Fetch run status and metadata (date range, review count, output paths).
  - Serve or proxy the latest weekly pulse one-pager.
- **Frontend:** Minimal single-page UI (could be React, or server-rendered templates) with:
  - A dashboard view showing last run info.
  - A form or buttons to:
    - Generate a new pulse.
    - Generate and send email.
  - A preview pane or link to open the one-page weekly pulse.

### 7.2 Backend API Design

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/api/pulse/run` | POST | Trigger a new pipeline run. Body: optional `weeks`, `send_email`, `recipient_email`, `recipient_name` (from frontend). Recipient name is used to personalize the email body: "Hi {recipient_name}, ...". Calls `run_pipeline(config)` with `RunConfig(recipient_email=..., recipient_name=...)`; recipient falls back to `EMAIL_TO` if not provided. Returns `run_id`. |
| `/api/pulse/status/{run_id}` | GET | Return status of a given run (pending, running, success, failed) plus summary (dates, review count, top themes). |
| `/api/pulse/latest` | GET | Return metadata for the latest successful run plus a link or embedded content for the one-pager. |
| `/api/pulse/latest/email` | POST | Trigger sending the email for the latest successful run (if not already sent, or allow re-send with a flag). |

**Implementation Notes:**

- The API layer should not contain business logic. It:
  - Validates input.
  - Builds a `PipelineConfig` object.
  - Calls `run_pipeline(config)` or enqueues a background job.
  - Returns `RunResult` (or a subset) mapped to JSON.
- For a simple first version, runs can be executed synchronously on the request thread, and a basic in-memory store can track the last run.
- For future scalability, this can be switched to a background task queue (e.g., RQ, Celery), but that is out of scope for the initial implementation.

### 7.3 Frontend UI Design

- **Dashboard page** (default):
  - Header: “Groww Weekly Review Pulse”.
  - Card showing:
    - Last run date.
    - Period covered.
    - Number of reviews analyzed.
    - Status badge (Success / Failed / Not run yet).
  - Buttons:
    - “Generate Weekly Pulse” (calls `/api/pulse/run` with `send_email=false`).
    - “Generate and Send Email” (calls `/api/pulse/run` with `send_email=true`).
  - Link or button: “View latest pulse” that opens the markdown/HTML one-pager in a new tab.
- **Pulse preview page**:
  - Renders the weekly-pulse markdown/HTML directly in the browser (either by serving the rendered HTML or by converting markdown on the server).

**Tech Choices (baseline):**

- **Backend:** FastAPI (Python) so it integrates cleanly with existing pipeline code and models.
- **Frontend:** Simple React app or FastAPI templates:
  - For hackability, server-side templates (e.g., Jinja) may be enough.
  - API-first design keeps the option open to later plug in a more complex SPA.

### 7.4 Data and State Handling

- Maintain a small `runs.json` (or SQLite DB) under `output/` that tracks:
  - `run_id`, `started_at`, `finished_at`, `status`, `period`, `total_reviews`, `output_dir`, `email_sent`.
- The Web UI reads this to show the latest run and status.
- Each pipeline run writes a `run_result.json` file into the output directory, which the API uses to respond to `/status` and `/latest`.

### 7.5 Security and Access

- For internal use (teams at Groww or internal demo), a simple approach is:
  - Restrict access by network (e.g., only accessible on VPN or localhost).
  - Optional basic authentication (username/password from env vars `DASHBOARD_USER`, `DASHBOARD_PASSWORD`).
- All actions are idempotent:
  - Re-triggering a run for the same date will either overwrite the previous run directory or create a new run with a different `run_id`.
  - Email send endpoint checks if `email_sent` is already true and can require a `force` flag to re-send.

**Outcome:** Non-technical stakeholders can generate and view the weekly pulse, and trigger the draft email, directly from a simple web dashboard instead of relying on CLI commands.

---

## Dependency Overview

```
Phase 1 (Groq client + PII scrubber + config)
    ↑
Phase 2 (Review ingestion)             ← uses Phase 1
    ↑
Phase 3 (Theme generation + grouping: Gemini)  ← uses Phase 1, 2
    ↑
Phase 4 (Pulse note generation)        ← uses Phase 1, 3
    ↑
Phase 5 (Email drafting + delivery)    ← uses Phase 4
    ↑
Phase 6 (CLI + pipeline + hardening)   ← uses Phase 1-5
    ↑
Phase 7 (Web UI + API)                 ← uses Phase 6
```

---

## Project Structure

```
App-Review-genAI-Project/
├── docs/
│   └── ARCHITECTURE.md
├── src/
│   ├── __init__.py
│   ├── main.py                  # CLI entry point
│   ├── pipeline.py              # Orchestrates all phases
│   ├── config.py                # All configuration and env vars
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── groq_client.py       # Groq API wrapper (pulse generation, etc.)
│   │   └── gemini_client.py     # Gemini API wrapper (theme generation)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── review_scraper.py    # Play Store review fetcher
│   ├── phases/
│   │   ├── __init__.py
│   │   ├── phase1/              # Phase 1: foundation helpers
│   │   ├── phase2/              # Phase 2: ingestion
│   │   └── phase3/              # Phase 3: Gemini-based theme generation + grouping
│   ├── generation/
│   │   ├── __init__.py
│   │   └── pulse_generator.py   # Weekly pulse note builder
│   ├── email/
│   │   ├── __init__.py
│   │   ├── email_builder.py     # Markdown → HTML email formatter
│   │   └── email_sender.py      # SMTP sender
│   ├── models/
│   │   ├── __init__.py
│   │   ├── review.py            # Review dataclass
│   │   ├── theme.py             # Theme + GroupedReview dataclasses
│   │   └── pulse.py             # WeeklyPulse dataclass
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py            # FastAPI / Flask app exposing pipeline endpoints
│   ├── web/
│   │   ├── __init__.py
│   │   ├── templates/           # Optional server-rendered templates for dashboard
│   │   └── static/              # JS/CSS assets if using a small frontend
│   └── utils/
│       ├── __init__.py
│       └── pii_scrubber.py      # PII detection and removal
├── tests/
│   ├── __init__.py
│   ├── test_groq_client.py
│   ├── test_review_scraper.py
│   ├── test_pii_scrubber.py
│   ├── test_theme_generator.py
│   ├── test_review_grouper.py
│   ├── test_pulse_generator.py
│   ├── test_email_builder.py
│   ├── test_email_sender.py
│   └── test_pipeline_e2e.py
├── output/                      # Generated outputs (gitignored)
│   └── YYYY-MM-DD/
│       ├── reviews.json
│       ├── themes.json
│       ├── grouped_reviews.json
│       ├── weekly-pulse.md
│       ├── weekly-pulse-email.eml
│       └── run_result.json      # Metadata about a given run (used by Web UI)
├── .env.example                 # Template for env vars
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Groq API key |
| `GEMINI_API_KEY` | Yes (for Phase 3) | - | Gemini API key used for theme generation and grouping |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Model for LLM calls |
| `REVIEW_WINDOW_WEEKS` | No | `8` | How many weeks of reviews to fetch (8-12) |
| `APP_ID` | No | `com.groww.v2` | Play Store app ID |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server host |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | Yes (for send) | - | SMTP username/email |
| `SMTP_PASSWORD` | Yes (for send) | - | SMTP password or app password |
| `EMAIL_FROM` | Yes (for send) | - | Sender email address |
| `EMAIL_TO` | No (when frontend provides recipient) | - | Fallback recipient; when using the Web UI, recipient is sent from the frontend per request. |
| `SEND_EMAIL` | No | `false` | Set to `true` to actually send email |

---

## Security and PII Handling

- **No PII in outputs:** Reviews are scrubbed before storage, LLM calls, and email content.
- **Scrubbing targets:** Email addresses, phone numbers (Indian and international formats), Aadhaar-like 12-digit numbers, usernames that look like real names (best-effort via regex + optional LLM check).
- **Quotes:** Attributed only to star rating, never to reviewer name, date, or profile.
- **Secrets:** All credentials via env vars; `.env` is gitignored; `.env.example` has placeholder values.
- **SMTP:** TLS enforced; App Passwords recommended over account passwords for Gmail.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `google-play-scraper` breaks (Google changes page structure) | Ingestion fails | Pin library version; fallback: manual CSV import; monitor for library updates. |
| Groq rate limits hit | Theme/pulse generation fails | Exponential backoff; batch reviews to minimize calls; cache intermediate results. |
| Too few reviews in window | Weak themes | Expand window dynamically (8 → 12 weeks); log warning if < 50 reviews. |
| PII leaks through scrubber | Compliance risk | Multi-layer approach: regex + LLM review of final output; manual spot-check in draft mode. |
| SMTP auth failures | Email not sent | Draft mode as default; clear error messages; test with `--dry-run`. |

---

## Suggested Order of Work

1. **Phase 1:** Set up project, implement Groq client and PII scrubber, land tests.
2. **Phase 2:** Build review scraper, validate with real Groww reviews, confirm PII scrubbing works.
3. **Phase 3:** Implement theme generation and review grouping, tune prompts with real data.
4. **Phase 4:** Build pulse note generator, iterate on output quality.
5. **Phase 5:** Add email formatting and SMTP delivery, test in draft mode first.
6. **Phase 6:** Wire up CLI, add logging and retry logic, write E2E test, finalize README.

Each phase should be a working increment: Phase 2 produces a clean review dataset you can inspect; Phase 3 adds themes you can validate; Phase 4 produces a readable pulse note before email is even wired up.
