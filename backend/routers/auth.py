import datetime as dt
import logging
import secrets
import smtplib
from email.mime.text import MIMEText

import bcrypt
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .. import gmail
from ..config import API_BASE, FRONTEND_URL, SMTP_SENDER_EMAIL, SMTP_SENDER_APP_PASSWORD, SMTP_HOST, SMTP_PORT, SMTP_FROM_NAME
from ..database import get_db
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
    """Send verification email using SMTP credentials from config."""
    sender_email = SMTP_SENDER_EMAIL
    sender_password = SMTP_SENDER_APP_PASSWORD
    verification_link = f'{API_BASE}/user-email/verification?token={token}&email={user.email}'
    msg = MIMEText(f'Click here to verify your email: {verification_link}')
    msg['Subject'] = f'Email Verification - {SMTP_FROM_NAME}'
    msg['From'] = sender_email
    msg['To'] = user.email
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, user.email, msg.as_string())
        return True
    except Exception as e:
        logger.warning('Verification email failed for %s: %s', user.email, e)
        return False


@router.post('/signup', response_model=TokenOut)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email.lower()).first()
    if exists:
        raise HTTPException(status_code=409, detail='An account with this email already exists')
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name or '',
        phone=payload.phone,
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.add(Subscription(user_id=user.id, plan='free', status='active'))
    # Generate and send verification token
    token = secrets.token_urlsafe(32)
    verification = EmailVerification(
        user_id=user.id,
        token_hash=hash_password(token),
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=48),
    )
    db.add(verification)
    db.commit()
    db.refresh(user)
    # Send verification email (non-blocking)
    _send_verification_email(user, token)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user, db))


@router.post('/login', response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail='Please verify your email first. Check your inbox for the verification link.',
        )
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
    return HTMLResponse(
        f'<script>window.location.href="{FRONTEND_URL}/login#{params}"</script>'
    )


@router.get('/google')
def google_login_url():
    if not gmail.GOOGLE_CLIENT_ID or not gmail.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail='Google OAuth is not configured on the server (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)',
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
def send_verification(user: User = Depends(get_current_user_unverified), db: Session = Depends(get_db)):
    token = secrets.token_urlsafe(32)
    token_hash = hash_password(token)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=48)
    verification = EmailVerification(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    # Send verification email
    _send_verification_email(user, token)
    return {'message': 'Verification email sent'}


@router.get('/verify-email')
def verify_email(token: str, db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc)
    # bcrypt salts random, so we can't filter by hash equality—scan and verify_password
    candidates = db.query(EmailVerification).filter(
        EmailVerification.used.is_(False),
        EmailVerification.expires_at > now,
    ).all()
    verification = next(
        (v for v in candidates if verify_password(token, v.token_hash)),
        None,
    )
    if not verification:
        raise HTTPException(status_code=400, detail='Invalid or expired verification token')
    verification.used = True
    user = db.query(User).filter(User.id == verification.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.is_verified = True
    db.commit()
    return {'message': 'Email verified successfully', 'is_verified': True}


@router.patch('/profile', response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if payload.bio is not None:
        if not profile:
            profile = Profile(user_id=user.id)
            db.add(profile)
        profile.bio = payload.bio
    db.commit()
    db.refresh(user)
    return _user_out(user, db)


@router.post('/forgot-password')
def forgot_password(payload: ResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        return {'message': 'If that email exists, a reset link has been generated.'}
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=hash_password(token),
            expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
        )
    )
    db.commit()
    # No email transport configured: log the reset token for local development.
    import logging

    logging.getLogger('cold_email_agent').info(
        'Password reset token for %s: %s', user.email, token
    )
    return {'message': 'If that email exists, a reset link has been generated.'}


@router.post('/reset-password')
def reset_password(payload: ResetConfirmRequest, db: Session = Depends(get_db)):
    reset = (
        db.query(PasswordReset)
        .filter(PasswordReset.used.is_(False))
        .order_by(PasswordReset.id.desc())
        .all()
    )
    match = None
    for row in reset:
        if verify_password(payload.token, row.token_hash):
            match = row
            break
    if not match:
        raise HTTPException(status_code=400, detail='Invalid or expired reset token')
    if match.expires_at < dt.datetime.now(dt.timezone.utc):
        raise HTTPException(status_code=400, detail='Reset token has expired')
    match.used = True
    user = db.query(User).filter(User.id == match.user_id).first()
    user.password_hash = hash_password(payload.password)
    db.commit()
    return {'message': 'Password updated. You can now log in.'}