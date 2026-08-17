import datetime as dt
import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import campaign_service
from ..database import get_db
from ..models import (
    AIAgent,
    AIModel,
    Campaign,
    CampaignRecipient,
    EmailAccount,
    EmailLog,
    GeneratedEmail,
    Recipient,
    User,
)
from ..schemas import GeneratedEmailOut, GeneratedEmailUpdate, ManualEmailIn
from ..security import get_current_user

router = APIRouter(prefix='/api', tags=['emails'])


def _out(db, ge):
    recipient = db.query(Recipient).filter(Recipient.id == ge.recipient_id).first()
    return GeneratedEmailOut(
        id=ge.id,
        campaign_id=ge.campaign_id,
        recipient_id=ge.recipient_id,
        recipient_email=recipient.email if recipient else '',
        recipient_name=recipient.contact_person_name or recipient.company_name if recipient else '',
        subject=ge.subject or '',
        body=ge.body or '',
        status=ge.status,
        error=ge.error or '',
        error_code=ge.error_code or '',
        generated_at=ge.generated_at.isoformat() if ge.generated_at else None,
        scheduled_at=ge.scheduled_at.isoformat() if ge.scheduled_at else None,
        sent_at=ge.sent_at.isoformat() if ge.sent_at else None,
    )


def _load_ge(db, user, email_id):
    ge = (
        db.query(GeneratedEmail)
        .join(Campaign, Campaign.id == GeneratedEmail.campaign_id)
        .filter(GeneratedEmail.id == email_id, Campaign.user_id == user.id)
        .first()
    )
    if not ge:
        raise HTTPException(status_code=404, detail='Email not found')
    return ge


