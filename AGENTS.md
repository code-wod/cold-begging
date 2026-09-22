# AGENTS.md

Cold-email automation SaaS + **automated job portal agent**: Excel/CSV recipients → AI-personalized outreach → review → send via the user's Gmail. Users can also connect job portals (LinkedIn, Naukri, Indeed, Wellfound, Hirist, Instahyre) and have the AI agent automatically search and apply to matching jobs. **The primary product is a multi-tenant FastAPI backend + Next.js frontend.** The root Flask app and Node CLI are legacy.

## Layout & entrypoints

- `backend/` — **primary API** (FastAPI, port **8000**). Multi-tenant SQLAlchemy app:
  - `main.py` — app factory, CORS, router wiring, starts the scheduler worker on startup.
  - `database.py`, `models.py` — SQLite by default (`backend/cold_email.db`); Postgres via `DATABASE_URL`. `init_db()` runs on startup (auto-creates tables).
  - `cold_email_agent.py` — near-copy of root agent, **minus CLI**, plus `ai_provider` param. Reused by `campaign_service.py` for research/personalization/sending.
  - `ai.py` — provider abstraction (`AnthropicProvider`, `OpenAIProvider`); the managed model is a **Pro-only** feature.
  - `gmail.py` — server-side Google OAuth (authorization-code flow, no browser), stores **encrypted** refresh tokens.
  - `worker.py` — in-process `CampaignWorker` thread polling scheduled campaigns (no Redis; swap for Celery later).
  - `routers/` — `auth`, `recipients`, `email_accounts`, `agents` (AI models+agents), `campaigns`, `emails`, `analytics`, `billing`, `jobs`, `applications`, `agent`, `job_portals`, `n8n`, `profile_assets`.
  - `services/` — `job_service.py` (job CRUD, preferences, resumes), `matching_service.py` (AI matching + cover letter/screening generation), `application_service.py` (application lifecycle), `notification_service.py`, `source_providers/` (Greenhouse, Lever, Ashby, generic ATS scrapers).
  - `providers/` — browser-based job portal providers: `linkedin.py`, `naukri.py`, `wellfound.py`, `hirist.py`, `instahyre.py`, `indeed.py`. Each implements `search_jobs`, `extract_job_detail`, `can_apply`, `prepare_application`, `submit_application`, `detect_application_result`.
  - `browser/` — Playwright browser automation: `manager.py` (persistent contexts, stealth), `session.py` (login verification, platform configs), `queue.py` (in-memory or Redis task queue), `worker.py` (task handlers for search/apply/login), `pool.py` (worker pool management).
  - `encryption.py` (Fernet), `security.py` (JWT + bcrypt), `schemas.py` (Pydantic), `config.py` (env + auto-persisted secrets).
- `frontend/` — **primary UI** (Next.js pages router, port **3000**). `pages/` has landing, auth, and the AWS-console-style app (`dashboard`, `campaigns/`, `recipients`, `ai-agents`, `ai-models`, `email-accounts`, `history`, `analytics`, `settings`, `profile`, `billing`, `onboarding`, `jobs/`, `applications/`, `job-portals`, `agent`, `resumes`, `job-preferences`). Design system in `components/ui.js` + `styles/global.css`; API client `lib/api.js`, auth context `lib/auth.js`. **Theming**: light/dark via CSS variables in `global.css` (`:root` = light, `[data-theme='dark']` = dark overrides); toggle is `components/ThemeToggle.js` (mounted in `Layout` topbar, landing nav, auth pages), persisted in `localStorage['pb-theme']`, set pre-paint by an inline script in `pages/_document.js`. Body font is the opencode-style mono stack (`--font-mono`, IBM Plex Mono via Google Fonts). Landing page (`pages/index.js`) is AWS-style (navy nav/footer + `#ff9900` accents). **Navigation** (`Layout.js`): sidebar sections — Overview (Dashboard), Job Hunting (Jobs, Applications, Job Portals, Agent Control, Resumes, Job Preferences), Automation (Campaigns, Recipients, AI Agents, Email Accounts, History, Analytics), Account (Settings, Billing, Profile).
- `app.py` + `templates/` — legacy Flask UI (port 5000). Superseded; leave alone.
- `node/` — legacy Node CLI. Leave alone.

