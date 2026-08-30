import datetime as dt

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), default='')
    avatar_url = Column(String(1024), default='')
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    phone = Column(String(64), default='')  # phone number


class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)
    bio = Column(Text, default='')
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EmailAccount(Base):
    __tablename__ = 'email_accounts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    provider = Column(String(32), default='google')  # google | smtp
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), default='')
    credentials_encrypted = Column(Text)  # encrypted refresh token / app password
    smtp_host = Column(String(255), default='smtp.gmail.com')
    smtp_port = Column(Integer, default=465)
    smtp_secure = Column(Boolean, default=True)
    smtp_username = Column(String(255), default='')
    is_default = Column(Boolean, default=False)
    status = Column(String(32), default='connected')
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'email', name='uq_email_account_user_email'),)


class RecipientGroup(Base):
    """A user-owned bucket of recipients (e.g. 'Startup Leads').

    Every recipient belongs to exactly one group owned by the same user.
    Group names are unique per user.""" 

    __tablename__ = 'recipient_groups'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    recipients = relationship('Recipient', back_populates='group', cascade='all, delete-orphan')

    __table_args__ = (UniqueConstraint('user_id', 'name', name='uq_recipient_group_user_name'),)


class Recipient(Base):
    __tablename__ = 'recipients'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    group_id = Column(Integer, ForeignKey('recipient_groups.id'), index=True, nullable=False)
    email = Column(String(255), nullable=False)
    company_name = Column(String(255), default='')
    industry = Column(String(255), default='')
    company_website = Column(String(1024), default='')
    job_role = Column(String(255), default='')
    position_level = Column(String(255), default='')
    linkedin_url = Column(String(1024), default='')
    employee_count = Column(String(64), default='')
    funding_status = Column(String(255), default='')
    recent_news = Column(Text, default='')
    contact_person_name = Column(String(255), default='')
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    group = relationship('RecipientGroup', back_populates='recipients')

    __table_args__ = (
        UniqueConstraint('user_id', 'email', name='uq_recipient_user_email'),
        Index('ix_recipient_user_group', 'user_id', 'group_id'),
    )


class AIModel(Base):
    __tablename__ = 'ai_models'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    provider = Column(String(32), nullable=False)  # openai | anthropic | managed
    model = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text)
    base_url = Column(String(1024), default='')
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    is_default = Column(Boolean, default=False)
    is_platform = Column(Boolean, default=False)  # admin-managed, shared model (platform credentials)
    price_usd = Column(Float, default=0)  # 0 = free for all users; >0 = Pro-only platform model
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AIAgent(Base):
    __tablename__ = 'ai_agents'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    purpose = Column(Text, default='')
    ai_model_id = Column(Integer, ForeignKey('ai_models.id'))
    system_prompt = Column(Text, default='')
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    status = Column(String(32), default='active')  # active | disabled
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


campaign_assets = Table(
    'campaign_assets',
    Base.metadata,
    Column('campaign_id', Integer, ForeignKey('campaigns.id'), primary_key=True),
    Column('asset_id', Integer, ForeignKey('user_profile_assets.id'), primary_key=True),
)


