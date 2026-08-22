import os
import secrets

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

# Storage for uploaded resume PDFs (gitignored).
UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads'))

# Email verification settings (override via env: SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD)
SMTP_SENDER_EMAIL = os.getenv('SMTP_SENDER_EMAIL', 'gk022135@gmail.com')
SMTP_SENDER_APP_PASSWORD = os.getenv('SMTP_SENDER_APP_PASSWORD', 'aipq ucst eval rnbg')  # Google App Password
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'Cold Begging')