import datetime as dt
import json

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


class JobProfile(Base):
    """Centralized job application profile for a user. One per user."""
    __tablename__ = 'job_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, index=True, nullable=False)

    # Personal
    first_name = Column(String(128), default='')
    middle_name = Column(String(128), default='')
    last_name = Column(String(128), default='')
    preferred_name = Column(String(128), default='')

    # Contact
    email = Column(String(255), default='')
    phone = Column(String(64), default='')
    country = Column(String(128), default='')
    state = Column(String(128), default='')
    city = Column(String(128), default='')
    address = Column(String(512), default='')
    postal_code = Column(String(32), default='')

    # Professional
    current_title = Column(String(255), default='')
    current_company = Column(String(255), default='')
    years_of_experience = Column(Integer)
    linkedin_url = Column(String(1024), default='')
    github_url = Column(String(1024), default='')
    portfolio_url = Column(String(1024), default='')
    personal_website = Column(String(1024), default='')

    # Education
    degree = Column(String(255), default='')
    field_of_study = Column(String(255), default='')
    university = Column(String(255), default='')
    graduation_year = Column(Integer)
    gpa = Column(String(32), default='')
    education_history = Column(Text, default='[]')  # JSON array

    # Work authorization
    authorized_to_work = Column(Boolean)
    requires_sponsorship = Column(Boolean)
    work_authorization_countries = Column(Text, default='[]')  # JSON array of country codes

    # Preferences
    preferred_locations = Column(Text, default='[]')  # JSON array
    remote_preference = Column(String(32), default='any')  # any, remote_only, hybrid_or_remote, onsite_only
    employment_type = Column(String(32), default='full_time')  # full_time, part_time, contract, internship
    notice_period = Column(String(64), default='')
    expected_salary = Column(String(64), default='')
    expected_salary_currency = Column(String(8), default='USD')
    willing_to_relocate = Column(Boolean)
    willing_to_travel = Column(Boolean)

    # Skills (JSON arrays)
    programming_languages = Column(Text, default='[]')
    frameworks = Column(Text, default='[]')
    databases = Column(Text, default='[]')
    tools = Column(Text, default='[]')
    other_skills = Column(Text, default='[]')

    # Experience history (JSON array)
    experience_history = Column(Text, default='[]')

    # Projects (JSON array)
    projects = Column(Text, default='[]')

    # Certifications (JSON array)
    certifications = Column(Text, default='[]')

    # Common application answers (JSON dict)
    common_answers = Column(Text, default='{}')

    # EEO / sensitive (JSON dict, only used if user explicitly configures)
    eeoo_answers = Column(Text, default='{}')

    # Custom answers (JSON dict for arbitrary Q&A pairs)
    custom_answers = Column(Text, default='{}')

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship('User', lazy='joined')

    def get_json_field(self, field_name, default=None):
        """Get a JSON field as parsed Python object."""
        val = getattr(self, field_name, None)
        if val is None:
            return default if default is not None else []
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else []

    def set_json_field(self, field_name, value):
        """Set a JSON field from a Python object."""
        setattr(self, field_name, json.dumps(value or []))

    def to_dict(self):
        """Serialize profile to dict with parsed JSON fields."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'preferred_name': self.preferred_name,
            'email': self.email,
            'phone': self.phone,
            'country': self.country,
            'state': self.state,
            'city': self.city,
            'address': self.address,
            'postal_code': self.postal_code,
            'current_title': self.current_title,
            'current_company': self.current_company,
            'years_of_experience': self.years_of_experience,
            'linkedin_url': self.linkedin_url,
            'github_url': self.github_url,
            'portfolio_url': self.portfolio_url,
            'personal_website': self.personal_website,
            'degree': self.degree,
            'field_of_study': self.field_of_study,
            'university': self.university,
            'graduation_year': self.graduation_year,
            'gpa': self.gpa,
            'education_history': self.get_json_field('education_history'),
            'authorized_to_work': self.authorized_to_work,
            'requires_sponsorship': self.requires_sponsorship,
            'work_authorization_countries': self.get_json_field('work_authorization_countries'),
            'preferred_locations': self.get_json_field('preferred_locations'),
            'remote_preference': self.remote_preference,
            'employment_type': self.employment_type,
            'notice_period': self.notice_period,
            'expected_salary': self.expected_salary,
            'expected_salary_currency': self.expected_salary_currency,
            'willing_to_relocate': self.willing_to_relocate,
            'willing_to_travel': self.willing_to_travel,
            'programming_languages': self.get_json_field('programming_languages'),
            'frameworks': self.get_json_field('frameworks'),
            'databases': self.get_json_field('databases'),
            'tools': self.get_json_field('tools'),
            'other_skills': self.get_json_field('other_skills'),
            'experience_history': self.get_json_field('experience_history'),
            'projects': self.get_json_field('projects'),
            'certifications': self.get_json_field('certifications'),
            'common_answers': self.get_json_field('common_answers', {}),
            'eeoo_answers': self.get_json_field('eeoo_answers', {}),
            'custom_answers': self.get_json_field('custom_answers', {}),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AutofillApplication(Base):
    """A single job application autofill session."""
    __tablename__ = 'autofill_applications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    job_profile_id = Column(Integer, ForeignKey('job_profiles.id'))

    # Job info
    job_url = Column(String(2048), nullable=False)
    company_name = Column(String(255), default='')
    role_title = Column(String(512), default='')
    ats_platform = Column(String(64), default='')  # greenhouse, lever, ashby, workday, unknown

    # Status: preparing, analyzing, filling, needs_review, ready, submitting, submitted, failed, cancelled
    status = Column(String(32), default='preparing', index=True)

    # Browser task tracking
    task_id = Column(String(64))
    browser_session_id = Column(String(128))

    # Resume used
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    resume_path = Column(String(1024), default='')

    # Summary stats
    total_fields = Column(Integer, default=0)
    auto_filled = Column(Integer, default=0)
    needs_review = Column(Integer, default=0)
    unanswered = Column(Integer, default=0)

    # Error tracking
    error_code = Column(String(64), default='')
    error_message = Column(Text, default='')
    requires_user_action = Column(String(64), default='')  # captcha_required, login_required, mfa_required

    # Screenshot
    screenshot_path = Column(String(1024), default='')

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    submitted_at = Column(DateTime(timezone=True))

    user = relationship('User', lazy='joined')
    job_profile = relationship('JobProfile', lazy='joined')
    resume = relationship('Resume', lazy='joined')
    fields = relationship('AutofillField', back_populates='application', lazy='dynamic', order_by='AutofillField.order')

    __table_args__ = (
        Index('ix_autofill_user_status', 'user_id', 'status'),
    )


class AutofillField(Base):
    """A single extracted/ mapped/ filled field in an autofill application."""
    __tablename__ = 'autofill_fields'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('autofill_applications.id'), index=True, nullable=False)

    # Field identification
    field_label = Column(String(512), default='')
    field_name = Column(String(255), default='')
    field_id = Column(String(255), default='')
    field_type = Column(String(32), default='text')  # text, email, phone, textarea, select, radio, checkbox, date, number, file, location, autocomplete, custom
    field_selector = Column(String(1024), default='')  # CSS selector for Playwright

    # Field context
    placeholder = Column(String(512), default='')
    aria_label = Column(String(512), default='')
    section = Column(String(255), default='')  # Form section/group name
    options = Column(Text, default='[]')  # JSON array for select/radio/checkbox options

    # Mapping
    profile_field = Column(String(255), default='')  # e.g. 'first_name', 'work_authorization.authorized'
    mapped_value = Column(Text, default='')  # Value from profile
    confidence = Column(Float, default=0.0)  # 0.0 - 1.0
    mapping_reasoning = Column(Text, default='')  # Why this mapping was chosen

    # User interaction
    user_value = Column(Text, default='')  # User-edited value (final value used)
    requires_review = Column(Boolean, default=False)
    user_edited = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)

    # Status: pending, mapped, filled, verified, failed, skipped
    status = Column(String(32), default='pending')

    # Order in form
    order = Column(Integer, default=0)

    # Raw DOM info for debugging
    raw_html = Column(Text, default='')

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    application = relationship('AutofillApplication', back_populates='fields')

    def get_options(self):
        try:
            return json.loads(self.options) if self.options else []
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'field_label': self.field_label,
            'field_name': self.field_name,
            'field_id': self.field_id,
            'field_type': self.field_type,
            'field_selector': self.field_selector,
            'placeholder': self.placeholder,
            'aria_label': self.aria_label,
            'section': self.section,
            'options': self.get_options(),
            'profile_field': self.profile_field,
            'mapped_value': self.mapped_value,
            'confidence': self.confidence,
            'mapping_reasoning': self.mapping_reasoning,
            'user_value': self.user_value,
            'requires_review': self.requires_review,
            'user_edited': self.user_edited,
            'skipped': self.skipped,
            'status': self.status,
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
