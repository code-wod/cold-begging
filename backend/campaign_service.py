import datetime as dt
import json
import logging
import smtplib
import threading
from email.mime.text import MIMEText

from . import gmail
from .ai import AnthropicProvider, is_managed, provider_for
from .cold_email_agent import ColdEmailAgent
from .config import FREE_RATE_PER_HOUR, MANAGED_MODEL_NAME, MAX_RATE_PER_HOUR, MIN_RATE_PER_HOUR
from .database import SessionLocal
from .encryption import decrypt_plaintext
from .models import (
    AIAgent,
    AIModel,
    Campaign,
    CampaignRecipient,
    EmailAccount,
    EmailLog,
    GeneratedEmail,
    Recipient,
    Subscription,
    UsageRecord,
    User,
)

logger = logging.getLogger('cold_email_agent')

_generation_lock = threading.Lock()

# Email statuses we treat as "queued / not yet finished" for the worker.
QUEUED_STATUSES = ['generated', 'approved', 'scheduled']


def _plan_of(db, user):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    return sub.plan if sub else 'free'


def validate_rate(plan, emails_per_hour):
    """Validate an hourly sending rate against the plan. Returns an error string or None."""
    try:
        rate = int(emails_per_hour or MIN_RATE_PER_HOUR)
    except (TypeError, ValueError):
        return 'Invalid sending rate'
    if rate < MIN_RATE_PER_HOUR:
        return f'Sending speed must be at least {MIN_RATE_PER_HOUR} emails/hour'
    if rate > MAX_RATE_PER_HOUR:
        return f'Sending speed is capped at {MAX_RATE_PER_HOUR} emails/hour'
    if plan != 'pro' and rate > FREE_RATE_PER_HOUR:
        return (
            f'Free plan sending speed is capped at {FREE_RATE_PER_HOUR} emails/hour. '
            'Higher speeds require a Pro plan.'
        )
    return None


def rate_interval_seconds(campaign):
    """Interval between sends derived from the hourly rate (3600 / rate)."""
    rate = getattr(campaign, 'emails_per_hour', None) or 0
    if rate < MIN_RATE_PER_HOUR:
        return getattr(campaign, 'delay_seconds', None) or 0
    return max(1, int(3600 / rate))


def load_agent_model(db, user, campaign):
    agent = (
        db.query(AIAgent).filter(AIAgent.id == campaign.agent_id, AIAgent.user_id == user.id).first()
        if campaign.agent_id else None
    )
    if not agent or agent.status == 'disabled':
        agent = (
            db.query(AIAgent)
            .filter(AIAgent.user_id == user.id, AIAgent.is_default.is_(True))
            .first()
        )
    model = None
    if agent and agent.ai_model_id:
        model = db.query(AIModel).filter(AIModel.id == agent.ai_model_id, AIModel.user_id == user.id).first()
    if model is None and campaign.ai_model_id:
        model = db.query(AIModel).filter(AIModel.id == campaign.ai_model_id, AIModel.user_id == user.id).first()
    if model is None:
        model = db.query(AIModel).filter(AIModel.user_id == user.id, AIModel.is_default.is_(True)).first()
    return agent, model


def resolve_provider(db, user, campaign, agent, model):
    """Returns (provider, model_name, max_tokens, temperature)."""
    plan = _plan_of(db, user)
    if is_managed(model):
        if plan != 'pro':
            raise PermissionError('The managed default AI model requires a Pro plan')
        return AnthropicProvider(), MANAGED_MODEL_NAME, 1000, 0.7
    if model:
        api_key = decrypt_plaintext(model.api_key_encrypted)
        provider = provider_for(model, api_key=api_key)
        if provider is not None:
            return provider, model.model, model.max_tokens or 1000, model.temperature or 0.7
    if plan == 'pro':
        return AnthropicProvider(), MANAGED_MODEL_NAME, 1000, 0.7
    raise RuntimeError(
        'No AI model configured. Add your own API key (AI Models) or upgrade to Pro for the managed model.'
    )


def build_email_agent(db, user, campaign, agent, model):
    provider, model_name, max_tokens, temperature = resolve_provider(db, user, campaign, agent, model)
    return ColdEmailAgent(
        excel_path=None,
        ai_model=model_name,
        tone=campaign.tone,
        subject_style=campaign.subject_style,
        email_length=campaign.email_length,
        use_company_research=campaign.use_company_research,
        custom_prompt=campaign.custom_prompt or None,
        max_tokens=max_tokens,
        ai_provider=provider,
    )


