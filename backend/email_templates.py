"""
Codessy email templates — HTML emails with branding.
All templates use inline CSS for maximum email client compatibility.
"""

import os

from .config import FRONTEND_URL, SMTP_FROM_NAME

# Brand colors
_BLUE = '#2875F0'
_PURPLE = '#7340E8'
_GREEN = '#10B981'
_CORAL = '#F45F72'
_DARK = '#070B1F'
_BG = '#F8FAFC'
_TEXT = '#1E293B'
_MUTED = '#64748B'
_BORDER = '#E2E8F0'

# Logo SVG inline (simplified for email)
_LOGO_SVG = '''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="48" height="48" role="img" aria-label="Codessy">
<defs>
  <linearGradient id="eb" x1="22" y1="0" x2="58" y2="36" gradientUnits="userSpaceOnUse">
    <stop stop-color="#35A7FF"/><stop offset="1" stop-color="#2875F0"/>
  </linearGradient>
  <linearGradient id="ep" x1="64" y1="0" x2="100" y2="36" gradientUnits="userSpaceOnUse">
    <stop stop-color="#9B5CFF"/><stop offset="1" stop-color="#7340E8"/>
  </linearGradient>
  <linearGradient id="eg" x1="22" y1="40" x2="58" y2="76" gradientUnits="userSpaceOnUse">
    <stop stop-color="#22D3A6"/><stop offset="1" stop-color="#10B981"/>
  </linearGradient>
  <linearGradient id="ec" x1="64" y1="40" x2="100" y2="76" gradientUnits="userSpaceOnUse">
    <stop stop-color="#FF9A55"/><stop offset="1" stop-color="#F45F72"/>
  </linearGradient>
</defs>
  <rect width="120" height="120" rx="28" fill="#070B1F"/>
  <g transform="translate(-1 22)">
    <path d="M22 18C22 8.059 30.059 0 40 0h18v18c0 9.941-8.059 18-18 18H22V18Z" fill="url(#eb)"/>
    <circle cx="82" cy="18" r="18" fill="url(#ep)"/>
    <path d="M22 40h18c9.941 0 18 8.059 18 18v18H40c-9.941 0-18-8.059-18-18V40Z" fill="url(#eg)"/>
    <path d="M64 40h18c9.941 0 18 8.059 18 18v18H82c-9.941 0-18-8.059-18-18V40Z" fill="url(#ec)"/>
  </g>
</svg>'''


