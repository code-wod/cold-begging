# Browser-Based Automatic Job Application Agent — Implementation Status

> **Status: NOT STARTED** — This document tracks the implementation progress for the browser-based job application agent feature as specified in the feature requirements.

---

## Executive Summary

| Feature Area | Status | Progress |
|--------------|--------|----------|
| Browser Infrastructure (Playwright, Worker, Redis) | ❌ Not Started | 0% |
| Provider Framework | ❌ Not Started | 0% |
| LinkedIn Provider (Easy Apply) | ❌ Not Started | 0% |
| Naukri Provider (One Click Apply) | ❌ Not Started | 0% |
| Wellfound Provider | ❌ Not Started | 0% |
| Hirist Provider | ❌ Not Started | 0% |
| Instahyre Provider | ❌ Not Started | 0% |
| AI Application Intelligence | ❌ Not Started | 0% |
| Frontend Dashboards | ❌ Not Started | 0% |
| n8n Integration | ❌ Not Started | 0% |
| Testing Infrastructure | ❌ Not Started | 0% |

**Overall: 0% Complete**

---

## What EXISTS in the Repository (Pre-Work)

The following related concepts already exist but are **NOT** the browser agent:

### Job Source Names (Strings Only)
In `backend/models.py` — Job model:
```python
source = Column(String(64))  # Values: linkedin, naukri, wellfound, greenhouse, lever, ashby, company, manual
```
These are just **string labels** for job import sources — no browser automation.

### LinkedIn URL Fields
- `Recipient.linkedin_url` — contact person's LinkedIn profile
- `UserProfileAsset.asset_type = 'linkedin'` — user's own LinkedIn profile link
- Used for cold email personalization, NOT browser login

### Source Providers (API-Based Only)
In `backend/services/source_providers/`:
- `ManualProvider` — HTML scraping of job URLs
- `GreenhouseProvider` — API-based job fetching
- `LeverProvider` — API-based job fetching
- `AshbyProvider` — API-based job fetching
- `GenericCompanyProvider` — HTML scraping

**None use Playwright or browser automation.**

---

## Required Implementation (Per Feature Spec)

### Phase 1: Browser Infrastructure
- [ ] Playwright integration (`pip install playwright && playwright install`)
- [ ] Browser Manager (launch, context, page lifecycle)
- [ ] Persistent Browser Sessions (user_data_dir per user/platform)
- [ ] Session Isolation (separate browser profiles)
- [ ] Browser Worker Process (independent from FastAPI)
- [ ] Redis Queue for task communication
- [ ] Worker Pool (concurrency limits)

### Phase 2: Provider Framework
- [ ] Abstract `JobPortalProvider` base class
- [ ] `PortalCapabilities` model
- [ ] Provider Registry
- [ ] Selector management per provider

### Phase 3: LinkedIn Provider
- [ ] Login detection (check for feed/session)
- [ ] Persistent session via browser context
- [ ] Job search with filters
- [ ] Job card extraction
- [ ] Easy Apply workflow
- [ ] Multi-step form handling
- [ ] Screening question detection
- [ ] Resume upload
- [ ] Submit detection
- [ ] Result verification

### Phase 4: Naukri Provider
- [ ] One Click Apply workflow
- [ ] Job search
- [ ] Result detection

### Phase 5: Wellfound Provider
- [ ] Search workflow
- [ ] Application workflow

### Phase 6: Hirist + Instahyre Providers
- [ ] Search workflows
- [ ] Application workflows

### Phase 7: AI Application Intelligence
- [ ] Field classification system (label/placeholder/accessible name)
- [ ] Candidate Answer Store (structured profile)
- [ ] AI Screening Answers (with "requires_user_input" fallback)
- [ ] Resume variant selection
- [ ] Cover letter generation (reuse existing)
- [ ] Duplicate protection (application history check)

### Phase 8: Frontend Dashboards
- [ ] Browser Session Dashboard (`/job-portals`)
- [ ] Agent Control Dashboard (`/agent`)
- [ ] Live Agent Logs (WebSocket/SSE)
- [ ] Application History with filters

### Phase 9: n8n Integration
- [ ] Scheduled agent runs via n8n
- [ ] API endpoints for agent control

---

## Architecture Integration Points

### Existing Code to Reuse
| Component | Location | Reuse For |
|-----------|----------|-----------|
| AI Matching | `matching_service.py` | Pre-application job scoring |
| Resume Management | `jobs.py` router + `Resume` model | Resume selection/upload |
| Candidate Profile | `JobPreferences` + `Resume` | Answer store |
| Cover Letter Gen | `matching_service.prepare_application` | Portal cover letters |
| Application Model | `Application` model | Track browser submissions |
| n8n Webhooks | `n8n.py` router | Scheduled agent triggers |

