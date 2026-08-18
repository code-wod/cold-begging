import datetime as dt
import json
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
    GeneratedEmail,
    Recipient,
    User,
    UserProfileAsset,
    campaign_assets,
)
from ..schemas import CampaignIn, CampaignOut, CampaignUpdate
from ..security import get_current_user

router = APIRouter(prefix='/api/campaigns', tags=['campaigns'])


def _serialize(db, campaign):
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
    pending = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.campaign_id == campaign.id,
            GeneratedEmail.status.in_(['generated', 'approved', 'scheduled', 'sending']),
        )
        .count()
    )
    cancelled = (
        db.query(GeneratedEmail)
        .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status == 'cancelled')
        .count()
    )
    recipient_count = (
        db.query(CampaignRecipient)
        .filter(CampaignRecipient.campaign_id == campaign.id)
        .count()
    )
    return CampaignOut(
        id=campaign.id,
        name=campaign.name,
        agent_id=campaign.agent_id,
        email_account_id=campaign.email_account_id,
        status=campaign.status,
        review_required=campaign.review_required,
        dry_run=campaign.dry_run,
        use_company_research=campaign.use_company_research,
        custom_prompt=campaign.custom_prompt or '',
        tone=campaign.tone,
        subject_style=campaign.subject_style,
        email_length=campaign.email_length,
        send_start_time=campaign.send_start_time,
        send_end_time=campaign.send_end_time,
        active_days=json.loads(campaign.active_days or '[]'),
        emails_per_hour=campaign.emails_per_hour,
        delay_seconds=campaign.delay_seconds,
        daily_limit=campaign.daily_limit,
        max_sends=campaign.max_sends,
        start_at=campaign.start_at.isoformat() if campaign.start_at else None,
        end_at=campaign.end_at.isoformat() if campaign.end_at else None,
        recipient_count=recipient_count,
        generated_count=total,
        sent_count=sent,
        failed_count=failed,
        pending_count=pending,
        cancelled_count=cancelled,
        asset_ids=[a.id for a in campaign.assets],
        created_at=campaign.created_at.isoformat() if campaign.created_at else None,
    )


def _load(db, user, campaign_id):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail='Campaign not found')
    return campaign


