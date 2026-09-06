import logging
import httpx
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models import User, EmailAccount, EmailLog, Application, Job
from backend.config import SMTP_SENDER_EMAIL, SMTP_SENDER_APP_PASSWORD, SMTP_HOST, SMTP_PORT, SMTP_FROM_NAME
from backend.encryption import decrypt_plaintext
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime as dt

logger = logging.getLogger('notification_service')


class NotificationService:
    """Service for sending notifications (email, Telegram, in-app)."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def send_job_match_notification(self, user: User, data: Dict[str, Any]):
        """Notify user of strong job matches."""
        job_count = data.get('job_count', 0)
        strong_matches = data.get('strong_matches', 0)
        applications_ready = data.get('applications_ready', 0)
        
        if job_count == 0:
            return
        
        subject = f"🎯 {job_count} new jobs found — {strong_matches} strong matches"
        
        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px 12px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🎯 New Job Matches Found</h1>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #e9ecef;">
                <p style="font-size: 16px;">Hi {user.full_name or 'there'},</p>
                <p>Your scheduled job discovery just completed. Here's what we found:</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="color: #6c757d;">Total jobs discovered</span>
                        <strong style="font-size: 18px;">{job_count}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="color: #6c757d;">Strong matches (≥80%)</span>
                        <strong style="font-size: 18px; color: #28a745;">{strong_matches}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #6c757d;">Applications ready to review</span>
                        <strong style="font-size: 18px; color: #007bff;">{applications_ready}</strong>
                    </div>
                </div>
                
                {self._format_top_matches(data.get('top_matches', []))}
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self._get_frontend_url()}/jobs" 
                       style="background: #667eea; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
                        View All Jobs →
                    </a>
                </div>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e9ecef;">
                <p style="color: #6c757d; font-size: 14px; text-align: center;">
                    You received this because you have job preferences configured. 
                    <a href="{self._get_frontend_url()}/job-preferences">Manage preferences</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        await self._send_email(user, subject, html)
    
    async def send_application_ready_notification(self, user: User, data: Dict[str, Any]):
        """Notify user when application package is ready."""
        app_id = data.get('application_id')
        job_title = data.get('job_title', 'Unknown Position')
        company_name = data.get('company_name', 'Unknown Company')
        match_score = data.get('match_score', 0)
        
        subject = f"✅ Application ready: {job_title} at {company_name} ({match_score}% match)"
        
        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 30px; border-radius: 12px 12px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">✅ Application Package Ready</h1>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #e9ecef;">
                <p>Your application for <strong>{job_title}</strong> at <strong>{company_name}</strong> is ready to review.</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p style="margin: 0;"><strong>Match Score:</strong> {match_score}%</p>
                    <p style="margin: 8px 0 0 0;"><strong>Package includes:</strong> Tailored cover letter, screening answers, recruiter email, recommended resume</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self._get_frontend_url()}/applications/{app_id}" 
                       style="background: #28a745; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
                        Review Application →
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        await self._send_email(user, subject, html)
    
    async def send_followup_notification(self, user: User, data: Dict[str, Any]):
        """Send follow-up reminder for pending applications."""
        app_id = data.get('application_id')
        job_title = data.get('job_title', 'Unknown Position')
        company_name = data.get('company_name', 'Unknown Company')
        days = data.get('days_since_applied', 0)
        status = data.get('status', 'applied')
        
        subject = f"📋 Follow up: {job_title} at {company_name} ({days} days ago)"
        
        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%); padding: 30px; border-radius: 12px 12px 0 0;">
                <h1 style="color: #333; margin: 0; font-size: 24px;">📋 Time to Follow Up</h1>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #e9ecef;">
                <p>It's been <strong>{days} days</strong> since you applied to <strong>{job_title}</strong> at <strong>{company_name}</strong>.</p>
                <p>Current status: <span style="background: #e9ecef; padding: 4px 12px; border-radius: 20px; font-size: 14px;">{status.replace('_', ' ').title()}</span></p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self._get_frontend_url()}/applications/{app_id}" 
                       style="background: #ffc107; color: #333; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
                        Update Status →
                    </a>
                </div>
                
                <p style="margin-top: 20px; font-size: 14px; color: #6c757d;">
                    Consider sending a polite follow-up email to the recruiter or hiring manager.
                </p>
            </div>
        </body>
        </html>
        """
        
        await self._send_email(user, subject, html)
    
    def _format_top_matches(self, matches: list) -> str:
        if not matches:
            return '<p style="color: #6c757d;">No strong matches this run. Try adjusting your preferences.</p>'
        
        items = []
        for m in matches[:5]:
            items.append(f"""
            <div style="background: white; padding: 16px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #667eea;">
                <strong>{m.get('title', 'Unknown')}</strong> at {m.get('company', 'Unknown')} — 
                <span style="color: #28a745; font-weight: 600;">{m.get('score', 0)}%</span>
                <br><small style="color: #6c757d;">{m.get('location', 'Remote')} · {m.get('type', 'Full-time')}</small>
            </div>
            """)
        return f'<div style="margin-top: 20px;"><strong>Top matches:</strong><br>{"".join(items)}</div>'
    
    def _get_frontend_url(self) -> str:
        from backend.config import FRONTEND_URL
        return FRONTEND_URL
    
    async def _send_email(self, user: User, subject: str, html: str):
        """Send email via user's default email account or system SMTP."""
        # Try user's default email account first
        account = self.db.query(EmailAccount).filter(
            EmailAccount.user_id == user.id,
            EmailAccount.is_default.is_(True),
            EmailAccount.status == 'connected'
        ).first()
        
        if account:
            await self._send_via_account(account, user.email, subject, html)
        else:
            # Fallback to system SMTP
            await self._send_via_system_smtp(user.email, subject, html)
    
    async def _send_via_account(self, account: EmailAccount, to_email: str, subject: str, html: str):
        """Send via user's connected email account."""
        try:
            if account.provider == 'google':
                from backend import gmail
                refresh_token = decrypt_plaintext(account.credentials_encrypted)
                if refresh_token:
                    gmail.send_via_gmail(refresh_token, account.email, subject, html, to_email)
                    return
            else:
                app_password = decrypt_plaintext(account.credentials_encrypted)
                if app_password:
                    await self._send_smtp(account, app_password, to_email, subject, html)
                    return
        except Exception as e:
            logger.warning('Failed to send via user account: %s', e)
        
        # Fallback
        await self._send_via_system_smtp(to_email, subject, html)
    
    async def _send_via_system_smtp(self, to_email: str, subject: str, html: str):
        """Send via system SMTP."""
        await self._send_smtp(
            type('obj', (object,), {
                'smtp_host': SMTP_HOST,
                'smtp_port': SMTP_PORT,
                'smtp_secure': True,
                'smtp_username': SMTP_SENDER_EMAIL,
                'email': SMTP_SENDER_EMAIL
            })(),
            SMTP_SENDER_APP_PASSWORD,
            to_email, subject, html
        )
    
    async def _send_smtp(self, account, password: str, to_email: str, subject: str, html: str):
        """Send email via SMTP."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SMTP_FROM_NAME} <{account.email}>"
        msg['To'] = to_email
        
        msg.attach(MIMEText(html, 'html'))
        
        host = account.smtp_host or SMTP_HOST
        port = account.smtp_port or SMTP_PORT
        secure = getattr(account, 'smtp_secure', True)
        username = account.smtp_username or account.email
        
        if secure:
            with smtplib.SMTP_SSL(host, port) as smtp:
                smtp.login(username, password)
                smtp.sendmail(account.email, to_email, msg.as_string())
        else:
            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.sendmail(account.email, to_email, msg.as_string())
    
    async def send_telegram(self, user: User, message: str):
        """Send Telegram notification (if user has connected bot)."""
        # Placeholder for Telegram integration
        # Would require storing user's chat_id and bot token
        pass


def get_notification_service(db: Session) -> NotificationService:
    return NotificationService(db)