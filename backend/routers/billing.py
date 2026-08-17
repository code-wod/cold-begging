import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import FREE_RATE_PER_HOUR, MAX_RATE_PER_HOUR
from ..database import get_db
from ..models import EmailLog, Subscription, UsageRecord, User
from ..schemas import SubscriptionOut, UsageOut
from ..security import get_current_user

router = APIRouter(prefix='/api/billing', tags=['billing'])

LIMITS = {
    'free': {
        'ai_generation': 100,
        'email_sent': 200,
        'emails_per_hour': FREE_RATE_PER_HOUR,
        'agents': 1,
        'campaigns': 3,
    },
    'pro': {
        'ai_generation': 5000,
        'email_sent': 10000,
        'emails_per_hour': MAX_RATE_PER_HOUR,
        'agents': 50,
        'campaigns': 500,
    },
}


def _get_subscription(db, user):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        sub = Subscription(user_id=user.id, plan='free', status='active')
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.get('', response_model=UsageOut)
def billing(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    ai = (
        db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
        .filter(UsageRecord.user_id == user.id, UsageRecord.metric == 'ai_generation')
        .scalar()
    )
    sent = (
        db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
        .filter(UsageRecord.user_id == user.id, UsageRecord.metric == 'email_sent')
        .scalar()
    )
    return UsageOut(
        ai_generation=int(ai),
        email_sent=int(sent),
        limits=LIMITS.get(sub.plan, LIMITS['free']),
    )


@router.get('/subscription', response_model=SubscriptionOut)
def subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    return SubscriptionOut(
        plan=sub.plan,
        status=sub.status,
        started_at=sub.started_at.isoformat() if sub.started_at else None,
        renews_at=sub.renews_at.isoformat() if sub.renews_at else None,
    )


@router.post('/upgrade')
def upgrade(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    sub.plan = 'pro'
    sub.status = 'active'
    sub.started_at = dt.datetime.now(dt.timezone.utc)
    sub.renews_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
    db.commit()
    return {'plan': 'pro'}


@router.post('/downgrade')
def downgrade(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    sub.plan = 'free'
    db.commit()
    return {'plan': 'free'}