### New Components Needed
```
backend/
├── browser/
│   ├── __init__.py
│   ├── manager.py          # Browser launch/context management
│   ├── session.py          # Persistent session handling
│   ├── worker.py           # Playwright worker process
│   ├── queue.py            # Redis task queue
│   └── pool.py             # Worker pool
├── providers/
│   ├── __init__.py
│   ├── base.py             # JobPortalProvider ABC
│   ├── capabilities.py     # PortalCapabilities
│   ├── registry.py         # Provider registry
│   ├── linkedin/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   └── selectors.py
│   ├── naukri/
│   ├── wellfound/
│   ├── hirist/
│   └── instahyre/
├── routers/
│   ├── job_portals.py      # Portal connection/status
│   └── agent.py            # Agent control/status/logs
└── models/ (extend)
    ├── browser_session.py
    ├── application_attempt.py
    └── agent_log.py
```

---

## Configuration Required

### Environment Variables (New)
```env
# Browser Agent
PLAYWRIGHT_HEADLESS=false
BROWSER_DATA_DIR=./browser-data
REDIS_URL=redis://localhost:6379/0
JOB_AGENT_ENABLED=false
DEFAULT_DAILY_APPLICATION_LIMIT=15
DEFAULT_MIN_MATCH_SCORE=80
DRY_RUN=true
MAX_BROWSER_WORKERS=3
MAX_USER_CONCURRENT_SESSIONS=1
```

### .gitignore Additions
```gitignore
browser-data/
*.log
playwright-report/
test-results/
```

---

## Safety Requirements (Non-Negotiable)

Per the feature specification, the implementation MUST:

1. **Never bypass CAPTCHA** — pause and request human intervention
2. **Never bypass anti-bot** — use normal browser, respect rate limits
3. **Never store passwords** — use persistent browser sessions only
4. **Never fabricate answers** — mark unknown questions as `requires_user_input`
5. **Never submit without validation** — verify all required fields
6. **Default to DRY_RUN** — skip final submit until explicitly enabled
7. **Isolate user data** — separate browser profiles, no shared cookies

---

## Testing Strategy

### Unit Tests (Mock)
- [ ] MockProvider for testing logic without browser
- [ ] Field classification accuracy
- [ ] Question type detection
- [ ] Duplicate detection logic
- [ ] State machine transitions

### Integration Tests (Playwright)
- [ ] Login detection per platform
- [ ] Job search + extraction
- [ ] Form filling (known fields)
- [ ] Resume upload
- [ ] DRY_RUN full workflow

### Manual Verification
- [ ] Real LinkedIn Easy Apply (with test account)
- [ ] Real Naukri One Click Apply
- [ ] Session persistence across restarts
- [ ] CAPTCHA/manual intervention pause/resume

---

## Next Steps

1. **Add Playwright to requirements.txt**
2. **Create browser/ module structure**
3. **Implement Browser Manager + Session persistence**
4. **Create Provider ABC + Registry**
5. **Implement LinkedIn Provider (most complex)**
6. **Add Redis + Worker process**
7. **Build Frontend dashboards**
8. **Add n8n workflow for scheduling**

---

## Files to Create (Estimated)

| File | Purpose |
|------|---------|
| `backend/requirements.txt` | Add `playwright`, `redis` |
| `backend/browser/manager.py` | Browser/context lifecycle |
| `backend/browser/session.py` | Persistent session (user_data_dir) |
| `backend/browser/worker.py` | Worker process main loop |
| `backend/browser/queue.py` | Redis task queue |
| `backend/browser/pool.py` | Worker pool management |
| `backend/providers/base.py` | JobPortalProvider ABC |
| `backend/providers/capabilities.py` | PortalCapabilities |
| `backend/providers/registry.py` | Provider registry |
| `backend/providers/linkedin/provider.py` | LinkedIn Easy Apply |
| `backend/providers/linkedin/selectors.py` | LinkedIn selectors |
| `backend/providers/naukri/provider.py` | Naukri One Click |
| `backend/providers/wellfound/provider.py` | Wellfound |
| `backend/providers/hirist/provider.py` | Hirist |
| `backend/providers/instahyre/provider.py` | Instahyre |
| `backend/routers/job_portals.py` | Portal connect/status API |
| `backend/routers/agent.py` | Agent control/status/logs |
| `backend/models/browser_session.py` | Session tracking model |
| `backend/models/application_attempt.py` | Attempt logging |
| `backend/models/agent_log.py` | Structured logging |
| `frontend/pages/job-portals.js` | Session dashboard |
| `frontend/pages/agent.js` | Control dashboard |
| `frontend/pages/agent-logs.js` | Live logs |
| `frontend/pages/applications/history.js` | Application history |
| `n8n-workflows/agent-scheduled-run.json` | n8n scheduled run |

---

## Notes

- **Do NOT modify** existing cold-email functionality (`campaigns`, `recipients`, `email_accounts`, etc.)
- **Extend** existing models (`Job`, `Application`, `Resume`) rather than replacing
- **Follow** existing API conventions (`/api/...`, Pydantic schemas, JWT auth)
- **Use** existing AI infrastructure (`matching_service`, `campaign_service` patterns)
- **Worker must be independently restartable** — no Playwright in FastAPI request handlers