## Full Setup (clean machine)

Run these in order from the repo root (`cold-begging/`):

```sh
# ── 1. Kill anything on port 8000/3000 (if "Address already in use") ──
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# ── 2. Backend venv + dependencies ──
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# ── 3. Install Playwright browsers (needed for job portal automation) ──
playwright install chromium
# Verify: should print "chromium-<version>" in ms-playwright cache
playwright install-deps 2>/dev/null   # macOS: usually no-op; Linux: installs system libs

# ── 4. Start Redis (optional — queue falls back to in-memory if unavailable) ──
# macOS:
brew services start redis 2>/dev/null || redis-server --daemonize yes
# Verify:
redis-cli ping   # → PONG

# ── 5. Configure backend environment ──
# backend/.env must exist (gitignored). Minimum required:
#   GEMINI_API_KEY=...          (for AI matching + chatbot)
#   GOOGLE_CLIENT_ID=...       (for Gmail OAuth — optional for SMTP-only)
#   GOOGLE_CLIENT_SECRET=...
#   SMTP_SENDER_EMAIL=...      (for email verification)
#   SMTP_SENDER_APP_PASSWORD=...
#   ADMIN_EMAILS=...           (comma-separated, promoted at startup)
#
# Optional env vars (shown with defaults):
#   DRY_RUN=true               (set to "false" to allow real job applications)
#   PLAYWRIGHT_HEADLESS=false   (set to "true" for headless browser)
#   REDIS_URL=redis://localhost:6379/0
#   DATABASE_URL=               (empty = SQLite at backend/cold_email.db)
#   FREE_RATE_PER_HOUR=10
#   MAX_RATE_PER_HOUR=50
#   DEFAULT_DAILY_APPLICATION_LIMIT=15

# ── 6. Start backend (:8000) ──
cd ..   # back to repo root
.venv/bin/uvicorn backend.main:app --port 8000 --reload
# Backend auto-creates DB tables on startup (init_db in lifespan)

# ── 7. Frontend (:3000) — in a separate terminal ──
cd frontend
npm install
npm run dev

# ── 8. n8n (optional — for webhook automations) ──
# Only needed if you want n8n webhook integrations (job discovery, notifications).
# Install:
npm install -g n8n
n8n start
# Then set N8N_WEBHOOK_SECRET in backend/.env and import workflows from n8n-workflows/
```

> **IMPORTANT**: Always run `uvicorn` from the **repo root** (`cold-begging/`), not from inside `backend/`.
> The `backend.main:app` import path requires the repo root to be the CWD.
> The venv lives in `backend/.venv/` but uvicorn must be invoked from `..` (repo root).

### Quick verify flow

```
signup → set job preferences → upload resume → connect job portals → search jobs → review applications → apply
signup → import recipients → add AI model+agent → connect email account → create campaign → generate → preview → send
```

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `Address already in use :8000` | `lsof -ti:8000 \| xargs kill -9` |
| `Address already in use :3000` | `lsof -ti:3000 \| xargs kill -9` |
| `playwright` not found | Run `playwright install chromium` inside the activated venv |
| Browser jobs fail with timeout | Ensure `PLAYWRIGHT_HEADLESS=false` in `backend/.env` (job portals need visible browser for login) |
| Redis connection error | `brew services start redis` or `redis-server --daemonize yes` — or just ignore (in-memory fallback works) |
| `No AI model configured` | Add a model at `/ai-models` (bring your own API key) or use the free platform model (auto-provisioned) |
| Gmail connect 401/500 | Set `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` in `backend/.env` |
| `job_portal_sessions` table missing | Tables auto-created on startup via `init_db()` — just restart the backend |

No tests, no linter/typecheck config, no CI.

## Job Portal Agent — How It Works

### Architecture
- **6 platforms supported**: LinkedIn, Naukri, Wellfound, Hirist, Instahyre, Indeed
- **Browser automation**: Playwright with persistent contexts per user/platform (stores cookies/login state in `backend/browser-data/{user_id}/{platform}/`)
- **Task queue**: In-memory by default (no Redis required). Optionally uses Redis if `REDIS_URL` is set.
- **AI matching**: Uses the user's configured AI model (or free platform model) to score jobs against their profile/resume. Falls back to keyword matching if no AI model is available.

