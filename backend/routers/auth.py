import datetime as dt
import hashlib
import logging
import re
import secrets
import smtplib
import time
from collections import defaultdict
from email.mime.text import MIMEText

import bcrypt
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import gmail
from ..config import (
    API_BASE,
    FRONTEND_URL,
    RATE_LIMIT_LOGIN_ATTEMPTS,
    RATE_LIMIT_LOGIN_WINDOW,
    RATE_LIMIT_RESET_ATTEMPTS,
    RATE_LIMIT_RESET_WINDOW,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)
from ..database import get_db
from ..email_credit_service import grant_free_credits
from ..email_templates import password_reset_email, verification_email
from ..encryption import decrypt_plaintext, encrypt_plaintext
from ..models import PasswordReset, Profile, Subscription, User, EmailVerification
from ..schemas import (
    LoginRequest,
    ProfileUpdate,
    ResetConfirmRequest,
    ResetRequest,
    SignupRequest,
    TokenOut,
    UserOut,
)
from ..security import (
    SECRET_KEY,
    create_access_token,
    get_current_user,
    get_current_user_unverified,
    hash_password,
    verify_password,
)

router = APIRouter(prefix='/api/auth', tags=['auth'])

logger = logging.getLogger('cold_email_agent')

OAUTH_ALGORITHM = 'HS256'

# ── In-memory rate limiter ──────────────────────────────────────────────
_rate_store = defaultdict(list)  # key → [timestamp, ...]


def _is_rate_limited(key, max_attempts, window_seconds):
    now = time.time()
    cutoff = now - window_seconds
    _rate_store[key] = [t for t in _rate_store[key] if t > cutoff]
    if len(_rate_store[key]) >= max_attempts:
        return True
    _rate_store[key].append(now)
    return False


def _check_password_strength(password):
    """Validate password meets minimum security requirements."""
    errors = []
    if len(password) < 8:
        errors.append('at least 8 characters')
    if len(password) > 128:
        errors.append('at most 128 characters')
    if not re.search(r'[a-z]', password):
        errors.append('at least one lowercase letter')
    if not re.search(r'[A-Z]', password):
        errors.append('at least one uppercase letter')
    if not re.search(r'[0-9]', password):
        errors.append('at least one digit')
    return errors


def _user_out(user, db):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        is_admin=bool(user.is_admin),
        plan=sub.plan if sub else 'free',
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _send_verification_email(user, token):
    """Send verification email using the active SMTP provider."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning('SMTP not configured — skipping verification email for %s', user.email)
        return False
    verification_link = f'{API_BASE}/user-email/verification?token={token}&email={user.email}'
    html_body = verification_email(verification_link, user.full_name)
    msg = MIMEText(html_body, 'html')
    msg['Subject'] = f'Verify your {SMTP_FROM_NAME} email'
    msg['From'] = f'{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>'
    msg['To'] = user.email
    msg['Reply-To'] = SMTP_FROM_EMAIL
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.sendmail(SMTP_FROM_EMAIL, user.email, msg.as_string())
        return True
    except Exception as e:
        logger.warning('Verification email failed: %s', type(e).__name__)
        return False


def _send_password_reset_email(user, token):
    """Send password reset email using the active SMTP provider."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning('SMTP not configured — skipping reset email for %s', user.email)
        return False
    reset_link = f'{FRONTEND_URL}/login?reset_token={token}'
    html_body = password_reset_email(reset_link, user.full_name)
    msg = MIMEText(html_body, 'html')
    msg['Subject'] = f'{SMTP_FROM_NAME} — Reset your password'
    msg['From'] = f'{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>'
    msg['To'] = user.email
    msg['Reply-To'] = SMTP_FROM_EMAIL
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.sendmail(SMTP_FROM_EMAIL, user.email, msg.as_string())
        return True
    except Exception as e:
        logger.warning('Password reset email failed: %s', type(e).__name__)
        return False


