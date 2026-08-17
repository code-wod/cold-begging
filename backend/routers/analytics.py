import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Campaign, EmailLog, Recipient, User
from ..schemas import AnalyticsOut
from ..security import get_current_user

router = APIRouter(prefix='/api/analytics', tags=['analytics'])


@router.get('', response_model=AnalyticsOut)
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sent = db.query(EmailLog).filter(EmailLog.user_id == user.id, EmailLog.status == 'sent').count()
    failed = (
        db.query(EmailLog).filter(EmailLog.user_id == user.id, EmailLog.status == 'failed').count()
    )
    scheduled = (
        db.query(EmailLog).filter(EmailLog.user_id == user.id, EmailLog.status == 'scheduled').count()
    )
    cancelled = (
        db.query(EmailLog).filter(EmailLog.user_id == user.id, EmailLog.status == 'cancelled').count()
    )
    generated = (
        db.query(EmailLog).filter(EmailLog.user_id == user.id, EmailLog.status == 'generated').count()
    )
    campaigns = db.query(Campaign).filter(Campaign.user_id == user.id).count()
    recipients = db.query(Recipient).filter(Recipient.user_id == user.id).count()

    delivered = sent
    delivery_rate = round(delivered / (sent + failed) * 100, 1) if (sent + failed) else 0.0

    today = dt.date.today()
    daily = []
    for i in range(13, -1, -1):
        day = today - dt.timedelta(days=i)
        start = dt.datetime.combine(day, dt.time.min).replace(tzinfo=dt.timezone.utc)
        end = dt.datetime.combine(day, dt.time.max).replace(tzinfo=dt.timezone.utc)
        count = (
            db.query(EmailLog)
            .filter(EmailLog.user_id == user.id, EmailLog.sent_at >= start, EmailLog.sent_at <= end)
            .count()
        )
        daily.append({'date': day.isoformat(), 'sent': count})

    return AnalyticsOut(
        emails_generated=generated,
        emails_scheduled=scheduled,
        emails_sent=sent,
        emails_failed=failed,
        emails_cancelled=cancelled,
        delivery_rate=delivery_rate,
        open_rate=None,
        reply_rate=None,
        campaigns=campaigns,
        recipients=recipients,
        daily=daily,
    )