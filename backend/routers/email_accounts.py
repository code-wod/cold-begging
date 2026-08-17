import smtplib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import gmail
from ..config import API_BASE, FRONTEND_URL
from ..database import get_db
from ..encryption import decrypt_plaintext, encrypt_plaintext
from ..models import EmailAccount, User
from ..schemas import EmailAccountIn, EmailAccountOut, EmailAccountUpdate
from ..security import create_access_token, decode_access_token, get_current_user

router = APIRouter(prefix='/api/email-accounts', tags=['email accounts'])


def _redirect_uri():
    return f'{API_BASE}/api/email-accounts/callback'


def _out(account):
    return EmailAccountOut(
        id=account.id,
        provider=account.provider,
        email=account.email,
        display_name=account.display_name or '',
        smtp_host=account.smtp_host or '',
        smtp_port=account.smtp_port or 0,
        smtp_secure=account.smtp_secure if account.smtp_secure is not None else True,
        smtp_username=account.smtp_username or '',
        is_default=bool(account.is_default),
        status=account.status,
        created_at=account.created_at.isoformat() if account.created_at else None,
    )


def _load(db, user, account_id):
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.id == account_id, EmailAccount.user_id == user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail='Email account not found')
    return account


def _set_default(db, user, account, is_default):
    if is_default:
        db.query(EmailAccount).filter(EmailAccount.user_id == user.id).update(
            {'is_default': False}, synchronize_session=False
        )
    account.is_default = bool(is_default)


@router.get('', response_model=list[EmailAccountOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = (
        db.query(EmailAccount).filter(EmailAccount.user_id == user.id).order_by(EmailAccount.id).all()
    )
    return [_out(a) for a in accounts]


@router.post('', response_model=EmailAccountOut)
def add_smtp_account(
    payload: EmailAccountIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.provider == 'smtp' and not payload.app_password:
        raise HTTPException(status_code=400, detail='A password is required for SMTP accounts')
    email = payload.email.lower()
    existing = (
        db.query(EmailAccount)
        .filter(EmailAccount.user_id == user.id, EmailAccount.email == email)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail='This email account is already connected')
    count = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).count()
    is_default = payload.is_default or count == 0
    account = EmailAccount(
        user_id=user.id,
        provider=payload.provider,
        email=email,
        display_name=payload.display_name,
        credentials_encrypted=encrypt_plaintext(payload.app_password) if payload.provider == 'smtp' else None,
        smtp_host=payload.smtp_host or 'smtp.gmail.com',
        smtp_port=payload.smtp_port or 465,
        smtp_secure=payload.smtp_secure if payload.smtp_secure is not None else True,
        smtp_username=payload.smtp_username,
        is_default=is_default,
        status='connected',
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _out(account)


@router.get('/connect')
def connect_google(user: User = Depends(get_current_user)):
    if not gmail.GOOGLE_CLIENT_ID or not gmail.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail='Google OAuth is not configured on the server (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)',
        )
    state = create_access_token(user.id)
    return {'authorize_url': gmail.build_authorize_url(state, _redirect_uri())}


@router.get('/callback')
def oauth_callback(code: str, state: str, error: str = '', db: Session = Depends(get_db)):
    if error:
        return f'<script>window.location.href="{FRONTEND_URL}/email-accounts?oauth_error=1"</script>'
    user_id = decode_access_token(state)
    if not user_id:
        raise HTTPException(status_code=401, detail='Invalid OAuth state')
    try:
        tokens = gmail.exchange_code(code, _redirect_uri())
    except Exception as exc:
        return f'<script>window.location.href="{FRONTEND_URL}/email-accounts?oauth_error=1"</script>'
    email = (tokens.get('email') or '').lower()
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.user_id == user_id, EmailAccount.email == email)
        .first()
    )
    if not account:
        count = db.query(EmailAccount).filter(EmailAccount.user_id == user_id).count()
        account = EmailAccount(
            user_id=user_id,
            provider='google',
            email=email,
            is_default=count == 0,
            status='connected',
        )
        db.add(account)
    account.credentials_encrypted = encrypt_plaintext(tokens['refresh_token'])
    account.status = 'connected'
    db.commit()
    return f'<script>window.location.href="{FRONTEND_URL}/email-accounts?connected=1"</script>'


@router.patch('/{account_id}', response_model=EmailAccountOut)
def update_account(
    account_id: int,
    payload: EmailAccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = _load(db, user, account_id)
    if payload.app_password:
        account.credentials_encrypted = encrypt_plaintext(payload.app_password)
        account.status = 'connected'
    for field in ('email', 'display_name', 'smtp_host', 'smtp_port', 'smtp_secure', 'smtp_username'):
        value = getattr(payload, field)
        if value is not None:
            setattr(account, field, value)
    if payload.is_default is not None:
        _set_default(db, user, account, payload.is_default)
    db.commit()
    db.refresh(account)
    return _out(account)


@router.post('/{account_id}/default', response_model=EmailAccountOut)
def set_default(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _load(db, user, account_id)
    _set_default(db, user, account, True)
    db.commit()
    db.refresh(account)
    return _out(account)


@router.post('/{account_id}/disconnect')
def disconnect_account(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _load(db, user, account_id)
    account.status = 'disconnected'
    account.credentials_encrypted = None
    db.commit()
    return {'ok': True}


@router.delete('/{account_id}')
def delete_account(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _load(db, user, account_id)
    db.delete(account)
    db.commit()
    return {'ok': True}


@router.post('/{account_id}/test')
def test_account(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _load(db, user, account_id)
    if not account.credentials_encrypted:
        raise HTTPException(status_code=400, detail='No credentials stored for this account')
    try:
        if account.provider == 'google':
            refresh_token = decrypt_plaintext(account.credentials_encrypted)
            gmail.build_gmail_service(refresh_token)
        else:
            password = decrypt_plaintext(account.credentials_encrypted)
            host = account.smtp_host or 'smtp.gmail.com'
            port = account.smtp_port or 465
            secure = account.smtp_secure if account.smtp_secure is not None else True
            username = account.smtp_username or account.email
            if secure:
                with smtplib.SMTP_SSL(host, port) as smtp:
                    smtp.login(username, password)
            else:
                with smtplib.SMTP(host, port) as smtp:
                    smtp.starttls()
                    smtp.login(username, password)
        account.status = 'connected'
        db.commit()
        return {'ok': True, 'status': 'connected', 'message': f'Connection to {account.email} verified'}
    except Exception as exc:
        account.status = 'error'
        db.commit()
        raise HTTPException(status_code=400, detail=f'Connection failed: {exc}')


def get_refresh_token(account):
    if not account or not account.credentials_encrypted:
        return None
    return decrypt_plaintext(account.credentials_encrypted)