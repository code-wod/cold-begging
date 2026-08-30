from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import FRONTEND_URL
from .database import init_db
from .routers import (
    admin,
    agents,
    analytics,
    auth,
    billing,
    campaigns,
    chat,
    email_accounts,
    emails,
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


app = FastAPI(title='Cold Email AI', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, 'http://localhost:3001', 'http://127.0.0.1:3001', 'http://10.12.25.237:3000', 'http://localhost:3000', 'http://localhost:3000/', 'https://cold-begging.vercel.app', 'https://cold-begging-c4rm2olv2-gk022135s-projects.vercel.app'],
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
)

for router in (auth, recipients, recipient_groups, email_accounts, agents, campaigns, emails, analytics, billing, chat, admin, profile_assets):
    app.include_router(router.router)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/')
def root():
    return {'name': 'Cold Email AI API', 'docs': '/docs', 'health': '/health'}


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
        candidates = db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.used.is_(False),
            EmailVerification.expires_at > now,
        ).all()
        verification = next(
            (v for v in candidates if verify_password(token, v.token_hash)),
            None,
        )
        if not verification:
            raise HTTPException(status_code=400, detail='Invalid or expired verification link')
        verification.used = True
        user.is_verified = True
        db.commit()
        # Set verification cookie and redirect to frontend
        response = RedirectResponse(url=f'{FRONTEND_URL}/login?verified=1')
        response.set_cookie('email_verified', 'true', max_age=3600, httponly=True, samesite='lax')
        return response
    finally:
        db.close()
