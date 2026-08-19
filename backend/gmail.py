import base64
import json
import logging
import time
import urllib.parse

import httpx
import jwt as pyjwt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

logger = logging.getLogger('cold_email_agent')

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'openid',
    'email',
]
# Sign-in scopes: identity only, no mailbox access.
LOGIN_SCOPES = ['openid', 'email', 'profile']


def _build_authorize_url(state, redirect_uri, scopes, extra=None):
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'state': state,
    }
    if extra:
        params.update(extra)
    return f'{AUTH_URL}?{urllib.parse.urlencode(params)}'


def build_authorize_url(state, redirect_uri):
    return _build_authorize_url(
        state, redirect_uri, SCOPES,
        extra={'access_type': 'offline', 'prompt': 'consent'},
    )


def build_login_authorize_url(state, redirect_uri):
    return _build_authorize_url(state, redirect_uri, LOGIN_SCOPES, extra={'prompt': 'select_account'})


def _email_from_id_token(id_token):
    claims = _id_token_claims(id_token)
    return claims.get('email') if claims else None


def _id_token_claims(id_token):
    if not id_token:
        return {}
    try:
        return pyjwt.decode(id_token, options={'verify_signature': False})
    except pyjwt.PyJWTError:
        return {}


def _token_response(data):
    response = httpx.post(
        TOKEN_URL,
        data=data,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def exchange_code(code, redirect_uri):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError('GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured')
    data = _token_response(
        {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
    )
    if 'refresh_token' not in data:
        raise RuntimeError('Google did not return a refresh token (access_type=offline required)')
    email = _email_from_id_token(data.get('id_token'))
    return {
        'email': email,
        'access_token': data.get('access_token'),
        'refresh_token': data.get('refresh_token'),
        'expires_in': data.get('expires_in', 3600),
    }


def exchange_login_code(code, redirect_uri):
    """Exchange an authorization code for sign-in identity claims (no refresh token)."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError('GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured')
    data = _token_response(
        {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }
    )
    claims = _id_token_claims(data.get('id_token'))
    if not claims or not claims.get('email'):
        raise RuntimeError('Google did not return a verified email')
    return {
        'email': claims.get('email'),
        'full_name': claims.get('name', ''),
        'avatar_url': claims.get('picture', ''),
        'email_verified': bool(claims.get('email_verified')),
    }


def build_gmail_service(refresh_token):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError('GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured')
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    try:
        from google.auth.transport.requests import Request

        creds.refresh(Request())
    except Exception as exc:
        raise RuntimeError(f'Gmail token refresh failed: {exc}') from exc
    return build('gmail', 'v1', credentials=creds)


def send_via_gmail(refresh_token, sender_email, subject, body, recipient_email):
    from email.mime.text import MIMEText

    service = build_gmail_service(refresh_token)
    message = MIMEText(body)
    message['to'] = recipient_email
    message['subject'] = subject
    if sender_email:
        message['from'] = sender_email
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return True