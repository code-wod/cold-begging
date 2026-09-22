# Automated Job Application Guide

This guide walks you through setting up and using the AI-powered job hunting features in Cold Begging.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COLD BEGGING v2.0                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   n8n        │───▶│  FastAPI     │◀──▶│  Next.js     │          │
│  │  (Orchestr.) │    │  (Backend)   │    │  (Frontend)  │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                    │
│         ▼                   ▼                   ▼                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Cron/       │    │  AI Matching │    │  Dashboard   │          │
│  │  Webhooks    │    │  Email Gen   │    │  Queue       │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Services:**
- **Frontend**: http://localhost:3000 (or 3001 if 3000 busy)
- **Backend API**: http://localhost:8000
- **n8n**: http://localhost:5678
- **API Docs**: http://localhost:8000/docs

---

## Quick Start

### 1. Start All Services

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
uvicorn backend.main:app --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens http://localhost:3000 (or 3001)

# Terminal 3: n8n (optional - for automation)
docker run -d --name n8n -p 5678:5678 \
  -e N8N_WEBHOOK_SECRET=your_secret_here \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=your_password \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

### 2. Configure Environment

**Backend (.env):**
```bash
ANTHROPIC_API_KEY=sk-ant-xxx        # For AI matching (Pro) or add your own
GEMINI_API_KEY=xxx                   # For chatbot + fallback matching
GOOGLE_CLIENT_ID=xxx                 # For Gmail OAuth
GOOGLE_CLIENT_SECRET=xxx
N8N_WEBHOOK_SECRET=your_secure_secret  # Must match n8n env
FRONTEND_URL=http://localhost:3000
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**n8n Environment:**
```bash
N8N_WEBHOOK_SECRET=your_secure_secret  # Same as backend
```

---

## Manual Job Import Flow

### Step 1: Sign Up & Configure Profile

1. Go to http://localhost:3000/signup
2. Create account
3. Go to **Job Preferences** → Add:
   - Preferred roles (e.g., "Backend Engineer", "Go Developer")
   - Locations (e.g., "Remote", "San Francisco", "India")
   - Skills (e.g., "Go", "Python", "PostgreSQL", "Docker")
   - Employment types, experience level, salary minimum
4. Go to **Resumes** → Upload PDF or add links (GitHub, LinkedIn, etc.)
5. Go to **AI Models** → Add your Anthropic/OpenAI/Gemini API key (or use Pro managed model)

### Step 2: Import a Job

**Option A: Via Frontend (Manual)**
1. Go to **Jobs** page
2. Click **"Import Job URL"**
3. Paste job URL (Greenhouse, Lever, Ashby, company career page, LinkedIn, etc.)
4. Click **Import**
5. System extracts job details, deduplicates, runs AI match

**Option B: Via n8n Webhook (Automated)**
```bash
curl -X POST http://localhost:5678/webhook/job-import \
  -H "Content-Type: application/json" \
  -d '{"url": "https://jobs.lever.co/company/backend-engineer"}'
