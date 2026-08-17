from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ''


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResetRequest(BaseModel):
    email: EmailStr


class ResetConfirmRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    avatar_url: str
    is_verified: bool
    plan: str = 'free'
    created_at: Optional[str] = None



class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserOut


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


# ---------- Recipients ----------
class RecipientIn(BaseModel):
    email: EmailStr
    company_name: str = ''
    industry: str = ''
    company_website: str = ''
    job_role: str = ''
    position_level: str = ''
    linkedin_url: str = ''
    employee_count: str = ''
    funding_status: str = ''
    recent_news: str = ''
    contact_person_name: str = ''


class RecipientOut(BaseModel):
    id: int
    email: str
    company_name: str
    industry: str
    company_website: str
    job_role: str
    position_level: str
    created_at: Optional[str] = None



class ImportResult(BaseModel):
    added: int
    duplicates: int
    invalid: int
    total: int


# ---------- AI models & agents ----------
class AIModelIn(BaseModel):
    name: str
    provider: str
    model: str
    api_key: str = ''
    base_url: str = ''
    temperature: float = 0.7
    max_tokens: int = 1000
    is_default: bool = False


class AIModelOut(BaseModel):
    id: int
    name: str
    provider: str
    model: str
    base_url: str
    temperature: float
    max_tokens: int
    is_default: bool
    has_api_key: bool = False
    created_at: Optional[str] = None



class AIAgentIn(BaseModel):
    name: str
    description: str = ''
    purpose: str = ''
    ai_model_id: Optional[int] = None
    system_prompt: str = ''
    temperature: float = 0.7
    max_tokens: int = 1000
    status: str = 'active'


class AIAgentOut(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    ai_model_id: Optional[int]
    model_name: str = ''
    system_prompt: str
    temperature: float
    max_tokens: int
    status: str
    is_default: bool = False
    created_at: Optional[str] = None



# ---------- Email accounts ----------
class EmailAccountIn(BaseModel):
    provider: str = 'smtp'
    email: str
    display_name: str = ''
    app_password: str = ''
    smtp_host: str = 'smtp.gmail.com'
    smtp_port: int = 465
    smtp_secure: bool = True
    smtp_username: str = ''
    is_default: bool = False


class EmailAccountUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    app_password: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_secure: Optional[bool] = None
    smtp_username: Optional[str] = None
    is_default: Optional[bool] = None


class EmailAccountOut(BaseModel):
    id: int
    provider: str
    email: str
    display_name: str
    smtp_host: str = ''
    smtp_port: int = 0
    smtp_secure: bool = True
    smtp_username: str = ''
    is_default: bool = False
    status: str
    created_at: Optional[str] = None



# ---------- Campaigns ----------
class CampaignIn(BaseModel):
    name: str
    agent_id: Optional[int] = None
    email_account_id: Optional[int] = None
    ai_model_id: Optional[int] = None
    recipient_ids: Optional[List[int]] = None
    review_required: bool = True
    dry_run: bool = True
    use_company_research: bool = True
    custom_prompt: str = ''
    tone: str = 'professional'
    subject_style: str = 'personalized'
    email_length: str = 'medium'
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    send_start_time: str = '09:00'
    send_end_time: str = '17:00'
    active_days: Optional[List[int]] = None
    emails_per_hour: int = 10
    delay_seconds: int = 0
    daily_limit: int = 0
    max_sends: int = 0
    timezone: str = 'UTC'


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[int] = None
    email_account_id: Optional[int] = None
    review_required: Optional[bool] = None
    dry_run: Optional[bool] = None
    use_company_research: Optional[bool] = None
    custom_prompt: Optional[str] = None
    tone: Optional[str] = None
    subject_style: Optional[str] = None
    email_length: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    send_start_time: Optional[str] = None
    send_end_time: Optional[str] = None
    active_days: Optional[List[int]] = None
    emails_per_hour: Optional[int] = None
    delay_seconds: Optional[int] = None
    daily_limit: Optional[int] = None
    max_sends: Optional[int] = None
    timezone: Optional[str] = None


class CampaignOut(BaseModel):
    id: int
    name: str
    agent_id: Optional[int]
    email_account_id: Optional[int]
    status: str
    review_required: bool
    dry_run: bool
    use_company_research: bool
    custom_prompt: str
    tone: str
    subject_style: str
    email_length: str
    send_start_time: str
    send_end_time: str
    active_days: List[int]
    emails_per_hour: int
    delay_seconds: int
    daily_limit: int
    max_sends: int
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    recipient_count: int = 0
    generated_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    cancelled_count: int = 0
    created_at: Optional[str] = None



# ---------- Generated emails ----------
class GeneratedEmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None


class ManualEmailIn(BaseModel):
    recipient_id: int
    email_account_id: int
    ai_agent_id: Optional[int] = None
    subject: str = ''
    body: str = ''


class GeneratedEmailOut(BaseModel):
    id: int
    campaign_id: int
    recipient_id: int
    recipient_email: str
    recipient_name: str = ''
    subject: str
    body: str
    status: str
    error: str
    error_code: str = ''
    generated_at: Optional[str] = None
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None



# ---------- Billing ----------
class SubscriptionOut(BaseModel):
    plan: str
    status: str
    started_at: Optional[str] = None
    renews_at: Optional[str] = None



class UsageOut(BaseModel):
    ai_generation: int
    email_sent: int
    limits: dict


# ---------- Analytics ----------
class AnalyticsOut(BaseModel):
    emails_generated: int
    emails_scheduled: int
    emails_sent: int
    emails_failed: int
    emails_cancelled: int
    delivery_rate: float
    open_rate: Optional[float]
    reply_rate: Optional[float]
    campaigns: int
    recipients: int
    daily: List[dict]