### Flow
1. **Connect portal** → `POST /api/job-portals/{platform}/connect` → Opens browser for manual login (or auto-fills if credentials provided). Session saved to disk.
2. **Set preferences** → `PUT /api/jobs/preferences` → Roles, locations, skills, salary, remote preference, experience levels.
3. **Upload resume** → `POST /api/jobs/resumes` → PDF uploaded, text extracted, skills detected.
4. **Search jobs** → `POST /api/agent/search` → Iterates connected platforms, scrapes job listings via Playwright, creates `Job` records, runs AI matching.
5. **Review matches** → `GET /api/applications?status=ready` → Jobs scored and ranked. AI generates cover letters, screening answers, recruiter emails.
6. **Apply** → `POST /api/applications/{id}/approve` then browser agent fills forms and submits via Easy Apply/One Click Apply.

### Key Models
- `JobPreferences` — user search config (roles, locations, skills, salary, remote, visa)
- `Resume` — uploaded resumes with extracted text/skills, `is_default` flag
- `Job` — normalized job listing from any source, deduped by `job_hash`
- `Application` — user-to-job link with `match_score`, `cover_letter`, `screening_answers`, `status` lifecycle
- `JobPortalSession` — tracks connection status per user/platform (but actual session state is on disk in browser-data)

### Key Endpoints
- `GET /api/job-portals` — list all platforms with connection status + capabilities
- `POST /api/job-portals/{platform}/connect` — connect (opens browser for login)
- `POST /api/job-portals/{platform}/verify` — verify session is still valid
- `POST /api/job-portals/{platform}/disconnect` — clear session
- `GET /api/agent/status` — agent stats (daily limit, queue, dry-run mode)
- `POST /api/agent/search` — search jobs across connected platforms (executes directly, no Redis needed)
- `GET /api/jobs` — list jobs with filters (source, location, remote, salary, search)
- `POST /api/jobs/import` — import job from URL
- `POST /api/jobs/{id}/match` — re-run AI matching
- `POST /api/jobs/{id}/prepare` — generate application package
- `GET /api/applications` — list user's applications
- `POST /api/applications/{id}/approve` — approve for submission
- `POST /api/applications/{id}/mark-applied` — mark as applied
- `GET /api/jobs/resumes` — list resumes
- `POST /api/jobs/resumes` — upload resume PDF
- `PUT /api/jobs/preferences` — update job preferences

### Provider Capabilities
| Platform | Job Search | Easy Apply | One-Click | Resume Upload | Cover Letter | Screening Q&A |
|----------|-----------|------------|-----------|---------------|--------------|---------------|
| LinkedIn | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| Naukri | ✅ | ✅ | ✅ | ✅ | — | — |
| Indeed | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| Wellfound | ✅ | ✅ | — | ✅ | ✅ | — |
| Hirist | ✅ | ✅ | — | — | — | — |
| Instahyre | ✅ | ✅ | — | ✅ | — | — |

## Gotchas

