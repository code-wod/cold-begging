# AGENTS.md

Cold-email automation SaaS: Excel/CSV recipients → AI-personalized outreach → review → send via the user's Gmail. **The primary product is a multi-tenant FastAPI backend + Next.js frontend.** The root Flask app and Node CLI are legacy.

## Layout & entrypoints

- `backend/` — **primary API** (FastAPI, port **8000**). Multi-tenant SQLAlchemy app:
  - `main.py` — app factory, CORS, router wiring, starts the scheduler worker on startup.
  - `database.py`, `models.py` — SQLite by default (`backend/cold_email.db`); Postgres via `DATABASE_URL`. `init_db()` runs on startup (auto-creates tables).
  - `cold_email_agent.py` — near-copy of root agent, **minus CLI**, plus `ai_provider` param. Reused by `campaign_service.py` for research/personalization/sending.
  - `ai.py` — provider abstraction (`AnthropicProvider`, `OpenAIProvider`); the managed model is a **Pro-only** feature.
  - `gmail.py` — server-side Google OAuth (authorization-code flow, no browser), stores **encrypted** refresh tokens.
  - `worker.py` — in-process `CampaignWorker` thread polling scheduled campaigns (no Redis; swap for Celery later).
  - `routers/` — `auth`, `recipients`, `email_accounts`, `agents` (AI models+agents), `campaigns`, `emails`, `analytics`, `billing`.
  - `encryption.py` (Fernet), `security.py` (JWT + bcrypt), `schemas.py` (Pydantic), `config.py` (env + auto-persisted secrets).
- `frontend/` — **primary UI** (Next.js pages router, port **3000**). `pages/` has landing, auth, and the AWS-console-style app (`dashboard`, `campaigns/`, `recipients`, `ai-agents`, `ai-models`, `email-accounts`, `history`, `analytics`, `settings`, `profile`, `billing`, `onboarding`). Design system in `components/ui.js` + `styles/global.css`; API client `lib/api.js`, auth context `lib/auth.js`. **Theming**: light/dark via CSS variables in `global.css` (`:root` = light, `[data-theme='dark']` = dark overrides); toggle is `components/ThemeToggle.js` (mounted in `Layout` topbar, landing nav, auth pages), persisted in `localStorage['pb-theme']`, set pre-paint by an inline script in `pages/_document.js`. Body font is the opencode-style mono stack (`--font-mono`, IBM Plex Mono via Google Fonts). Landing page (`pages/index.js`) is AWS-style (navy nav/footer + `#ff9900` accents).
- `app.py` + `templates/` — legacy Flask UI (port 5000). Superseded; leave alone.
- `node/` — legacy Node CLI. Leave alone.

## Run commands

```sh
# Backend API (:8000) — REQUIRED by the frontend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn backend.main:app --port 8000   # run from repo root

# Frontend (:3000) — expects the API at NEXT_PUBLIC_API_URL (default http://localhost:8000)
cd frontend && npm install && npm run dev

# Legacy Flask UI (:5000) — optional, root cold_email_agent.py CLI
pip install -r requirements.txt && python app.py
```

No tests, no linter/typecheck config, no CI. Verify by running the servers and exercising the flow (signup → import recipients → add AI model+agent → connect email account → create campaign → generate → preview → send).

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
- **Route-order trap**: in `routers/emails.py`, `/emails/history` must stay defined before `/emails/{email_id}` (FastAPI matches in order).
- **`frontend/.next/` build artifacts are committed** and not in `.gitignore`. Don't add stale `.next` output to commits.
- **Python 3.9** is in use; `zoneinfo` (scheduler), `list[...]` annotations and pydantic v2 (needs `email-validator`) all work, but keep type hints compatible.