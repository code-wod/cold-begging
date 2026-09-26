from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from backend.database import Base


class ExtensionProfile(Base):
    """Stores user's application profile for the browser extension."""
    __tablename__ = 'extension_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)

    # Personal info (flattened for easy extension access)
    first_name = Column(String(255), default='')
    middle_name = Column(String(255), default='')
    last_name = Column(String(255), default='')
    full_name = Column(String(255), default='')
    email = Column(String(255), default='')
    phone = Column(String(64), default='')

    # Address
    street = Column(String(500), default='')
    city = Column(String(255), default='')
    state = Column(String(255), default='')
    country = Column(String(255), default='')
    postal_code = Column(String(64), default='')

    # Professional
    current_title = Column(String(255), default='')
    years_of_experience = Column(String(64), default='')
    current_company = Column(String(255), default='')
    linkedin = Column(String(1024), default='')
    github = Column(String(1024), default='')
    portfolio = Column(String(1024), default='')
    skills = Column(JSON, default=list)

    # Education (JSON array)
    education = Column(JSON, default=list)

    # Work authorization
    authorized_to_work = Column(Boolean, default=False)
    requires_sponsorship = Column(Boolean, default=False)
    willing_to_relocate = Column(Boolean, default=False)

    # Preferences
    remote_preference = Column(String(64), default='')
    notice_period = Column(String(64), default='')
    salary_expectation = Column(String(64), default='')

    # Documents
    resume_path = Column(String(1024), default='')
    resume_name = Column(String(255), default='')
    cover_letter_path = Column(String(1024), default='')

    # Custom Q&A answers (JSON)
    custom_answers = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExtensionLearnedAnswer(Base):
    """Stores learned answers for recurring application questions."""
    __tablename__ = 'extension_learned_answers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    question = Column(Text, nullable=False)
    normalized_question = Column(Text, nullable=False, index=True)
    answer = Column(Text, nullable=False)
    answer_type = Column(String(64), default='text')
    scope = Column(String(32), default='global')  # global, company, job, session
    source = Column(String(32), default='user')   # user, profile, ai, imported
    confidence = Column(Float, default=1.0)
    user_confirmed = Column(Boolean, default=False)
    used_count = Column(Integer, default=0)
    company = Column(String(255), default='')
    job_title = Column(String(255), default='')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExtensionSession(Base):
    """Tracks extension usage sessions."""
    __tablename__ = 'extension_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    url = Column(Text, nullable=False)
    company = Column(String(255), default='')
    job_title = Column(String(255), default='')
    platform = Column(String(64), default='')
    fields_detected = Column(Integer, default=0)
    fields_filled = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    completed = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