def recipient_to_data(recipient):
    return {
        'email': recipient.email,
        'company_name': recipient.company_name,
        'industry': recipient.industry,
        'website': recipient.company_website,
        'job_role': recipient.job_role,
        'position_level': recipient.position_level,
        'linkedin_url': recipient.linkedin_url or '',
        'employee_count': recipient.employee_count or '',
        'funding_status': recipient.funding_status or '',
        'recent_news': recipient.recent_news or '',
        'contact_person_name': recipient.contact_person_name or '',
    }


def generate_campaign(campaign_id):
    with _generation_lock:
        _generate_campaign_impl(campaign_id)


def _generate_campaign_impl(campaign_id):
    from .database import SessionLocal as SL

    db = SL()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return
        user = db.query(User).filter(User.id == campaign.user_id).first()
        agent, model = load_agent_model(db, user, campaign)
        email_agent = build_email_agent(db, user, campaign, agent, model)

        rows = (
            db.query(GeneratedEmail)
            .filter(GeneratedEmail.campaign_id == campaign.id)
            .count()
        )
        if rows > 0:
            campaign.status = 'review_required' if campaign.review_required else 'scheduled'
            db.commit()
            return

        recipients = (
            db.query(Recipient)
            .join(CampaignRecipient, CampaignRecipient.recipient_id == Recipient.id)
            .filter(CampaignRecipient.campaign_id == campaign.id)
            .all()
        )
        account = None
        if campaign.email_account_id:
            account = (
                db.query(EmailAccount)
                .filter(EmailAccount.id == campaign.email_account_id, EmailAccount.user_id == user.id)
                .first()
            )
        sender_email = account.email if account else ''
        ai_provider = model.provider if model else 'managed'
        ai_model = model.model if model else MANAGED_MODEL_NAME
        ai_agent_id = agent.id if agent else None
        now = dt.datetime.now(dt.timezone.utc)
        for recipient in recipients:
            data = recipient_to_data(recipient)
            try:
                profile = email_agent.research_company(data)
                subject, body = email_agent.generate_personalized_email(data, profile)
            except Exception as exc:
                logger.warning('Generation failed for %s: %s', recipient.email, exc)
                subject, body = email_agent.generate_personalized_email(
                    data, {'company_pain_points': [], 'growth_stage': 'unknown', 'target_for_hiring': True, 'company_culture': '', 'key_keywords': []}
                )
                if not subject or not body:
                    subject, body = '', ''
            db.add(
                GeneratedEmail(
                    campaign_id=campaign.id,
                    recipient_id=recipient.id,
                    subject=subject or '',
                    body=body or '',
                    status='generated',
                )
            )
            db.add(
                EmailLog(
                    user_id=user.id,
                    campaign_id=campaign.id,
                    recipient_id=recipient.id,
                    email_account_id=account.id if account else None,
                    sender_email=sender_email,
                    recipient_email=recipient.email,
                    subject=subject or '',
                    body=body or '',
                    generated_subject=subject or '',
                    generated_body=body or '',
                    status='generated',
                    ai_agent_id=ai_agent_id,
                    ai_provider=ai_provider,
                    ai_model=ai_model,
                    execution_type='scheduled',
                    generated_at=now,
                )
            )
            db.add(UsageRecord(user_id=user.id, campaign_id=campaign.id, metric='ai_generation'))
        campaign.status = 'review_required' if campaign.review_required else 'scheduled'
        db.commit()
    except PermissionError as exc:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.status = 'failed'
            db.commit()
    except Exception as exc:
        logger.error('Campaign generation crashed: %s', exc)
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.status = 'failed'
            db.commit()
    finally:
        db.close()


def _email_log_for(db, campaign, generated_email):
    """Find the EmailLog snapshot for a generated email (create a stub if missing)."""
    log = (
        db.query(EmailLog)
        .filter(
            EmailLog.campaign_id == campaign.id,
            EmailLog.recipient_id == generated_email.recipient_id,
        )
        .order_by(EmailLog.id.desc())
        .first()
    )
    if log:
        return log
    recipient = db.query(Recipient).filter(Recipient.id == generated_email.recipient_id).first()
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.id == campaign.email_account_id, EmailAccount.user_id == campaign.user_id)
        .first()
    )
    now = dt.datetime.now(dt.timezone.utc)
    log = EmailLog(
        user_id=campaign.user_id,
        campaign_id=campaign.id,
        recipient_id=generated_email.recipient_id,
        email_account_id=account.id if account else None,
        sender_email=account.email if account else '',
        recipient_email=recipient.email if recipient else '',
        subject=generated_email.subject or '',
        body=generated_email.body or '',
        generated_subject=generated_email.subject or '',
        generated_body=generated_email.body or '',
        status='sending',
        execution_type='scheduled',
        generated_at=generated_email.generated_at or now,
    )
    db.add(log)
    db.flush()
    return log


