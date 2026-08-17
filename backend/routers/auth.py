import datetime as dt
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix='/api/auth', tags=['auth'])


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