def _base(title, subtitle, content_html):
    """Base email template wrapper."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{_BG};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:40px 20px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;">

<!-- Logo -->
<tr><td align="center" style="padding-bottom:24px;">
{_LOGO_SVG}
<div style="font-size:20px;font-weight:700;color:{_DARK};margin-top:8px;letter-spacing:-0.5px;">Codessy</div>
<div style="font-size:11px;color:{_MUTED};letter-spacing:1px;text-transform:uppercase;">BUILD. AUTOMATE. SCALE.</div>
</td></tr>

<!-- Card -->
<tr><td style="background:#fff;border-radius:16px;border:1px solid {_BORDER};overflow:hidden;">
  <!-- Header -->
  <div style="background:linear-gradient(135deg,{_BLUE},{_PURPLE});padding:32px 40px;text-align:center;">
    <div style="font-size:14px;color:rgba(255,255,255,0.8);margin-bottom:4px;">{subtitle}</div>
    <div style="font-size:24px;font-weight:700;color:#fff;">{title}</div>
  </div>
  <!-- Body -->
  <div style="padding:32px 40px;">
    {content_html}
  </div>
</td></tr>

<!-- Footer -->
<tr><td align="center" style="padding:24px 0;">
<div style="font-size:12px;color:{_MUTED};">
  This email was sent by {SMTP_FROM_NAME}. If you didn't expect this, you can safely ignore it.
</div>
<div style="font-size:11px;color:{_MUTED};margin-top:8px;">
  <a href="{FRONTEND_URL}" style="color:{_BLUE};text-decoration:none;">{SMTP_FROM_NAME}</a> &mdash; Cold email automation
</div>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''


def verification_email(verification_link, user_name=''):
    """Email verification template."""
    greeting = f'Hi {user_name},' if user_name else 'Hi there,'
    content = f'''
    <p style="margin:0 0 16px;font-size:15px;color:{_TEXT};">{greeting}</p>
    <p style="margin:0 0 24px;font-size:15px;color:{_TEXT};">
      Welcome to {SMTP_FROM_NAME}! Please verify your email address to get started.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:0 0 24px;">
      <a href="{verification_link}" style="
        display:inline-block;
        background:linear-gradient(135deg,{_BLUE},{_PURPLE});
        color:#fff;
        font-size:15px;
        font-weight:600;
        text-decoration:none;
        padding:14px 48px;
        border-radius:10px;
      ">Verify Email Address</a>
    </td></tr>
    </table>
    <p style="margin:0 0 8px;font-size:13px;color:{_MUTED};">
      Or copy this link: <span style="word-break:break-all;color:{_BLUE};">{verification_link}</span>
    </p>
    <p style="margin:0;font-size:13px;color:{_MUTED};">
      This link expires in 48 hours. If you didn't create an account, ignore this email.
    </p>
    '''
    return _base('Verify Your Email', 'One step away', content)


def password_reset_email(reset_link, user_name=''):
    """Password reset template."""
    greeting = f'Hi {user_name},' if user_name else 'Hi there,'
    content = f'''
    <p style="margin:0 0 16px;font-size:15px;color:{_TEXT};">{greeting}</p>
    <p style="margin:0 0 24px;font-size:15px;color:{_TEXT};">
      We received a request to reset your {SMTP_FROM_NAME} password. Click the button below to choose a new password.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:0 0 24px;">
      <a href="{reset_link}" style="
        display:inline-block;
        background:linear-gradient(135deg,{_BLUE},{_PURPLE});
        color:#fff;
        font-size:15px;
        font-weight:600;
        text-decoration:none;
        padding:14px 48px;
        border-radius:10px;
      ">Reset Password</a>
    </td></tr>
    </table>
    <p style="margin:0 0 8px;font-size:13px;color:{_MUTED};">
      Or copy this link: <span style="word-break:break-all;color:{_BLUE};">{reset_link}</span>
    </p>
    <p style="margin:0 0 16px;font-size:13px;color:{_MUTED};">
      This link expires in 1 hour.
    </p>
    <div style="border-top:1px solid {_BORDER};padding-top:16px;margin-top:8px;">
      <p style="margin:0;font-size:13px;color:{_MUTED};">
        If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.
      </p>
    </div>
    '''
    return _base('Reset Your Password', 'Password recovery', content)


def welcome_email(user_name='', login_link=''):
    """Welcome email sent after signup (optional)."""
    greeting = f'Hi {user_name}!' if user_name else 'Hi!'
    content = f'''
    <p style="margin:0 0 16px;font-size:15px;color:{_TEXT};">{greeting}</p>
    <p style="margin:0 0 24px;font-size:15px;color:{_TEXT};">
      Your {SMTP_FROM_NAME} account is ready. Here's what you can do:
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
      <tr><td style="padding:12px 0;border-bottom:1px solid {_BORDER};">
        <span style="color:{_GREEN};font-size:16px;">&#10003;</span>
        <span style="font-size:14px;color:{_TEXT};margin-left:8px;">Import recipients from Excel / CSV</span>
      </td></tr>
      <tr><td style="padding:12px 0;border-bottom:1px solid {_BORDER};">
        <span style="color:{_GREEN};font-size:16px;">&#10003;</span>
        <span style="font-size:14px;color:{_TEXT};margin-left:8px;">AI-personalized cold emails</span>
      </td></tr>
      <tr><td style="padding:12px 0;border-bottom:1px solid {_BORDER};">
        <span style="color:{_GREEN};font-size:16px;">&#10003;</span>
        <span style="font-size:14px;color:{_TEXT};margin-left:8px;">Connect your Gmail for sending</span>
      </td></tr>
      <tr><td style="padding:12px 0;">
        <span style="color:{_GREEN};font-size:16px;">&#10003;</span>
        <span style="font-size:14px;color:{_TEXT};margin-left:8px;">Track opens, clicks, and replies</span>
      </td></tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:0 0 16px;">
      <a href="{login_link}" style="
        display:inline-block;
        background:linear-gradient(135deg,{_BLUE},{_PURPLE});
        color:#fff;
        font-size:15px;
        font-weight:600;
        text-decoration:none;
        padding:14px 48px;
        border-radius:10px;
      ">Go to Dashboard</a>
    </td></tr>
    </table>
    <p style="margin:0;font-size:13px;color:{_MUTED};">
      You have <strong>50 free credits</strong> to get started. Happy sending!
    </p>
    '''
    return _base('Welcome to Codessy', 'Your account is ready', content)