```

### Step 3: Review Match Analysis

1. Click on the imported job to see **Job Detail**
2. Click **"Run Match"** to see AI analysis:
   - Match score (0-100%)
   - Matched skills ✓
   - Missing skills ✗
   - Reasoning summary
   - Risk factors
   - Recommended resume variant

**Thresholds:**
- **≥80%**: Strong apply → Auto-prepare application
- **70-79%**: Apply → Queue for review
- **<70%**: Weak → Mark for review only

### Step 4: Prepare Application

1. Click **"Prepare Application"** (auto-runs for ≥80% matches)
2. System generates:
   - **Cover letter** - Tailored to job + your resume
   - **Screening answers** - Evidence-based, never hallucinated
   - **Recruiter email** - Personalized cold email
   - **Resume recommendation** - Best variant for this job
3. Creates application record in **Applications** queue

---

## Application Queue Workflow

### Dashboard: `/applications`

| Status | Meaning | Actions |
|--------|---------|---------|
| `ready` | Package generated, needs review | **Approve** / **Reject** |
| `approved` | Ready to apply | **Open Application** / **Reject** |
| `application_opened` | You clicked apply link | **Mark Applied** / **Reject** |
| `applied` | Submitted, awaiting response | Update status manually |
| `screening` | Employer screening | Update status |
| `interview` | Interview scheduled | Update status |
| `offer` | Offer received | **Accept** / **Withdraw** |
| `rejected` | Not selected | — |
| `withdrawn` | You withdrew | — |

### Actions:

1. **Approve** → Moves to `approved`, enables "Open Application"
2. **Open Application** → Opens job URL in new tab, marks `application_opened`
3. **Mark Applied** → Confirms submission, marks `applied` with timestamp
4. **Reject/Withdraw** → Removes from active queue

---

## Automated Discovery (n8n)

### Import Workflows

1. Open n8n at http://localhost:5678
2. Go to **Workflows** → **Import**
3. Import from `n8n-workflows/`:
   - `daily-job-discovery.json` - Runs daily 6 AM IST
   - `followup-reminders.json` - Weekly Monday 9 AM
   - `manual-job-import.json` - Webhook endpoint

### Daily Job Discovery

**Schedule**: Daily 6 AM IST (configurable in workflow)

**What it does:**
1. Fetches all users with job preferences
2. For each user, searches Greenhouse, Lever, Ashby, company pages
3. Imports new jobs, deduplicates
4. Runs AI matching
5. Creates applications for ≥70% matches
6. Sends email notification with summary

**Email notification includes:**
- Total jobs found
- Strong matches (≥80%)
- Applications ready to review
- Top 5 matches with scores

### Follow-up Reminders

**Schedule**: Weekly Monday 9 AM IST

**What it does:**
1. Finds applications in `applied`/`screening` > 7 days old
2. Sends follow-up reminder email
3. Includes job title, company, days since applied

---

## Source Adapters

| Source | Search | Details | Apply API | Status |
|--------|--------|---------|-----------|--------|
| Greenhouse | ✅ | ✅ | Partner API | ✅ Implemented |
| Lever | ✅ | ✅ | Partner API | ✅ Implemented |
| Ashby | ✅ | ✅ | Partner API | ✅ Implemented |
| Company Career | ❌ | ✅ | ❌ | ✅ Implemented |
| Manual URL | ❌ | ✅ | ❌ | ✅ Implemented |
| LinkedIn | Limited | ✅ | ❌ | Manual import |
| Naukri | Limited | ✅ | ❌ | Manual import |
| Wellfound | Limited | ✅ | ❌ | Manual import |
| Indeed | Limited | ✅ | ❌ | Manual import |

**Important**: We do NOT bypass anti-bot measures. For platforms without official APIs, the flow is:
```
Discover → Analyze → Prepare → User Approves → Open URL → User Submits
```

---

## Email Integration

### Cold Email to Recruiters

The system reuses the existing cold-email automation:

1. For each high-match job, generates **recruiter email**
2. Uses your connected Gmail/SMTP account
3. Campaign workflow: Recipients → AI Agent → Generate → Review → Send

**To send recruiter emails:**
1. Go to **Email Accounts** → Connect Gmail (OAuth) or add SMTP
2. Go to **Campaigns** → Create campaign with "recruiter" agent
3. Add recipients (recruiter emails from job data or manual)
4. Generate → Review → Launch

---

## Troubleshooting

### CORS Errors
```
Access to fetch at 'http://localhost:8000/api/...' from origin 'http://localhost:3000' 
blocked by CORS policy
```
**Fix**: Ensure `FRONTEND_URL=http://localhost:3000` in backend `.env` and restart backend. Frontend `.env.local` must have `NEXT_PUBLIC_API_URL=http://localhost:8000`.

### 404 on API Calls
```
POST http://localhost:3000/api/jobs/resumes 404
```
**Fix**: Frontend is calling its own API routes instead of backend. Check `NEXT_PUBLIC_API_URL` in frontend `.env.local` and restart frontend dev server.

### "Select is not defined"
**Fix**: Import `Select` from `../components/ui` in the page component.

### n8n Webhook 401
```
Invalid n8n secret
```
**Fix**: Ensure `N8N_WEBHOOK_SECRET` matches in backend `.env` and n8n environment.

### AI Match Fails
```
No AI model configured
```
**Fix**: Go to **AI Models** page and add your API key, or upgrade to Pro for managed model.

---

## API Endpoints Reference

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List with filters |
| POST | `/api/jobs/import` | Import from URL |
| GET | `/api/jobs/{id}` | Job detail |
| POST | `/api/jobs/{id}/match` | Run AI match |
| POST | `/api/jobs/{id}/prepare` | Generate application |

### Resumes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs/resumes` | List resumes |
| POST | `/api/jobs/resumes` | Upload PDF |
| POST | `/api/jobs/resumes/link` | Add link |
| PATCH | `/api/jobs/resumes/{id}` | Update |
| POST | `/api/jobs/resumes/{id}/default` | Set default |
| DELETE | `/api/jobs/resumes/{id}` | Delete |

### Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/applications` | List queue |
| GET | `/api/applications/ready` | Ready to review |
| GET | `/api/applications/stats` | Statistics |
| GET | `/api/applications/{id}` | Detail |
| POST | `/api/applications/{id}/approve` | Approve |
| POST | `/api/applications/{id}/open` | Open URL |
| POST | `/api/applications/{id}/mark-applied` | Mark applied |
| POST | `/api/applications/{id}/reject` | Reject |
| POST | `/api/applications/{id}/withdraw` | Withdraw |

### n8n Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/n8n/users/active` | Users with preferences |
| POST | `/api/n8n/webhook/job-discovery` | Trigger discovery |
| POST | `/api/n8n/webhook/match-and-prepare` | Match specific job |
| POST | `/api/n8n/webhook/notify` | Send notification |
| POST | `/api/n8n/webhook/followup-check` | Check follow-ups |

---

## Security Notes

- All n8n webhooks require `X-N8N-Secret` header
- User data is tenant-isolated (user_id scoping)
- API keys encrypted with Fernet
- Gmail OAuth tokens encrypted
- JWT tokens for authentication
- No CAPTCHA bypassing or anti-bot evasion

---

## Next Steps

1. **Add Telegram/Slack notifications** - Extend `notification_service.py`
2. **Browser extension** - Capture jobs from any page → n8n webhook
3. **Scheduled discovery** - Fine-tune n8n cron for your timezone
4. **Analytics dashboard** - Track match rates, application funnel
5. **Team collaboration** - Share job lists, team applications