from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    recipients,
)
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
    allow_origins=[FRONTEND_URL, 'http://localhost:3001', 'http://127.0.0.1:3001'],
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
)

for router in (auth, recipients, email_accounts, agents, campaigns, emails, analytics, billing, chat, admin, profile_assets):
    app.include_router(router.router)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/')
def root():
    return {'name': 'Cold Email AI API', 'docs': '/docs', 'health': '/health'}