def _classify_error(exc):
    message = str(exc)
    if isinstance(exc, smtplib.SMTPAuthenticationError) or 'authenticate' in message.lower():
        return 'AUTH_ERROR', message
    if 'token' in message.lower() or 'OAuth' in message:
        return 'AUTH_ERROR', message
    return 'SEND_ERROR', message


def send_generated_email(db, campaign, generated_email, execution_type='scheduled'):
    """Send one generated email via the campaign's email account.

    Moves the email through sending -> sent/failed and keeps the EmailLog snapshot
    in sync. Returns (status, error).
    """
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.id == campaign.email_account_id, EmailAccount.user_id == campaign.user_id)
        .first()
    )
    recipient = db.query(Recipient).filter(Recipient.id == generated_email.recipient_id).first()
    if not account:
        return ('failed', 'No sending account configured for this campaign')
    log = _email_log_for(db, campaign, generated_email)
    now = dt.datetime.now(dt.timezone.utc)
    generated_email.status = 'sending'
    log.status = 'sending'
    log.execution_type = execution_type
    log.sender_email = account.email
    log.recipient_email = recipient.email if recipient else generated_email.recipient_email
    db.flush()
    try:
        if account.provider == 'google':
            refresh_token = decrypt_plaintext(account.credentials_encrypted)
            if not refresh_token:
                raise RuntimeError('OAuth token missing — reconnect the account')
            gmail.send_via_gmail(
                refresh_token, account.email, generated_email.subject, generated_email.body, recipient.email
            )
        else:
            app_password = decrypt_plaintext(account.credentials_encrypted)
            if not app_password:
                raise RuntimeError('SMTP app password missing')
            _send_via_smtp(account, app_password, recipient.email, generated_email.subject, generated_email.body)
        generated_email.status = 'sent'
        generated_email.sent_at = now
        generated_email.error = ''
        generated_email.error_code = ''
        campaign.last_sent_at = now
        log.status = 'sent'
        log.subject = generated_email.subject or ''
        log.body = generated_email.body or ''
        log.sent_at = now
        log.failed_at = None
        log.error = ''
        log.error_code = ''
        db.add(UsageRecord(user_id=campaign.user_id, campaign_id=campaign.id, metric='email_sent'))
        return ('sent', '')
    except Exception as exc:
        error_code, message = _classify_error(exc)
        generated_email.status = 'failed'
        generated_email.error = message
        generated_email.error_code = error_code
        log.status = 'failed'
        log.subject = generated_email.subject or ''
        log.body = generated_email.body or ''
        log.failed_at = now
        log.error = message
        log.error_code = error_code
        return ('failed', message)


def retry_email_log(db, user, log):
    """Re-attempt a failed email from its snapshot. Bounded manual retry (no auto-loop)."""
    if log.user_id != user.id:
        raise PermissionError('Not your email')
    if log.status not in ('failed', 'cancelled'):
        raise RuntimeError('Only failed or cancelled emails can be retried')
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.id == log.email_account_id, EmailAccount.user_id == user.id)
        .first()
    )
    if not account:
        return ('failed', 'No sending account configured for this email')
    now = dt.datetime.now(dt.timezone.utc)
    try:
        if account.provider == 'google':
            refresh_token = decrypt_plaintext(account.credentials_encrypted)
            if not refresh_token:
                raise RuntimeError('OAuth token missing — reconnect the account')
            gmail.send_via_gmail(refresh_token, account.email, log.subject, log.body, log.recipient_email)
        else:
            app_password = decrypt_plaintext(account.credentials_encrypted)
            if not app_password:
                raise RuntimeError('SMTP app password missing')
            _send_via_smtp(account, app_password, log.recipient_email, log.subject, log.body)
        log.status = 'sent'
        log.sent_at = now
        log.failed_at = None
        log.error = ''
        log.error_code = ''
        if log.campaign_id:
            generated = (
                db.query(GeneratedEmail)
                .filter(GeneratedEmail.campaign_id == log.campaign_id, GeneratedEmail.recipient_id == log.recipient_id)
                .first()
            )
            if generated:
                generated.status = 'sent'
                generated.sent_at = now
                generated.error = ''
                generated.error_code = ''
            campaign = db.query(Campaign).filter(Campaign.id == log.campaign_id).first()
            if campaign:
                campaign.last_sent_at = now
        db.add(UsageRecord(user_id=user.id, campaign_id=log.campaign_id, metric='email_sent'))
        return ('sent', '')
    except Exception as exc:
        error_code, message = _classify_error(exc)
        log.status = 'failed'
        log.failed_at = now
        log.error = message
        log.error_code = error_code
        return ('failed', message)


