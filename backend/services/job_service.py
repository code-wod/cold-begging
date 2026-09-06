import json
import logging
import datetime as dt
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from backend.models import (
    Job, JobPreferences, Resume, Application, JobSourceLog, User
)
from backend.schemas import JobPreferencesIn, ResumeIn, JobImportIn
from backend.services.source_providers import provider_registry
from backend.services.source_providers.base import JobListing
from backend.config import FREE_JOB_MATCHES_PER_DAY, PRO_JOB_MATCHES_PER_DAY
from backend.database import SessionLocal

logger = logging.getLogger('job_service')


class JobService:
    """Service for job management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_job(self, listing: JobListing, source: str) -> Job:
        """Create a new job from a normalized listing."""
        job_hash = provider_registry.get_provider(source).compute_job_hash(listing)
        
        # Check for existing
        existing = self.db.query(Job).filter(Job.job_hash == job_hash).first()
        if existing:
            # Update source_data to track multiple sources
            existing.source_data = self._merge_source_data(existing.source_data, listing.source_data)
            existing.updated_at = dt.datetime.now(dt.timezone.utc)
            self.db.commit()
            return existing
        
        job = Job(
            source=source,
            external_id=listing.external_id,
            title=listing.title,
            company_name=listing.company_name,
            company_url=listing.company_url,
            location=listing.location,
            remote_type=listing.remote_type,
            employment_type=listing.employment_type,
            experience_level=listing.experience_level,
            salary_min=listing.salary_min,
            salary_max=listing.salary_max,
            currency=listing.currency,
            description=listing.description,
            requirements=listing.requirements,
            skills=json.dumps(listing.skills or []),
            application_url=listing.application_url,
            posted_at=listing.posted_at,
            job_hash=job_hash,
            source_data=json.dumps(listing.source_data or {}),
            status='active'
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def _merge_source_data(self, existing_data: str, new_data: dict) -> str:
        """Merge source data from multiple sources."""
        try:
            existing = json.loads(existing_data) if existing_data else {}
        except json.JSONDecodeError:
            existing = {}
        existing.update(new_data)
        existing['_merged'] = True
        return json.dumps(existing)
    
    def get_job(self, job_id: int, user_id: Optional[int] = None) -> Optional[Job]:
        """Get a job by ID."""
        query = self.db.query(Job).filter(Job.id == job_id)
        if user_id is not None:
            # Jobs are global, but we might want to check if user has access
            pass
        return query.first()
    
    def list_jobs(
        self,
        user_id: Optional[int] = None,
        source: Optional[str] = None,
        status: str = 'active',
        location: Optional[str] = None,
        remote_type: Optional[str] = None,
        employment_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        company: Optional[str] = None,
        min_salary: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List jobs with filters."""
        query = self.db.query(Job).filter(Job.status == status)
        
        if source:
            query = query.filter(Job.source == source)
        if location:
            query = query.filter(Job.location.ilike(f'%{location}%'))
        if remote_type:
            query = query.filter(Job.remote_type == remote_type)
        if employment_type:
            query = query.filter(Job.employment_type == employment_type)
        if experience_level:
            query = query.filter(Job.experience_level == experience_level)
        if company:
            query = query.filter(Job.company_name.ilike(f'%{company}%'))
        if min_salary:
            query = query.filter(or_(
                Job.salary_min >= min_salary,
                Job.salary_max >= min_salary
            ))
        if search:
            query = query.filter(or_(
                Job.title.ilike(f'%{search}%'),
                Job.company_name.ilike(f'%{search}%'),
                Job.description.ilike(f'%{search}%'),
                Job.skills.ilike(f'%{search}%')
            ))
        
        total = query.count()
        jobs = query.order_by(desc(Job.discovered_at)).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            'items': jobs,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def import_job_from_url(self, url: str) -> Job:
        """Import a job from a URL using the appropriate provider."""
        import asyncio
        
        provider_name = provider_registry.detect_provider(url)
        provider = provider_registry.get_provider(provider_name)
        
        if not provider:
            raise ValueError(f'No provider found for URL: {url}')
        
        # Run async provider in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            listing = loop.run_until_complete(provider.get_job(url))
        finally:
            loop.close()
        
        if not listing:
            # Create minimal job record
            listing = JobListing(
                external_id=url,
                title='Unknown Position',
                company_name='Unknown Company',
                application_url=url,
                source_data={'url': url, 'error': 'Failed to extract job data'}
            )
        
        return self.create_job(listing, provider_name)
    
    def get_job_preferences(self, user_id: int) -> Optional[JobPreferences]:
        """Get user's job preferences."""
        return self.db.query(JobPreferences).filter(JobPreferences.user_id == user_id).first()
    
    def update_job_preferences(self, user_id: int, data: JobPreferencesIn) -> JobPreferences:
        """Update user's job preferences."""
        prefs = self.get_job_preferences(user_id)
        if not prefs:
            prefs = JobPreferences(user_id=user_id)
            self.db.add(prefs)
        
        prefs.preferred_roles = json.dumps(data.preferred_roles)
        prefs.preferred_locations = json.dumps(data.preferred_locations)
        prefs.employment_types = json.dumps(data.employment_types)
        prefs.experience_levels = json.dumps(data.experience_levels)
        prefs.skills = json.dumps(data.skills)
        prefs.minimum_salary = data.minimum_salary
        prefs.currency = data.currency
        prefs.remote_preference = data.remote_preference
        prefs.visa_sponsorship = data.visa_sponsorship
        prefs.updated_at = dt.datetime.now(dt.timezone.utc)
        
        self.db.commit()
        self.db.refresh(prefs)
        return prefs
    
    def create_resume(self, user_id: int, data: ResumeIn, file_path: str = '', text_content: str = '') -> Resume:
        """Create a new resume."""
        # If this is set as default, unset other defaults
        if data.is_default:
            self.db.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.is_default.is_(True)
            ).update({'is_default': False})
        
        resume = Resume(
            user_id=user_id,
            name=data.name,
            filename=data.filename or '',
            stored_path=file_path,
            text_content=text_content,
            resume_type=data.resume_type,
            is_default=data.is_default
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume
    
    def get_resumes(self, user_id: int) -> List[Resume]:
        """Get all resumes for a user."""
        return self.db.query(Resume).filter(Resume.user_id == user_id).order_by(desc(Resume.is_default), desc(Resume.created_at)).all()
    
    def get_resume(self, resume_id: int, user_id: int) -> Optional[Resume]:
        """Get a specific resume."""
        return self.db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    
    def set_default_resume(self, user_id: int, resume_id: int) -> Resume:
        """Set a resume as default."""
        self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_default.is_(True)
        ).update({'is_default': False})
        
        resume = self.get_resume(resume_id, user_id)
        if resume:
            resume.is_default = True
            self.db.commit()
            self.db.refresh(resume)
        return resume
    
    def delete_resume(self, user_id: int, resume_id: int) -> bool:
        """Delete a resume."""
        resume = self.get_resume(resume_id, user_id)
        if not resume:
            return False
        self.db.delete(resume)
        self.db.commit()
        return True
    
    def check_match_limit(self, user_id: int) -> bool:
        """Check if user has exceeded daily match limit."""
        from backend.models import Subscription
        sub = self.db.query(Subscription).filter(Subscription.user_id == user_id).first()
        plan = sub.plan if sub else 'free'
        limit = PRO_JOB_MATCHES_PER_DAY if plan == 'pro' else FREE_JOB_MATCHES_PER_DAY
        
        # Count matches today
        today_start = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.created_at >= today_start
        ).count()
        
        return count < limit
    
    def log_source_run(self, source: str, status: str, jobs_found: int = 0, jobs_new: int = 0, jobs_duplicate: int = 0, error: str = None) -> JobSourceLog:
        """Log a job source discovery run."""
        log = JobSourceLog(
            source=source,
            status=status,
            jobs_found=jobs_found,
            jobs_new=jobs_new,
            jobs_duplicate=jobs_duplicate,
            error=error
        )
        self.db.add(log)
        self.db.commit()
        return log
    
    def get_source_logs(self, source: Optional[str] = None, limit: int = 50) -> List[JobSourceLog]:
        """Get job source run logs."""
        query = self.db.query(JobSourceLog).order_by(desc(JobSourceLog.started_at))
        if source:
            query = query.filter(JobSourceLog.source == source)
        return query.limit(limit).all()


def get_job_service() -> JobService:
    db = SessionLocal()
    try:
        return JobService(db)
    finally:
        db.close()