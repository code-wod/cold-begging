from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith('sqlite'):
    connect_args = {'check_same_thread': False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _promote_admins()


def _promote_admins():
    """Persistently promote users listed in ADMIN_EMAILS (comma-separated) to admin."""
    from .config import ADMIN_EMAILS
    from .models import User

    emails = [e.strip().lower() for e in (ADMIN_EMAILS or '').split(',') if e.strip()]
    if not emails:
        return
    db = SessionLocal()
    try:
        for email in emails:
            user = db.query(User).filter(User.email == email).first()
            if user and not user.is_admin:
                user.is_admin = True
        db.commit()
    finally:
        db.close()