class UserProfileAsset(Base):
    """A personal profile asset: a resume PDF, resume link, or social/website URL.

    asset_type: resume | resume_link | github | linkedin | website
    Resumes (PDF or link) are the compulsory input for campaign personalization
    and count toward the per-user resume cap (free = 5, Pro higher).
    """

    __tablename__ = 'user_profile_assets'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    asset_type = Column(String(32), nullable=False)
    title = Column(String(255), default='')  # display label, e.g. 'Product resume' or 'GitHub'
    url = Column(String(1024), default='')  # for resume_link/github/linkedin/website
    filename = Column(String(255), default='')  # original PDF filename
    stored_path = Column(String(1024), default='')  # server path under uploads/
    text_content = Column(Text, default='')  # extracted PDF text, used as sender context
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    agent_id = Column(Integer, ForeignKey('ai_agents.id'))
    email_account_id = Column(Integer, ForeignKey('email_accounts.id'))
    ai_model_id = Column(Integer, ForeignKey('ai_models.id'))
    status = Column(String(32), default='draft')
    review_required = Column(Boolean, default=True)
    dry_run = Column(Boolean, default=True)
    use_company_research = Column(Boolean, default=True)
    custom_prompt = Column(Text, default='')
    tone = Column(String(32), default='professional')
    subject_style = Column(String(32), default='personalized')
    email_length = Column(String(32), default='medium')
    start_at = Column(DateTime(timezone=True))
    end_at = Column(DateTime(timezone=True))
    send_start_time = Column(String(16), default='09:00')
    send_end_time = Column(String(16), default='17:00')
    active_days = Column(Text, default='[1,2,3,4,5]')  # JSON list of weekday ints (0=Mon)
    emails_per_hour = Column(Integer, default=10)  # 4–50; free plan capped at 10
    delay_seconds = Column(Integer, default=0)  # legacy fixed delay; unused when emails_per_hour set
    daily_limit = Column(Integer, default=0)  # optional extra safety cap; 0 = no additional cap
    max_sends = Column(Integer, default=0)  # total sends per campaign; 0 = unlimited. Auto-stops when reached
    timezone = Column(String(64), default='UTC')
    last_sent_at = Column(DateTime(timezone=True))
    assets = relationship('UserProfileAsset', secondary=campaign_assets, lazy='selectin')
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CampaignRecipient(Base):
    __tablename__ = 'campaign_recipients'

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), index=True, nullable=False)
    recipient_id = Column(Integer, ForeignKey('recipients.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint('campaign_id', 'recipient_id', name='uq_campaign_recipient'),)


class GeneratedEmail(Base):
    __tablename__ = 'generated_emails'

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), index=True, nullable=False)
    recipient_id = Column(Integer, ForeignKey('recipients.id'), nullable=False)
    subject = Column(Text, default='')
    body = Column(Text, default='')
    status = Column(String(32), default='generated')  # generated | approved | scheduled | sending | sent | failed | cancelled | skipped
    error = Column(Text, default='')
    error_code = Column(String(64), default='')
    generated_at = Column(DateTime(timezone=True), default=utcnow)
    approved_at = Column(DateTime(timezone=True))
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint('campaign_id', 'recipient_id', name='uq_campaign_recipient_email'),)


class EmailLog(Base):
    """Append-only history/snapshot of every email that flowed through the system.

    Status mirrors the email lifecycle: generated | scheduled | sending | sent | failed | cancelled.
    Final content lives in `subject`/`body`; the original AI output is preserved in
    `generated_subject`/`generated_body` for comparison.
    """

    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    recipient_id = Column(Integer, ForeignKey('recipients.id'))
    email_account_id = Column(Integer, ForeignKey('email_accounts.id'))
    sender_email = Column(String(320), default='')
    recipient_email = Column(String(320), default='')
    subject = Column(Text, default='')  # final subject (edited version actually sent)
    body = Column(Text, default='')  # final body actually sent
    generated_subject = Column(Text, default='')
    generated_body = Column(Text, default='')
    status = Column(String(32), default='generated')  # generated | scheduled | sending | sent | failed | cancelled
    error = Column(Text, default='')
    error_code = Column(String(64), default='')
    ai_agent_id = Column(Integer, ForeignKey('ai_agents.id'))
    ai_provider = Column(String(32), default='')
    ai_model = Column(String(128), default='')
    execution_type = Column(String(32), default='scheduled')  # scheduled | manual
    generated_at = Column(DateTime(timezone=True))
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    plan = Column(String(32), default='free')  # free | pro
    status = Column(String(32), default='active')  # active | canceled | past_due
    started_at = Column(DateTime(timezone=True), default=utcnow)
    renews_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UsageRecord(Base):
    __tablename__ = 'usage_records'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    metric = Column(String(64), nullable=False)  # ai_generation | email_sent
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class PasswordReset(Base):
    __tablename__ = 'password_resets'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class EmailVerification(Base):
    __tablename__ = 'email_verifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)