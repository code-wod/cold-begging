# n8n Workflows for Cold Begging

This directory contains n8n workflow definitions for automating job discovery, matching, and notifications.

## Workflows

### 1. Daily Job Discovery (`daily-job-discovery.json`)
**Schedule**: Daily at 6 AM IST (configurable via cron)
**Purpose**: Automatically discover new jobs for all users with configured preferences

**Flow**:
1. Cron trigger fires
2. Fetch all users with job preferences
3. For each user, trigger job discovery via `/api/n8n/webhook/job-discovery`
4. Aggregate results
5. Send email notification with summary

**Environment Variables Required**:
- `N8N_WEBHOOK_SECRET` - Shared secret for API authentication
- Backend `FRONTEND_URL` - For notification links

### 2. Follow-up Reminders (`followup-reminders.json`)
**Schedule**: Weekly on Monday 9 AM IST
**Purpose**: Remind users to follow up on pending applications

**Flow**:
1. Cron trigger fires
2. Call `/api/n8n/webhook/followup-check`
3. Finds applications in `applied`/`screening` status > 7 days old
4. Sends follow-up notification emails

### 3. Manual Job Import (`manual-job-import.json`)
**Trigger**: HTTP Webhook at `/webhook/job-import`
**Purpose**: Allow external systems (browser extension, email parser) to import jobs

**Flow**:
1. Receive POST with `{ "url": "https://..." }`
2. Validate URL
3. Call backend `/api/jobs/import` with user's auth token
4. Return job details and match score

## Setup Instructions

### 1. Configure n8n
```bash
# Start n8n (Docker)
docker run -d --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=your_password \
  -e N8N_WEBHOOK_SECRET=your_shared_secret \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

### 2. Import Workflows
1. Open n8n at `http://localhost:5678`
2. Go to Workflows → Import
3. Select each `.json` file from this directory
4. Save and activate each workflow

### 3. Configure Environment Variables
Add to n8n environment or `.env`:
```bash
N8N_WEBHOOK_SECRET=your_secure_random_string
```

Add to backend `.env`:
```bash
N8N_WEBHOOK_SECRET=your_secure_random_string
FRONTEND_URL=http://localhost:3000
```

### 4. Test Workflows
1. **Daily Job Discovery**: Click "Execute Workflow" on the daily workflow
2. **Manual Import**: POST to `http://localhost:5678/webhook/job-import` with:
   ```json
   { "url": "https://jobs.lever.co/company/backend-engineer" }
   ```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/n8n/users/active` | GET | Get users with job preferences |
| `/api/n8n/webhook/job-discovery` | POST | Trigger job discovery for users |
| `/api/n8n/webhook/match-and-prepare` | POST | Match specific job/user |
| `/api/n8n/webhook/notify` | POST | Send notification email |
| `/api/n8n/jobs/pending-match` | GET | Get unmatched recent jobs |
| `/api/n8n/webhook/followup-check` | POST | Check and send follow-ups |

## Security

All n8n webhook endpoints require `X-N8N-Secret` header matching the backend's `N8N_WEBHOOK_SECRET`. Generate a secure secret:

```bash
openssl rand -hex 32
```

## Customization

### Change Schedule
Edit the cron expression in the trigger node:
- Daily: `0 6 * * *` (6 AM)
- Every 6 hours: `0 */6 * * *`
- Weekdays only: `0 6 * * 1-5`

### Add More Sources
In `daily-job-discovery.json`, the `Trigger Job Discovery` node sends `sources` array. Modify to include:
```json
"sources": ["greenhouse", "lever", "ashby", "company", "manual"]
```

### Notification Channels
The `Send Notification` node calls `/api/n8n/webhook/notify` which currently sends email. To add Telegram/Slack:
1. Modify `backend/services/notification_service.py`
2. Add `send_telegram` / `send_slack` methods
3. Update the notify webhook to handle multiple channels

## Monitoring

Check n8n execution logs for:
- Job discovery success/failure counts
- Notification delivery status
- Follow-up reminders sent

Backend logs (in `backend/uvicorn.log`) show:
- Job import results
- AI matching results
- Email sending status