@router.post('/signup', response_model=TokenOut)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limit signup per IP
    client_ip = request.client.host if request.client else 'unknown'
    if _is_rate_limited(f'signup:{client_ip}', 10, 3600):
        raise HTTPException(status_code=429, detail='Too many signup attempts. Try again later.')

    # Validate password strength
    pw_errors = _check_password_strength(payload.password)
    if pw_errors:
        raise HTTPException(status_code=400, detail=f'Password too weak: {", ".join(pw_errors)}')

    # Normalize email (lowercase, strip whitespace)
    email = payload.email.strip().lower()

    # Check duplicate (DB constraint also enforces this)
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=409, detail='An account with this email already exists')

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=(payload.full_name or '').strip()[:255],
        phone=(payload.phone or '').strip()[:64],
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.add(Subscription(user_id=user.id, plan='free', status='active'))
    grant_free_credits(db, user.id)

    # Generate verification token
    token = secrets.token_urlsafe(32)
    verification = EmailVerification(
        user_id=user.id,
        token_hash=hash_password(token),
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=48),
    )
    db.add(verification)

    # Invalidate any previous unused verifications for this user
    db.query(EmailVerification).filter(
        EmailVerification.user_id == user.id,
        EmailVerification.used.is_(False),
    ).update({'used': True})

    db.commit()
    db.refresh(user)

    _send_verification_email(user, token)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user, db))


@router.post('/login', response_model=TokenOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else 'unknown'
    email = payload.email.strip().lower()

    # Rate limit per email+IP
    if _is_rate_limited(f'login:{email}', RATE_LIMIT_LOGIN_ATTEMPTS, RATE_LIMIT_LOGIN_WINDOW):
        raise HTTPException(status_code=429, detail='Too many login attempts. Please try again later.')
    if _is_rate_limited(f'login_ip:{client_ip}', RATE_LIMIT_LOGIN_ATTEMPTS * 3, RATE_LIMIT_LOGIN_WINDOW):
        raise HTTPException(status_code=429, detail='Too many login attempts. Please try again later.')

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail='Please verify your email first. Check your inbox for the verification link.',
        )

    # Reset rate limit on successful login
    _rate_store.pop(f'login:{email}', None)

    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user, db))


def _login_redirect_uri():
    return f'{API_BASE}/api/auth/google/callback'


def _oauth_state():
    payload = {
        'nonce': secrets.token_urlsafe(16),
        'exp': dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10),
    }
    return pyjwt.encode(payload, SECRET_KEY, algorithm=OAUTH_ALGORITHM)


def _verify_oauth_state(state):
    try:
        pyjwt.decode(state, SECRET_KEY, algorithms=[OAUTH_ALGORITHM])
        return True
    except pyjwt.PyJWTError:
        return False


def _redirect_to_login(params):
    # Sanitize params to prevent XSS
    safe_params = params.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#39;')
    return HTMLResponse(
        f'<script>window.location.href="{FRONTEND_URL}/login#{safe_params}"</script>'
    )


@router.get('/google')
def google_login_url():
    if not gmail.GOOGLE_CLIENT_ID or not gmail.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail='Google OAuth is not configured on the server',
        )
    return {'authorize_url': gmail.build_login_authorize_url(_oauth_state(), _login_redirect_uri())}


@router.get('/google/callback')
def google_login_callback(
    code: str,
    state: str,
    error: str = '',
    db: Session = Depends(get_db),
):
    if error or not _verify_oauth_state(state):
        return _redirect_to_login('google_error=1')
    try:
        info = gmail.exchange_login_code(code, _login_redirect_uri())
    except Exception:
        return _redirect_to_login('google_error=1')
    email = info['email'].lower()
    user = db.query(User).filter(User.email == email).first()
    is_new = False
    if not user:
        is_new = True
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            full_name=info.get('full_name', ''),
            avatar_url=info.get('avatar_url', ''),
            is_verified=bool(info.get('email_verified')),
        )
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id))
        db.add(Subscription(user_id=user.id, plan='free', status='active'))
        grant_free_credits(db, user.id)
    else:
        if info.get('full_name') and not user.full_name:
            user.full_name = info['full_name']
        if info.get('avatar_url') and not user.avatar_url:
            user.avatar_url = info['avatar_url']
        if info.get('email_verified'):
            user.is_verified = True
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return _redirect_to_login(f'google_token={token}{"&new=1" if is_new else ""}')


