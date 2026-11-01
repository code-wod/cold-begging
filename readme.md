# Cold Begging

## New Guidelines for developer for project setup in their local
- First Step clone the repositry
- after clone the repo move to desired directory like backend/ or frontend/
- install the dependencies in respective dirctires
- run the respective command in desired directory 

A cold email automation system for job opportunity outreach.

## Architecture

- `backend/` — FastAPI service that processes Excel data, generates personalized emails, and optionally sends them via Gmail SMTP or Gmail API.
- `frontend/` — Next.js app for uploading the Excel file and controlling dry-run/send behavior.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Environment variables:

- `ANTHROPIC_API_KEY`
- `SENDER_EMAIL`
- `GMAIL_APP_PASSWORD`
- `GOOGLE_CREDENTIALS_PATH`
- `FLASK_SECRET_KEY` (not used in backend)

Run backend:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Excel format

Required columns:

- Email
- Company Name
- Industry
- Company Website
- Job Role
- Position Level

## Notes

- The frontend calls backend `/process` on `http://localhost:8000/process`.
- Use dry run first to verify generated emails.
- Sending via Gmail API requires credentials JSON.