@router.get('/campaigns/{campaign_id}/emails', response_model=list[GeneratedEmailOut])
def campaign_emails(
    campaign_id: int,
    status: str = '',
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    query = db.query(GeneratedEmail).filter(GeneratedEmail.campaign_id == campaign_id)
    if status:
        query = query.filter(GeneratedEmail.status == status)
    items = query.order_by(GeneratedEmail.id).all()
    return [_out(db, ge) for ge in items]


@router.get('/emails/history')
def email_history(
    campaign_id: int = 0,
    status: str = '',
    search: str = '',
    sender: str = '',
    agent_id: int = 0,
    date_from: str = '',
    date_to: str = '',
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EmailLog).filter(EmailLog.user_id == user.id)
    if campaign_id:
        query = query.filter(EmailLog.campaign_id == campaign_id)
    if status:
        query = query.filter(EmailLog.status == status)
    if sender:
        query = query.filter(EmailLog.sender_email.ilike(f'%{sender}%'))
    if agent_id:
        query = query.filter(EmailLog.ai_agent_id == agent_id)
    if search:
        query = query.filter(EmailLog.recipient_email.ilike(f'%{search}%'))
    if date_from:
        try:
            query = query.filter(EmailLog.created_at >= dt.datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(EmailLog.created_at <= dt.datetime.fromisoformat(date_to))
        except ValueError:
            pass
    total = query.count()
    items = query.order_by(EmailLog.created_at.desc()).offset(offset).limit(limit).all()
    campaigns = {c.id: c.name for c in db.query(Campaign).filter(Campaign.user_id == user.id).all()}
    result = [_history_item(log, campaigns.get(log.campaign_id, '')) for log in items]
    return {'total': total, 'items': result}


def _history_item(log, campaign_name=''):
    return {
        'id': log.id,
        'recipient': log.recipient_email or '',
        'recipient_email': log.recipient_email or '',
        'sender_email': log.sender_email or '',
        'email_account_id': log.email_account_id,
        'campaign_id': log.campaign_id,
        'campaign': campaign_name,
        'subject': log.subject or '',
        'body': log.body or '',
        'generated_subject': log.generated_subject or '',
        'generated_body': log.generated_body or '',
        'status': log.status,
        'error': log.error or '',
        'error_code': log.error_code or '',
        'ai_agent_id': log.ai_agent_id,
        'ai_provider': log.ai_provider or '',
        'ai_model': log.ai_model or '',
        'execution_type': log.execution_type or 'scheduled',
        'generated_at': log.generated_at.isoformat() if log.generated_at else None,
        'scheduled_at': log.scheduled_at.isoformat() if log.scheduled_at else None,
        'sent_at': log.sent_at.isoformat() if log.sent_at else None,
        'failed_at': log.failed_at.isoformat() if log.failed_at else None,
        'created_at': log.created_at.isoformat() if log.created_at else None,
    }


def _load_log(db, user, log_id):
    log = (
        db.query(EmailLog)
        .filter(EmailLog.id == log_id, EmailLog.user_id == user.id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail='Email not found')
    return log


@router.get('/emails/history/{log_id}')
def email_detail(log_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = _load_log(db, user, log_id)
    campaigns = {c.id: c.name for c in db.query(Campaign).filter(Campaign.user_id == user.id).all()}
    return _history_item(log, campaigns.get(log.campaign_id, ''))


@router.post('/emails/history/{log_id}/retry')
def retry_email(log_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = _load_log(db, user, log_id)
    if log.status not in ('failed', 'cancelled'):
        raise HTTPException(status_code=400, detail='Only failed or cancelled emails can be retried')
    status, error = campaign_service.retry_email_log(db, user, log)
    db.commit()
    return {'status': status, 'error': error, 'id': log.id}


@router.post('/emails/manual')
def send_manual_email(payload: ManualEmailIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipient = (
        db.query(Recipient).filter(Recipient.id == payload.recipient_id, Recipient.user_id == user.id).first()
    )
    if not recipient:
        raise HTTPException(status_code=400, detail='Invalid recipient')
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.id == payload.email_account_id, EmailAccount.user_id == user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=400, detail='Invalid sending account')
    if not payload.subject or not payload.body:
        raise HTTPException(status_code=400, detail='Subject and body are required')
    ai_provider = ai_model = ''
    if payload.ai_agent_id:
        agent = (
            db.query(AIAgent)
            .filter(AIAgent.id == payload.ai_agent_id, AIAgent.user_id == user.id)
            .first()
        )
        if agent and agent.ai_model_id:
            model = db.query(AIModel).filter(AIModel.id == agent.ai_model_id).first()
            ai_provider = model.provider if model else ''
            ai_model = model.model if model else ''
    log, status, error = campaign_service.send_manual_email(
        db, user, account, recipient, payload.subject, payload.body, ai_provider, ai_model
    )
    db.commit()
    campaigns = {c.id: c.name for c in db.query(Campaign).filter(Campaign.user_id == user.id).all()}
    return _history_item(log, campaigns.get(log.campaign_id, ''))


@router.get('/emails/{email_id}', response_model=GeneratedEmailOut)
def get_email(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(db, _load_ge(db, user, email_id))


@router.patch('/emails/{email_id}', response_model=GeneratedEmailOut)
def update_email(
    email_id: int,
    payload: GeneratedEmailUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ge = _load_ge(db, user, email_id)
    if ge.status in ('sent',):
        raise HTTPException(status_code=400, detail='This email has already been sent')
    if payload.subject is not None:
        ge.subject = payload.subject
    if payload.body is not None:
        ge.body = payload.body
    if payload.status is not None:
        ge.status = payload.status
    log = (
        db.query(EmailLog)
        .filter(EmailLog.campaign_id == ge.campaign_id, EmailLog.recipient_id == ge.recipient_id)
        .order_by(EmailLog.id.desc())
        .first()
    )
    if log:
        log.subject = ge.subject
        log.body = ge.body
    db.commit()
    db.refresh(ge)
    return _out(db, ge)


@router.post('/emails/{email_id}/approve', response_model=GeneratedEmailOut)
def approve_email(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ge = _load_ge(db, user, email_id)
    ge.status = 'approved'
    db.commit()
    db.refresh(ge)
    return _out(db, ge)


@router.post('/campaigns/{campaign_id}/approve-all')
def approve_all(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = (
        db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    db.query(GeneratedEmail).filter(
        GeneratedEmail.campaign_id == campaign_id, GeneratedEmail.status == 'generated'
    ).update({'status': 'approved'}, synchronize_session=False)
    db.commit()
    return {'ok': True}


def _regenerate(db, user, ge):
    campaign = db.query(Campaign).filter(Campaign.id == ge.campaign_id).first()
    agent, model = campaign_service.load_agent_model(db, user, campaign)
    email_agent = campaign_service.build_email_agent(db, user, campaign, agent, model)
    recipient = db.query(Recipient).filter(Recipient.id == ge.recipient_id).first()
    data = campaign_service.recipient_to_data(recipient)
    profile = email_agent.research_company(data)
    subject, body = email_agent.generate_personalized_email(data, profile)
    ge.subject = subject
    ge.body = body
    ge.status = 'generated'
    log = (
        db.query(EmailLog)
        .filter(EmailLog.campaign_id == ge.campaign_id, EmailLog.recipient_id == ge.recipient_id)
        .order_by(EmailLog.id.desc())
        .first()
    )
    if log:
        log.subject = subject
        log.body = body
        log.generated_subject = subject
        log.generated_body = body
        log.status = 'generated'
    return ge


@router.post('/emails/{email_id}/regenerate', response_model=GeneratedEmailOut)
def regenerate_email(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ge = _load_ge(db, user, email_id)
    _regenerate(db, user, ge)
    db.commit()
    db.refresh(ge)
    return _out(db, ge)


@router.post('/emails/{email_id}/send')
def send_email(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ge = _load_ge(db, user, email_id)
    campaign = db.query(Campaign).filter(Campaign.id == ge.campaign_id).first()
    if campaign.dry_run:
        return {'status': 'skipped', 'dry_run': True, 'message': 'Dry run mode — no email was sent'}
    if ge.status == 'sent':
        raise HTTPException(status_code=400, detail='Already sent')
    status, error = campaign_service.send_generated_email(db, campaign, ge)
    db.commit()
    return {'status': status, 'error': error}


@router.post('/campaigns/{campaign_id}/send-pending')
def send_pending(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = (
        db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    if campaign.dry_run:
        return {'sent': 0, 'dry_run': True, 'message': 'Dry run mode — nothing was sent'}
    emails = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.campaign_id == campaign_id,
            GeneratedEmail.status.in_(['generated', 'approved']),
        )
        .order_by(GeneratedEmail.id)
        .all()
    )
    sent = 0
    for ge in emails:
        status, _ = campaign_service.send_generated_email(db, campaign, ge)
        if status == 'sent':
            sent += 1
    db.commit()
    return {'sent': sent, 'total': len(emails)}

