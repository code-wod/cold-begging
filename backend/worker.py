import datetime as dt
import json
import logging
import threading
from zoneinfo import ZoneInfo

from . import campaign_service
from .config import FREE_RATE_PER_HOUR
from .database import SessionLocal
from .models import Campaign, EmailLog, GeneratedEmail, Subscription

logger = logging.getLogger('cold_email_agent')


class CampaignWorker(threading.Thread):
    """Background scheduler: sends due scheduled emails without blocking HTTP requests.

    Kept in-process (no Redis) so the app runs anywhere; swap for Celery + Redis
    by replacing `run()` with the equivalent task dispatch.
    """

    def __init__(self, poll_interval=15):
        super().__init__(daemon=True)
        self.poll_interval = poll_interval
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                self._process_due()
            except Exception as exc:
                logger.error('Worker error: %s', exc)
            self._stop.wait(self.poll_interval)

    def _process_due(self):
        db = SessionLocal()
        try:
            campaigns = (
                db.query(Campaign)
                .filter(Campaign.status.in_(['scheduled', 'running']))
                .all()
            )
            for campaign in campaigns:
                try:
                    self._process_campaign(db, campaign)
                except Exception as exc:
                    logger.error('Campaign %s worker error: %s', campaign.id, exc)
            db.commit()
        finally:
            db.close()

    _TZ_ALIASES = {
        'IST': 'Asia/Kolkata',
        'EST': 'America/New_York',
        'EDT': 'America/New_York',
        'CST': 'America/Chicago',
        'CDT': 'America/Chicago',
        'MST': 'America/Denver',
        'MDT': 'America/Denver',
        'PST': 'America/Los_Angeles',
        'PDT': 'America/Los_Angeles',
        'GMT': 'UTC',
    }

    def _zone_for(self, name):
        name = (name or 'UTC').strip()
        name = self._TZ_ALIASES.get(name.upper(), name)
        try:
            return ZoneInfo(name)
        except Exception:
            return dt.timezone.utc

    def _naive_utc(self, value):
        # SQLite returns naive datetimes (tzinfo lost); Postgres returns aware.
        # Normalize both to naive UTC so comparisons are backend-agnostic.
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return value

    def _local_now(self, campaign):
        try:
            return dt.datetime.now(dt.timezone.utc).astimezone(self._zone_for(campaign.timezone))
        except Exception:
            return dt.datetime.now(dt.timezone.utc)

    def _process_campaign(self, db, campaign):
        now_utc = dt.datetime.now(dt.timezone.utc)
        now_naive_utc = now_utc.replace(tzinfo=None)  # SQLite returns naive datetimes for all tz columns
        local = self._local_now(campaign)
        if campaign.start_at and self._naive_utc(campaign.start_at) > now_naive_utc:
            return
        if campaign.end_at and self._naive_utc(campaign.end_at) < now_naive_utc:
            campaign.status = 'completed'
            return
        if not self._in_schedule(campaign, local):
            return

        # Defense in depth: clamp the rate to the user's plan (backend also validates on save).
        sub = db.query(Subscription).filter(Subscription.user_id == campaign.user_id).first()
        plan = sub.plan if sub else 'free'
        rate = campaign.emails_per_hour or 0
        if plan != 'pro' and rate > FREE_RATE_PER_HOUR:
            rate = FREE_RATE_PER_HOUR
        interval = campaign_service.rate_interval_seconds(campaign)

        # Daily safety cap (0 = unlimited) — secondary to the hourly rate.
        if campaign.daily_limit:
            day_start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
            day_start_utc = day_start_local.astimezone(dt.timezone.utc).replace(tzinfo=None)
            sent_today = (
                db.query(EmailLog)
                .filter(
                    EmailLog.campaign_id == campaign.id,
                    EmailLog.status == 'sent',
                    EmailLog.sent_at >= day_start_utc,
                )
                .count()
            )
            if sent_today >= campaign.daily_limit:
                return

        # Hourly rate enforcement: never exceed emails_per_hour in the last rolling hour.
        if rate > 0:
            hour_ago = now_naive_utc - dt.timedelta(hours=1)
            sent_in_hour = (
                db.query(EmailLog)
                .filter(
                    EmailLog.campaign_id == campaign.id,
                    EmailLog.status == 'sent',
                    EmailLog.sent_at >= hour_ago,
                )
                .count()
            )
            if sent_in_hour >= rate:
                return

        # Auto-stop: if the campaign has a total-send cap, stop once it is reached.
        if campaign.max_sends and campaign.max_sends > 0:
            sent_total = (
                db.query(GeneratedEmail)
                .filter(
                    GeneratedEmail.campaign_id == campaign.id,
                    GeneratedEmail.status == 'sent',
                )
                .count()
            )
            if sent_total >= campaign.max_sends:
                campaign.status = 'completed'
                return

        # Space sends by the rate-derived interval.
        if campaign.last_sent_at:
            elapsed = (now_naive_utc - self._naive_utc(campaign.last_sent_at)).total_seconds()
            if interval and elapsed < interval:
                return

        next_email = (
            db.query(GeneratedEmail)
            .filter(
                GeneratedEmail.campaign_id == campaign.id,
                GeneratedEmail.status.in_(['generated', 'approved', 'scheduled']),
            )
            .order_by(GeneratedEmail.id)
            .first()
        )
        if not next_email:
            total = (
                db.query(GeneratedEmail)
                .filter(GeneratedEmail.campaign_id == campaign.id)
                .count()
            )
            sent = (
                db.query(GeneratedEmail)
                .filter(
                    GeneratedEmail.campaign_id == campaign.id,
                    GeneratedEmail.status == 'sent',
                )
                .count()
            )
            if total and sent == total:
                campaign.status = 'completed'
            return

        if campaign.dry_run:
            return  # dry-run campaigns generate but never send

        status, error = campaign_service.send_generated_email(db, campaign, next_email)
        if status == 'failed':
            logger.warning('Send failed for campaign %s: %s', campaign.id, error)
        if campaign.max_sends and campaign.max_sends > 0:
            sent_total = (
                db.query(GeneratedEmail)
                .filter(
                    GeneratedEmail.campaign_id == campaign.id,
                    GeneratedEmail.status == 'sent',
                )
                .count()
            )
            if sent_total >= campaign.max_sends:
                campaign.status = 'completed'
                return
        campaign.status = 'running'

    def _in_schedule(self, campaign, local):
        try:
            active_days = json.loads(campaign.active_days or '[]')
        except ValueError:
            active_days = []
        if active_days and local.weekday() not in active_days:
            return False
        try:
            sh, sm = map(int, campaign.send_start_time.split(':'))
            eh, em = map(int, campaign.send_end_time.split(':'))
        except (ValueError, AttributeError):
            return True
        current = local.hour * 60 + local.minute
        start = sh * 60 + sm
        end = eh * 60 + em
        if start <= end:
            return start <= current < end
        return current >= start or current < end