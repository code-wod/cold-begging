# Backend Deployment

Deploy the FastAPI backend (`backend/`) to **Render** (recommended) or **AWS**. The frontend is a separate Next.js app (deploy first, see "Deploy order" below).

## How the backend works (read this first)

- The backend is a FastAPI app started with `uvicorn backend.main:app`.
- **The campaign scheduler/worker is an in-process thread** (`backend/worker.py`), started automatically by `backend/main.py` on startup. It does **not** run as a separate process and is **not** `cold_email_agent.py` (root, legacy CLI — unused by this backend).
- Consequences:
  - You must run the backend as a **long-lived process**. Serverless (Vercel functions, Lambda API Gateway) won't work.
  - You must run **exactly one process / one replica** (`--workers 1`, `desiredCount=1`). Multiple processes each start their own worker thread → duplicate sends and double polling.
  - The worker only runs while the process is awake. Hosts that sleep when idle (Render free tier) pause scheduled sends until the instance is next awake.

## Deploy order

1. **Frontend first** — build with `NEXT_PUBLIC_API_URL=https://your-api.yourdomain.com` (it hardcodes `http://localhost:8000` otherwise), deploy to Vercel, note the URL.
2. **Backend** — set `FRONTEND_URL=https://your-app.vercel.app` (this is the CORS allowlist in `backend/main.py`).
3. The frontend calls the API via `NEXT_PUBLIC_API_URL` (set at frontend build time).

---

## Option 1: Render (recommended)

### 1. Create the service

- Dashboard → **New → Web Service** → connect your GitHub repo.
- **Name**: `cold-email-api`
- **Runtime**: Python 3.12 (pinned via `runtime.txt` at the repo root — newer defaults like 3.14 can break binary wheels for `psycopg2-binary`).
- **Region**: closest to your recipients' servers (Singapore/India recommended for IST sending windows).

### 2. Build & start commands

| Setting           | Value                                                        |
| ----------------- | ------------------------------------------------------------ |
| Build Command     | `pip install -r backend/requirements.txt`                    |
| Start Command     | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1` |

`psycopg2-binary` (Postgres driver) is already in `backend/requirements.txt`.

Render injects `$PORT` — do not hardcode `8000`. The `--workers 1` is mandatory (see note above).

### 3. Create a Postgres database

- Dashboard → **New → Postgres** → create `cold-email-db` (choose a region with your web service).
- Copy the **Internal Database URL** (e.g. `postgres://...`) into the `DATABASE_URL` env var of the web service. `postgres://` and `postgresql://` are both accepted.
- Tables are created automatically: `init_db()` runs on every startup. No manual migration step on a fresh DB.

### 4. Environment variables

Set these on the web service:

| Variable                  | Required | Notes                                                                                              |
| ------------------------- | -------- | -------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`            | Yes      | Render Postgres internal URL. Never leave the SQLite default in prod.                              |
| `FRONTEND_URL`            | Yes      | Deployed frontend URL — CORS allowlist.                                                            |
| `API_BASE`                | Yes      | Deployed API URL, e.g. `https://cold-email-api.onrender.com` — used for the Gmail OAuth callback.   |
| `SECRET_KEY`              | Yes      | JWT signing secret. Generate once: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.   |
| `FERNET_KEY`              | Yes      | 44-char Fernet key used to encrypt stored Gmail/SMTP passwords. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `ANTHROPIC_API_KEY`       | Optional | Used by user-added models and the managed model.                                                   |
| `GEMINI_API_KEY`          | Optional | Used by the in-app chat.                                                                           |
| `GOOGLE_CLIENT_ID`        | Optional | Server-side Gmail OAuth. SMTP app-password accounts work without these.                            |
| `GOOGLE_CLIENT_SECRET`    | Optional | See above.                                                                                         |
| `ADMIN_EMAILS`            | Optional | Comma-separated emails promoted to admin on startup (managed AI models, `/admin` UI).              |
| `FREE_RATE_PER_HOUR`      | Optional | Free-plan send rate cap, default `10`.                                                            |
| `MAX_RATE_PER_HOUR`       | Optional | Pro-plan cap, default `50`.                                                                        |
| `FREE_RESUME_LIMIT`       | Optional | Resume assets per free user, default `5`.                                                          |
| `PRO_RESUME_LIMIT`        | Optional | Resume assets per Pro user, default `100`.                                                         |
| `ACCESS_TOKEN_EXPIRE_DAYS`| Optional | JWT lifetime in days, default `7`.                                                                 |

