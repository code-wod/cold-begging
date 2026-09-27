from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import FRONTEND_URL
from .database import init_db
from .routers import (
    admin,
    agent,
    agents,
    analytics,
    applications,
    auth,
    billing,
    browser_stream,
    campaigns,
    chat,
    email_accounts,
    email_credits,
    emails,
    extension,
    job_application,
    job_portals,
    jobs,
    n8n,
    profile_assets,
    recipient_groups,
    recipients,
)
from .routers.auth import _user_out, verify_email
from .security import get_current_user
from .worker import CampaignWorker

worker = CampaignWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    worker.start()
    yield
    worker.stop()


app = FastAPI(title='Codessy API', version='1.0.0', lifespan=lifespan)

# ── CORS — only allow known origins ─────────────────────────────────────
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
# Add production origins from env if set
import os
PROD_ORIGINS = os.getenv('ALLOWED_ORIGINS', '')
if PROD_ORIGINS:
    ALLOWED_ORIGINS.extend([o.strip() for o in PROD_ORIGINS.split(',') if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
    allow_headers=['Authorization', 'Content-Type'],
    allow_credentials=True,
)

# ── Security headers middleware ──────────────────────────────────────────


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    # Allow iframes for resume preview endpoint
    if '/preview' not in request.url.path:
        response.headers['X-Frame-Options'] = 'DENY'
    if request.url.scheme == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains'
    return response


for router in (auth, recipients, recipient_groups, email_accounts, agents, campaigns, emails, analytics, billing, chat, admin, profile_assets, jobs, applications, n8n, job_portals, agent, job_application, browser_stream, extension, email_credits):
    app.include_router(router.router)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/')
def root():
    return {'name': 'Codessy API', 'docs': '/docs', 'health': '/health'}


@app.get('/user-email/verification')
def email_verification(token: str = '', email: str = ''):
    """Root-level verification endpoint: /user-email/verification?token=xxx&email=xxx"""
    from .database import SessionLocal as SL
    from .models import User, EmailVerification
    from .security import verify_password
    import datetime as _dt

    db = SL()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            raise HTTPException(status_code=400, detail='Invalid verification link')
        now = _dt.datetime.now(_dt.timezone.utc)
        cutoff = now - _dt.timedelta(hours=48)
        candidates = db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.used.is_(False),
            EmailVerification.expires_at > now,
            EmailVerification.created_at > cutoff,
        ).order_by(EmailVerification.id.desc()).limit(20).all()
        verification = next(
            (v for v in candidates if verify_password(token, v.token_hash)),
            None,
        )
        if not verification:
            raise HTTPException(status_code=400, detail='Invalid or expired verification link')
        verification.used = True
        user.is_verified = True
        db.commit()
        response = RedirectResponse(url=f'{FRONTEND_URL}/login?verified=1')
        response.set_cookie(
            'email_verified', 'true',
            max_age=3600, httponly=True, samesite='lax', secure=True,
        )
        return response
    finally:
        db.close()