def send_manual_email(db, user, account, recipient, subject, body, ai_provider='', ai_model=''):
    """Send a one-off manual email and record it in history. Returns (log, status, error)."""
    now = dt.datetime.now(dt.timezone.utc)
    log = EmailLog(
        user_id=user.id,
        recipient_id=recipient.id,
        email_account_id=account.id,
        sender_email=account.email,
        recipient_email=recipient.email,
        subject=subject or '',
        body=body or '',
        generated_subject=subject or '',
        generated_body=body or '',
        status='sending',
        execution_type='manual',
        ai_provider=ai_provider,
        ai_model=ai_model,
        generated_at=now,
        scheduled_at=now,
    )
    db.add(log)
    db.flush()
    try:
        if account.provider == 'google':
            refresh_token = decrypt_plaintext(account.credentials_encrypted)
            if not refresh_token:
                raise RuntimeError('OAuth token missing — reconnect the account')
            gmail.send_via_gmail(refresh_token, account.email, subject or '', body or '', recipient.email)
        else:
            app_password = decrypt_plaintext(account.credentials_encrypted)
            if not app_password:
                raise RuntimeError('SMTP app password missing')
            _send_via_smtp(account, app_password, recipient.email, subject or '', body or '')
        log.status = 'sent'
        log.sent_at = now
        db.add(UsageRecord(user_id=user.id, metric='email_sent'))
        return (log, 'sent', '')
    except Exception as exc:
        error_code, message = _classify_error(exc)
        log.status = 'failed'
        log.failed_at = now
        log.error = message
        log.error_code = error_code
        return (log, 'failed', message)


def schedule_campaign(db, campaign):
    """Mark queued emails as scheduled (launch)."""
    now = dt.datetime.now(dt.timezone.utc)
    queued = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status.in_(QUEUED_STATUSES))
        .all()
    )
    for item in queued:
        item.status = 'scheduled'
        item.scheduled_at = now
        log = _email_log_for(db, campaign, item)
        log.status = 'scheduled'
        log.scheduled_at = now
    db.flush()


def cancel_campaign(db, campaign):
    """Cancel a campaign: pending emails become cancelled, campaign stops."""
    pending = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status.in_(QUEUED_STATUSES))
        .all()
    )
    for item in pending:
        item.status = 'cancelled'
        log = _email_log_for(db, campaign, item)
        log.status = 'cancelled'
    campaign.status = 'cancelled'
    db.flush()


def _send_via_smtp(account, password, recipient, subject, body):
    message = MIMEText(body)
    message['From'] = account.email
    message['To'] = recipient
    message['Subject'] = subject
    host = account.smtp_host or 'smtp.gmail.com'
    port = account.smtp_port or 465
    secure = account.smtp_secure if account.smtp_secure is not None else True
    username = account.smtp_username or account.email
    if secure:
        with smtplib.SMTP_SSL(host, port) as smtp:
            smtp.login(username, password)
            smtp.sendmail(account.email, recipient, message.as_string())
    else:
        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(account.email, recipient, message.as_string())


def campaign_progress(db, campaign):
    total = db.query(GeneratedEmail).filter(GeneratedEmail.campaign_id == campaign.id).count()
    sent = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status == 'sent')
        .count()
    )
    failed = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status == 'failed')
        .count()
    )
    cancelled = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status == 'cancelled')
        .count()
    )
    pending = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status.in_(QUEUED_STATUSES))
        .count()
    )
    return {
        'total': total,
        'sent': sent,
        'failed': failed,
        'cancelled': cancelled,
        'pending': pending,
        'percent': round((sent + failed) / total * 100) if total else 0,
    }