import os
import secrets
import sys

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _persist_secret(filename, env_name):
    value = os.getenv(env_name)
    if value:
        return value
    path = os.path.join(BASE_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            return handle.read().strip()
    value = secrets.token_urlsafe(48)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(value)
    return value


DATABASE_URL = os.getenv('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "cold_email.db")}'
SECRET_KEY = _persist_secret('.secret_key', 'SECRET_KEY')


def _fernet_secret():
    env = os.getenv('FERNET_KEY')
    if env and len(env) == 44:
        return env
    from cryptography.fernet import Fernet

    path = os.path.join(BASE_DIR, '.fernet_key')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            existing = handle.read().strip()
        if len(existing) == 44:
            return existing
    value = Fernet.generate_key().decode()
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(value)
    return value


FERNET_KEY = _fernet_secret()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
API_BASE = os.getenv('API_BASE', 'http://localhost:8000')
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv('ACCESS_TOKEN_EXPIRE_DAYS', '7'))

# Comma-separated emails promoted to admin at startup (persisted in the DB).
ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '')

# Paid feature flag: the platform-managed model is a Pro plan feature.
MANAGED_MODEL_NAME = os.getenv('MANAGED_MODEL_NAME', 'claude-3.5')

# Sending-rate plan limits (emails/hour), configurable server-side.
FREE_RATE_PER_HOUR = int(os.getenv('FREE_RATE_PER_HOUR', '10'))
MAX_RATE_PER_HOUR = int(os.getenv('MAX_RATE_PER_HOUR', '50'))
MIN_RATE_PER_HOUR = int(os.getenv('MIN_RATE_PER_HOUR', '4'))

# Profile-asset limits (number of resumes a user may keep).
FREE_RESUME_LIMIT = int(os.getenv('FREE_RESUME_LIMIT', '5'))
PRO_RESUME_LIMIT = int(os.getenv('PRO_RESUME_LIMIT', '100'))

# Job hunting limits
FREE_JOB_MATCHES_PER_DAY = int(os.getenv('FREE_JOB_MATCHES_PER_DAY', '20'))
PRO_JOB_MATCHES_PER_DAY = int(os.getenv('PRO_JOB_MATCHES_PER_DAY', '200'))
AUTO_PREPARE_THRESHOLD = int(os.getenv('AUTO_PREPARE_THRESHOLD', '80'))
REVIEW_THRESHOLD = int(os.getenv('REVIEW_THRESHOLD', '70'))

# n8n integration
N8N_WEBHOOK_SECRET = os.getenv('N8N_WEBHOOK_SECRET', '')

# Storage for uploaded resume PDFs (gitignored).
UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads'))
RESUME_UPLOAD_DIR = os.getenv('RESUME_UPLOAD_DIR', os.path.join(UPLOAD_DIR, 'resumes'))

# ── SMTP Provider Configuration ─────────────────────────────────────────
# SMTP_METHOD must be 'gmail' or 'namecheap'. Fail fast if invalid/missing.
SMTP_METHOD = os.getenv('SMTP_METHOD', '').lower()
_VALID_SMTP_METHODS = {'gmail', 'namecheap'}
if SMTP_METHOD not in _VALID_SMTP_METHODS:
    print(
        f'[FATAL] SMTP_METHOD must be one of {_VALID_SMTP_METHODS}, got: {SMTP_METHOD!r}. '
        'Set SMTP_METHOD=gmail or SMTP_METHOD=namecheap in backend/.env',
        file=sys.stderr,
    )
    sys.exit(1)

# Gmail SMTP settings
GMAIL_SMTP_HOST = os.getenv('GMAIL_SMTP_HOST', 'smtp.gmail.com')
GMAIL_SMTP_PORT = int(os.getenv('GMAIL_SMTP_PORT', '465'))
GMAIL_SMTP_USERNAME = os.getenv('GMAIL_SMTP_USERNAME', '')
GMAIL_SMTP_PASSWORD = os.getenv('GMAIL_SMTP_PASSWORD', '')
GMAIL_FROM_EMAIL = os.getenv('GMAIL_FROM_EMAIL', '')