- **Two copies of `cold_email_agent.py`** (root and `backend/`). They drift — edit both when changing the agent logic. Root copy is authoritative; backend copy removes the CLI block. Both now take `ai_provider` and delegate generation through it.
- **OAuth needs server-side Google credentials.** Without `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, the Gmail connect button 401s/500s. SMTP (app-password) accounts work without them.
- **Email accounts are per-user and the sender for all campaign/manual mail.** `email_accounts` rows carry `user_id` (every query scopes by it — tenant isolation is enforced in list/test/edit/delete and in `campaign_service`). Campaigns store `email_account_id`; generation/send resolve the account from the campaign and send **from that account's address**, never from a global `SMTP_USER`/`SMTP_PASS`. Providers: `google` (OAuth, refresh token Fernet-encrypted per account) or `smtp` (configurable `smtp_host`/`smtp_port`/`smtp_secure`/`smtp_username` + encrypted password; default `smtp.gmail.com:465`). Each user has one `is_default` account (first added becomes default; `POST /{id}/default` clears others) — the campaign wizard, manual compose, and `POST /api/campaigns` (create) preselect it. Endpoints: `POST ''` (add SMTP), `GET /connect` + `GET /callback` (OAuth), `PATCH /{id}` (edit), `POST /{id}/default`, `POST /{id}/test`, `POST /{id}/disconnect` (soft: clears creds), `DELETE /{id}` (hard delete). Profile page has a full Email Accounts panel plus a dedicated `/email-accounts` page. `EmailLog` snapshots store `email_account_id` + `sender_email`; history filters by sender.
- **Managed default AI model = Pro plan.** `resolve_provider` in `campaign_service.py` raises `PermissionError` for free users; agents fail fast. Free users must add their own model with an API key.
- **Admin + platform AI models.** `User.is_admin` (promoted at startup from comma-separated `ADMIN_EMAILS` env; currently `gaurav@gmail.com` in `backend/.env`). `get_current_admin` in `security.py` 403s non-admins. `backend/routers/admin.py` (`/api/admin`, admin-only): platform AI model CRUD + test (`price_usd` 0 = free for all users, >0 = Pro-only; keys encrypted), and user management (set plan, toggle admin role; can't demote self; delete of an in-use platform model returns 409). Platform models (`AIModel.is_platform=True`) are admin-owned but shared via `campaign_service.model_visible_to` / `list_visible_models` (own + free platforms for everyone, paid platforms for Pro) — they appear in `/api/ai-models`, agent model dropdowns, and the campaign wizard, and `resolve_provider` uses the admin-stored key (free ones also act as the fallback default when a user has no model). Users can test but not edit/delete platform models. Admin UI: `/admin` page (nav link only for admins).
- **Auto-stop cap**: Campaigns store `max_sends` (0 = unlimited, per-campaign total). The worker checks the sent count before and after each send and flips the campaign to `completed` when the cap is reached (pending emails stay `scheduled` but are never sent). Field is on the create/update schemas and wizard. SQLite schema additions need a manual `ALTER TABLE ... ADD COLUMN` on existing DBs (create_all won't add columns to existing tables).
- **Sending rate is hourly, not a fixed delay.** Campaigns store `emails_per_hour` (4–50, plan-gated: free ≤10, Pro ≤50, server-configurable via `FREE_RATE_PER_HOUR`/`MAX_RATE_PER_HOUR`). `campaign_service.validate_rate()` returns a 403 for out-of-plan rates on create/update (and the worker clamps as defense in depth). `rate_interval_seconds()` derives the send interval as `3600 / rate`. `delay_seconds` is legacy/unused.
- **Email history is a full snapshot.** `EmailLog` stores final `subject`/`body`, `generated_subject`/`generated_body`, `sender_email`, `recipient_email`, `ai_agent_id`/`ai_provider`/`ai_model`, `execution_type` (scheduled|manual), and lifecycle timestamps. Statuses: `generated | scheduled | sending | sent | failed | cancelled`. The worker marks `scheduled → sending → sent/failed`; only a confirmed Gmail/SMTP send becomes `sent`; failures get `error_code` (`AUTH_ERROR`/`SEND_ERROR`). Every generated email also creates an `EmailLog` row, so history shows the whole pipeline.
- **Manual emails** go through `POST /api/emails/manual` (recipient + account + subject/body) and land in history with `execution_type: manual`. Failed/cancelled history rows can be retried via `POST /api/emails/history/{log_id}/retry` (bounded manual retry, no auto-loop).
- **Campaign actions**: `launch` marks queued emails `scheduled` (`campaign_service.schedule_campaign`); `cancel` marks pending emails `cancelled` and stops the campaign. Cancel/retry keep already-sent emails intact.
- **Test-connection endpoints**: `POST /api/email-accounts/{id}/test` (OAuth token refresh / SMTP login) and `POST /api/ai-models/{id}/test` (minimal provider call via `AIProvider.test_connection`). Both mark accounts `connected`/`error`.
- **Generation is async.** `POST /api/campaigns/{id}/generate` starts a background thread; poll `GET /api/campaigns/{id}` for status (`generating` → `review_required`/`scheduled`). Generation with no valid AI provider fails the campaign to `failed`.
- **Auto-send scheduling** happens in the in-process `worker.py` thread — it only runs while uvicorn is up, respects `send_start_time`/`send_end_time`/`active_days`/`emails_per_hour` (rolling-hour cap + derived interval)/`daily_limit` (0 = unlimited), and will not send when `dry_run=True`.
- **Secrets via env vars**: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NEXT_PUBLIC_API_URL`. `SECRET_KEY` and `FERNET_KEY` auto-generate into `backend/.secret_key` / `backend/.fernet_key` (gitignored) if unset — don't delete them or stored tokens become undecryptable.
- **In-app chatbot**: floating `frontend/components/ChatWidget.js` (mounted in `Layout`) calls `POST /api/chat` (auth required, `backend/routers/chat.py`). It answers app-help questions via `GeminiProvider` using `GEMINI_API_KEY` (env; currently written to the gitignored `backend/.env`) and model `gemini-3.5-flash-lite`. Returns 503 if the key is missing. Keep the SYSTEM_PROMPT in sync if app flows change.
- **Excel/CSV schema**: only the `Email` column is required; `Company Name`, `Industry`, `Company Website`, `Job Role`, `Position Level` and other columns are optional (missing → blank). Column names are case-insensitive. Import preview/import endpoints validate and detect duplicates before commit; invalid emails are skipped, and missing-`Email` files return a 400 with a clear message.
- **Profile assets personalize campaigns.** `UserProfileAsset` rows (asset_type `resume` | `resume_link` | `github` | `linkedin` | `website`) are per-user and stored via `backend/routers/profile_assets.py` (`/api/profile-assets`): `POST /resume` (multipart PDF → saved under `backend/uploads/{user_id}/` (gitignored, `UPLOAD_DIR`), text extracted with `pypdf` into `text_content`), `POST /link` (JSON), `GET ''`, `DELETE /{id}`. Resumes (PDF or link) count toward a plan-gated cap (`FREE_RESUME_LIMIT`=5, `PRO_RESUME_LIMIT`=100 via `config.py`); exceeding → 403. Campaigns attach assets via the `campaign_assets` join table (`Campaign.assets` relationship, `asset_ids` on `CampaignIn`/`CampaignUpdate`/`CampaignOut`) — **create/update require ≥1 resume-type asset** (`_resolve_assets` in `routers/campaigns.py` 400s otherwise). `campaign_service._sender_context()` builds a "Sender Background" block (resume text snippet + links) passed to `ColdEmailAgent.sender_context`, injected into the generation prompt (edit **both** `cold_email_agent.py` copies). UI: profile page "Resume & Profile Assets" panel + wizard step 3 (upload/attach/select, ≥1 resume to continue). New SQLite tables (`user_profile_assets`, `campaign_assets`) are auto-created by `create_all`.
- **Job portal sessions are stored on disk**, not in the database. `backend/browser-data/{user_id}/{platform}/` contains Playwright persistent context data (cookies, localStorage). The `JobPortalSession` DB model exists but the `SessionManager` uses JSON files + in-memory cache. Don't delete `backend/browser-data/` or users lose their logins.
- **Task queue has no Redis dependency.** `browser/queue.py` provides `InMemoryTaskQueue` as fallback when Redis is unavailable. All job portal operations (connect, search, apply) execute directly in-process. Redis is optional for scaling to multiple workers.
- **Browser automation requires Playwright browsers installed.** Run `playwright install chromium` in the backend venv. The system uses stealth scripts to avoid detection (hides `navigator.webdriver`, spoofs user-agent).
- **DRY_RUN mode** (`config.py`, default `true`) prevents actual job applications from being submitted. The agent will fill forms but not click final submit. Set `DRY_RUN=false` in `backend/.env` to enable real applications.
- **Job search executes synchronously** in the `POST /api/agent/search` endpoint (not via background queue). Large searches may take 30-60 seconds per platform. The browser opens, scrolls, extracts cards, and returns results in the HTTP response.
- **Application lifecycle**: `discovered` → `matched` → `ready` (with cover letter/screening) → `approved` → `applied`. Users review and approve before the agent submits. AI matching must score ≥70 to auto-prepare an application package.
- **Route-order trap**: in `routers/emails.py`, `/emails/history` must stay defined before `/emails/{email_id}` (FastAPI matches in order).
- **`frontend/.next/` build artifacts are committed** and not in `.gitignore`. Don't add stale `.next` output to commits.
- **Python 3.9** is in use; `zoneinfo` (scheduler), `list[...]` annotations and pydantic v2 (needs `email-validator`) all work, but keep type hints compatible.