@router.get('/me', response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_out(user, db)


@router.get('/subscription', response_model=dict)
def subscription_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    plan = sub.plan if sub else 'free'
    return {'is_pro': plan == 'pro', 'plan': plan}


@router.post('/send-verification')
def send_verification(
    request: Request,
    user: User = Depends(get_current_user_unverified),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else 'unknown'
    if _is_rate_limited(f'verify:{user.id}', 3, 3600):
        raise HTTPException(status_code=429, detail='Too many verification requests. Try again in an hour.')

    # Invalidate old unused tokens
    db.query(EmailVerification).filter(
        EmailVerification.user_id == user.id,
        EmailVerification.used.is_(False),
    ).update({'used': True})

    token = secrets.token_urlsafe(32)
    verification = EmailVerification(
        user_id=user.id,
        token_hash=hash_password(token),
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=48),
    )
    db.add(verification)
    db.commit()

    _send_verification_email(user, token)
    return {'message': 'Verification email sent'}


@router.get('/verify-email')
def verify_email(token: str, db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc)
    # Only check recent unused tokens (last 48h) to avoid O(n) bcrypt scan
    cutoff = now - dt.timedelta(hours=48)
    candidates = db.query(EmailVerification).filter(
        EmailVerification.used.is_(False),
        EmailVerification.expires_at > now,
        EmailVerification.created_at > cutoff,
    ).order_by(EmailVerification.id.desc()).limit(20).all()

    verification = next(
        (v for v in candidates if verify_password(token, v.token_hash)),
        None,
    )
    if not verification:
        raise HTTPException(status_code=400, detail='Invalid or expired verification token')

    verification.used = True
    user = db.query(User).filter(User.id == verification.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail='Invalid verification link')
    user.is_verified = True
    db.commit()
    return {'message': 'Email verified successfully', 'is_verified': True}


@router.post('/detect-timezone')
def detect_timezone(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save the browser-detected timezone to the user profile."""
    tz = (payload.get('timezone') or '').strip()[:64]
    if not tz:
        return {'timezone': user.timezone or 'UTC'}
    user.timezone = tz
    db.commit()
    return {'timezone': user.timezone}


@router.patch('/profile', response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()[:255]
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url[:1024]
    if payload.timezone is not None:
        user.timezone = payload.timezone.strip()[:64] or 'UTC'
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if payload.bio is not None:
        if not profile:
            profile = Profile(user_id=user.id)
            db.add(profile)
        profile.bio = payload.bio[:5000]
    db.commit()
    db.refresh(user)
    return _user_out(user, db)


@router.post('/forgot-password')
def forgot_password(payload: ResetRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else 'unknown'
    email = payload.email.strip().lower()

    # Rate limit per email and per IP
    if _is_rate_limited(f'reset:{email}', RATE_LIMIT_RESET_ATTEMPTS, RATE_LIMIT_RESET_WINDOW):
        return {'message': 'If that email exists, a reset link has been generated.'}
    if _is_rate_limited(f'reset_ip:{client_ip}', RATE_LIMIT_RESET_ATTEMPTS * 5, RATE_LIMIT_RESET_WINDOW):
        return {'message': 'If that email exists, a reset link has been generated.'}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Generic response — no email enumeration
        return {'message': 'If that email exists, a reset link has been generated.'}

    # Invalidate old reset tokens
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used.is_(False),
    ).update({'used': True})

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=hash_password(token),
            expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
        )
    )
    db.commit()

    # Send reset email (never log the token)
    _send_password_reset_email(user, token)

    return {'message': 'If that email exists, a reset link has been generated.'}


@router.post('/reset-password')
def reset_password(payload: ResetConfirmRequest, db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc)
    # Only check recent unused tokens
    cutoff = now - dt.timedelta(hours=1)
    candidates = db.query(PasswordReset).filter(
        PasswordReset.used.is_(False),
        PasswordReset.expires_at > now,
        PasswordReset.created_at > cutoff,
    ).order_by(PasswordReset.id.desc()).limit(10).all()

    match = None
    for row in candidates:
        if verify_password(payload.token, row.token_hash):
            match = row
            break

    if not match:
        raise HTTPException(status_code=400, detail='Invalid or expired reset token')
    if match.expires_at < now:
        raise HTTPException(status_code=400, detail='Reset token has expired')

    # Validate new password strength
    pw_errors = _check_password_strength(payload.password)
    if pw_errors:
        raise HTTPException(status_code=400, detail=f'Password too weak: {", ".join(pw_errors)}')

    match.used = True
    user = db.query(User).filter(User.id == match.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail='Invalid reset token')
    user.password_hash = hash_password(payload.password)
    db.commit()

    return {'message': 'Password updated. You can now log in.'}