def _validate_account(db, user, account_id):
    account = (
        db.query(EmailAccount)
        .filter(EmailAccount.id == account_id, EmailAccount.user_id == user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=400, detail='Invalid sending account')
    return account


def _plan_of(db, user):
    return campaign_service._plan_of(db, user)


def _resolve_assets(db, user, asset_ids):
    """Load the user's own assets for the given ids, enforcing at least one resume."""
    asset_ids = list(asset_ids or [])
    assets = (
        db.query(UserProfileAsset)
        .filter(
            UserProfileAsset.id.in_(asset_ids) if asset_ids else False,
            UserProfileAsset.user_id == user.id,
        )
        .all()
    )
    if len(assets) != len(set(asset_ids)):
        raise HTTPException(status_code=400, detail='Invalid profile asset')
    if not any(a.asset_type in ('resume', 'resume_link') for a in assets):
        raise HTTPException(
            status_code=400,
            detail='Attach at least one resume (PDF or link) to the campaign',
        )
    return assets


@router.post('', response_model=CampaignOut)
def create_campaign(payload: CampaignIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account_id = payload.email_account_id
    if account_id:
        _validate_account(db, user, account_id)
    else:
        default_account = (
            db.query(EmailAccount)
            .filter(EmailAccount.user_id == user.id, EmailAccount.is_default.is_(True))
            .first()
        )
        if default_account:
            account_id = default_account.id
    if payload.agent_id:
        agent = (
            db.query(AIAgent)
            .filter(AIAgent.id == payload.agent_id, AIAgent.user_id == user.id)
            .first()
        )
        if not agent:
            raise HTTPException(status_code=400, detail='Invalid AI agent')
    rate_error = campaign_service.validate_rate(_plan_of(db, user), payload.emails_per_hour)
    if rate_error:
        raise HTTPException(status_code=403, detail=rate_error)
    assets = _resolve_assets(db, user, payload.asset_ids)
    campaign = Campaign(
        user_id=user.id,
        name=payload.name,
        agent_id=payload.agent_id,
        email_account_id=account_id,
        ai_model_id=payload.ai_model_id,
        assets=assets,
        status='draft',
        review_required=payload.review_required,
        dry_run=payload.dry_run,
        use_company_research=payload.use_company_research,
        custom_prompt=payload.custom_prompt,
        tone=payload.tone,
        subject_style=payload.subject_style,
        email_length=payload.email_length,
        start_at=_parse_dt(payload.start_at),
        end_at=_parse_dt(payload.end_at),
        send_start_time=payload.send_start_time,
        send_end_time=payload.send_end_time,
        active_days=json.dumps(payload.active_days or [1, 2, 3, 4, 5]),
        emails_per_hour=payload.emails_per_hour,
        delay_seconds=payload.delay_seconds,
        daily_limit=payload.daily_limit,
        max_sends=payload.max_sends,
        timezone=payload.timezone,
    )
    db.add(campaign)
    db.flush()
    for recipient_id in payload.recipient_ids or []:
        recipient = (
            db.query(Recipient)
            .filter(Recipient.id == recipient_id, Recipient.user_id == user.id)
            .first()
        )
        if recipient:
            db.add(CampaignRecipient(campaign_id=campaign.id, recipient_id=recipient.id))
    db.commit()
    db.refresh(campaign)
    return _serialize(db, campaign)


def _parse_dt(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


@router.get('', response_model=list[CampaignOut])
def list_campaigns(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.user_id == user.id)
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return [_serialize(db, c) for c in campaigns]


@router.get('/{campaign_id}', response_model=CampaignOut)
def get_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize(db, _load(db, user, campaign_id))


@router.patch('/{campaign_id}', response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = _load(db, user, campaign_id)
    if payload.emails_per_hour is not None:
        rate_error = campaign_service.validate_rate(_plan_of(db, user), payload.emails_per_hour)
        if rate_error:
            raise HTTPException(status_code=403, detail=rate_error)
    data = payload.dict(exclude_none=True)
    if 'asset_ids' in data:
        campaign.assets = _resolve_assets(db, user, data.pop('asset_ids'))
    for field, value in data.items():
        if field == 'active_days':
            value = json.dumps(value)
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return _serialize(db, campaign)


@router.post('/{campaign_id}/generate')
def generate_campaign(
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = _load(db, user, campaign_id)
    if campaign.status in ('generating', 'running', 'scheduled'):
        raise HTTPException(status_code=400, detail=f'Campaign is already {campaign.status}')
    if campaign.email_account_id is None:
        raise HTTPException(status_code=400, detail='Select a sending account before generating')
    campaign.status = 'generating'
    db.commit()
    thread = threading.Thread(target=campaign_service.generate_campaign, args=(campaign.id,), daemon=True)
    thread.start()
    return {'status': 'generating'}


@router.post('/{campaign_id}/test')
def test_campaign(
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = _load(db, user, campaign_id)
    campaign.status = 'generating'
    campaign.dry_run = True
    db.commit()
    thread = threading.Thread(target=campaign_service.generate_campaign, args=(campaign.id,), daemon=True)
    thread.start()
    return {'status': 'generating', 'dry_run': True}


@router.post('/{campaign_id}/launch')
def launch_campaign(
    campaign_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = _load(db, user, campaign_id)
    if campaign.email_account_id is None:
        raise HTTPException(status_code=400, detail='Select a sending account')
    if campaign.status != 'review_required':
        raise HTTPException(status_code=400, detail='Campaign must be in review before launching')
    pending = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.campaign_id == campaign.id,
            GeneratedEmail.status.in_(['generated', 'approved']),
        )
        .count()
    )
    if campaign.review_required and pending:
        approved = (
            db.query(GeneratedEmail)
            .filter(GeneratedEmail.campaign_id == campaign.id, GeneratedEmail.status == 'approved')
            .count()
        )
        if approved == 0:
            raise HTTPException(status_code=400, detail='Approve at least one email before launching')
    campaign_service.schedule_campaign(db, campaign)
    campaign.status = 'scheduled'
    db.commit()
    return _serialize(db, campaign)


@router.post('/{campaign_id}/pause')
def pause_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = _load(db, user, campaign_id)
    if campaign.status in ('scheduled', 'running'):
        campaign.status = 'paused'
        db.commit()
    return _serialize(db, campaign)


@router.post('/{campaign_id}/resume')
def resume_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = _load(db, user, campaign_id)
    if campaign.status == 'paused':
        campaign.status = 'scheduled'
        db.commit()
    return _serialize(db, campaign)


@router.post('/{campaign_id}/cancel')
def cancel_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = _load(db, user, campaign_id)
    if campaign.status in ('scheduled', 'running', 'paused', 'review_required'):
        campaign_service.cancel_campaign(db, campaign)
        db.commit()
    return _serialize(db, campaign)


@router.post('/{campaign_id}/duplicate', response_model=CampaignOut)
def duplicate_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    source = _load(db, user, campaign_id)
    copy = Campaign(
        user_id=user.id,
        name=f'{source.name} (copy)',
        agent_id=source.agent_id,
        email_account_id=source.email_account_id,
        ai_model_id=source.ai_model_id,
        status='draft',
        review_required=source.review_required,
        dry_run=True,
        use_company_research=source.use_company_research,
        custom_prompt=source.custom_prompt,
        tone=source.tone,
        subject_style=source.subject_style,
        email_length=source.email_length,
        send_start_time=source.send_start_time,
        send_end_time=source.send_end_time,
        active_days=source.active_days,
        emails_per_hour=source.emails_per_hour,
        delay_seconds=source.delay_seconds,
        daily_limit=source.daily_limit,
        max_sends=source.max_sends,
        timezone=source.timezone,
        assets=list(source.assets),
    )
    db.add(copy)
    db.flush()
    for cr in db.query(CampaignRecipient).filter(CampaignRecipient.campaign_id == source.id).all():
        db.add(CampaignRecipient(campaign_id=copy.id, recipient_id=cr.recipient_id))
    db.commit()
    db.refresh(copy)
    return _serialize(db, copy)


@router.delete('/{campaign_id}')
def delete_campaign(campaign_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _load(db, user, campaign_id)
    # Core deletes only (no ORM delete of the parent): guaranteed to remove every
    # campaign_assets row, including ones the ORM collection doesn't know about.
    db.execute(campaign_assets.delete().where(campaign_assets.c.campaign_id == campaign_id))
    db.query(GeneratedEmail).filter(GeneratedEmail.campaign_id == campaign_id).delete(synchronize_session=False)
    db.query(CampaignRecipient).filter(CampaignRecipient.campaign_id == campaign_id).delete(synchronize_session=False)
    db.query(Campaign).filter(Campaign.id == campaign_id).delete(synchronize_session=False)
    db.commit()
    return {'ok': True}