**Secrets must be stable.** Changing `SECRET_KEY` invalidates all sessions; changing `FERNET_KEY` makes stored email-account credentials undecryptable. Set them explicitly on Render — do not rely on the local auto-generated files (`.secret_key` / `.fernet_key` are gitignored and only exist locally).

### 5. Health check & keep-alive

- Set the Render **Health Check Path** to `/health`.
- The worker only runs while the process is awake. On the **free tier** the instance sleeps after 15 min of inactivity, so scheduled sends pause. Either:
  - Use a paid (non-sleeping) instance, or
  - Ping it periodically — Render **Cron Jobs** can hit `https://cold-email-api.onrender.com/health` every few minutes.

### 6. Gmail OAuth (optional)

If you want Google OAuth accounts instead of SMTP app passwords:

- Set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` and add **Authorized redirect URI** in the Google Cloud console: `https://cold-email-api.onrender.com/api/email-accounts/callback`.

---

## Option 2: AWS

### A. ECS Fargate (recommended)

1. Create a `Dockerfile` at the repo root:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

2. Push to ECR, create a task definition with **desiredCount = 1** and the env vars from the table above (`DATABASE_URL` → Amazon RDS Postgres).
3. Create a service in front of an ALB. Target group health check path: `/health`.
4. Do **not** scale to more than 1 task (worker duplication — see top of this doc).

### B. EC2 + systemd (simplest)

1. `git clone` the repo on the instance, `cd cold-begging`, create a venv, `pip install -r backend/requirements.txt`.
2. Run a Postgres via RDS or on the instance; set `DATABASE_URL` etc. in a `.env` file in `backend/` (or environment).
3. `/etc/systemd/system/cold-email.service`:

```ini
[Unit]
Description=Cold Email API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/cold-begging
Environment="DATABASE_URL=postgresql://..."
Environment="FRONTEND_URL=https://your-app.vercel.app"
Environment="API_BASE=https://api.yourdomain.com"
Environment="SECRET_KEY=..."
Environment="FERNET_KEY=..."
ExecStart=/home/ubuntu/cold-begging/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always

[Install]
WantedBy=multi-user.target
```

4. `sudo systemctl enable --now cold-email`, front with Caddy/nginx for TLS, point `FRONTEND_URL` / `API_BASE` at the public HTTPS URLs.

---

## Operational notes

- **Schema changes on an existing DB**: new tables are auto-created by `create_all`, but new **columns** on existing tables require a manual `ALTER TABLE ... ADD COLUMN` (SQLite) or `ALTER TABLE ... ADD COLUMN` / migrations (Postgres). Fresh databases are fine.
- **Resume PDFs are stored on local disk** (`backend/uploads/`, `UPLOAD_DIR`). On Render/Fargate the disk is ephemeral — uploads are lost on every redeploy and you can't share them across instances. This is acceptable for a single-instance setup; for persistence, uploads would need object storage (not yet implemented).
- **Timezones**: the worker resolves campaign zones via IANA keys (`Asia/Kolkata`, not `IST`). Stored timestamps are naive UTC; the worker normalizes both SQLite (naive) and Postgres (aware) values.
- **Monitoring**: `GET /health` returns `{"status": "ok"}`; app logs under `GET /` and `/docs` (Swagger) for manual checks.