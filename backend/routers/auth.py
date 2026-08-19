import datetime as dt
import secrets

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .. import gmail
from ..config import API_BASE, FRONTEND_URL
from ..database import get_db
from ..models import PasswordReset, Profile, Subscription, User
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
    hash_password,
    verify_password,
)

router = APIRouter(prefix='/api/auth', tags=['auth'])

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


@router.post('/signup', response_model=TokenOut)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email.lower()).first()
    if exists:
        raise HTTPException(status_code=409, detail='An account with this email already exists')
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name or '',
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.add(Subscription(user_id=user.id, plan='free', status='active'))
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user, db))


@router.post('/login', response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
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