# Namecheap SMTP settings
NAMECHEAP_SMTP_HOST = os.getenv('NAMECHEAP_SMTP_HOST', 'mail.privateemail.com')
NAMECHEAP_SMTP_PORT = int(os.getenv('NAMECHEAP_SMTP_PORT', '465'))
NAMECHEAP_SMTP_USERNAME = os.getenv('NAMECHEAP_SMTP_USERNAME', '')
NAMECHEAP_SMTP_PASSWORD = os.getenv('NAMECHEAP_SMTP_PASSWORD', '')
NAMECHEAP_FROM_EMAIL = os.getenv('NAMECHEAP_FROM_EMAIL', '')

# Resolved SMTP settings — single source of truth for the active provider
if SMTP_METHOD == 'gmail':
    SMTP_HOST = GMAIL_SMTP_HOST
    SMTP_PORT = GMAIL_SMTP_PORT
    SMTP_USERNAME = GMAIL_SMTP_USERNAME
    SMTP_PASSWORD = GMAIL_SMTP_PASSWORD
    SMTP_FROM_EMAIL = GMAIL_FROM_EMAIL
else:  # namecheap
    SMTP_HOST = NAMECHEAP_SMTP_HOST
    SMTP_PORT = NAMECHEAP_SMTP_PORT
    SMTP_USERNAME = NAMECHEAP_SMTP_USERNAME
    SMTP_PASSWORD = NAMECHEAP_SMTP_PASSWORD
    SMTP_FROM_EMAIL = NAMECHEAP_FROM_EMAIL

SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'Codessy')

# Legacy aliases — used by auth.py for sending verification/reset emails
SMTP_SENDER_EMAIL = SMTP_FROM_EMAIL
SMTP_SENDER_APP_PASSWORD = SMTP_PASSWORD

# Browser Agent Configuration
PLAYWRIGHT_HEADLESS = os.getenv('PLAYWRIGHT_HEADLESS', 'false').lower() == 'true'
BROWSER_DATA_DIR = os.getenv('BROWSER_DATA_DIR', os.path.join(BASE_DIR, 'browser-data'))
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
JOB_AGENT_ENABLED = os.getenv('JOB_AGENT_ENABLED', 'false').lower() == 'true'
DEFAULT_DAILY_APPLICATION_LIMIT = int(os.getenv('DEFAULT_DAILY_APPLICATION_LIMIT', '15'))
DEFAULT_MIN_MATCH_SCORE = int(os.getenv('DEFAULT_MIN_MATCH_SCORE', '80'))
DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'
MAX_BROWSER_WORKERS = int(os.getenv('MAX_BROWSER_WORKERS', '3'))
MAX_USER_CONCURRENT_SESSIONS = int(os.getenv('MAX_USER_CONCURRENT_SESSIONS', '1'))

# Job Application Autofill
AUTOFILL_UPLOAD_DIR = os.getenv('AUTOFILL_UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads', 'autofill'))

# Email Verification (Go email-verifier API server)
EMAIL_VERIFIER_URL = os.getenv('EMAIL_VERIFIER_URL', 'http://localhost:8080')
EMAIL_VERIFIER_TIMEOUT = int(os.getenv('EMAIL_VERIFIER_TIMEOUT', '10'))

# Razorpay
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')

# Rate limiting (in-memory, per-server)
RATE_LIMIT_LOGIN_ATTEMPTS = int(os.getenv('RATE_LIMIT_LOGIN_ATTEMPTS', '5'))
RATE_LIMIT_LOGIN_WINDOW = int(os.getenv('RATE_LIMIT_LOGIN_WINDOW', '300'))  # seconds
RATE_LIMIT_RESET_ATTEMPTS = int(os.getenv('RATE_LIMIT_RESET_ATTEMPTS', '3'))
RATE_LIMIT_RESET_WINDOW = int(os.getenv('RATE_LIMIT_RESET_WINDOW', '3600'))  # seconds
