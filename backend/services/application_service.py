import json
import logging
import datetime as dt
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from backend.models import Application, Job, Resume, User, ApplicationStatus
from backend.services.job_service import JobService
from backend.services.matching_service import MatchingService
from backend.database import SessionLocal

logger = logging.getLogger('application_service')


class ApplicationService:
    """Service for application queue management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.job_service = JobService(db)
        self.matching_service = MatchingService(db)
    
    def create_application(
        self,
        user: User,
        job: Job,
        match_result: Dict[str, Any],
        application_package: Dict[str, Any]
    ) -> Application:
        """Create an application record from match and package."""
        # Check for existing application
        existing = self.db.query(Application).filter(
            Application.user_id == user.id,
            Application.job_id == job.id
        ).first()
        
        if existing:
            # Update existing
            existing.status = ApplicationStatus.READY
            existing.match_score = match_result.get('match_score')
            existing.match_analysis = json.dumps(match_result)
            existing.cover_letter = application_package.get('cover_letter', '')
            existing.screening_answers = json.dumps(application_package.get('screening_answers', {}))
            existing.recruiter_email = application_package.get('recruiter_email', '')
            existing.recommended_resume_id = application_package.get('recommended_resume_id')
            existing.application_url = job.application_url
            existing.updated_at = dt.datetime.now(dt.timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        app = Application(
            user_id=user.id,
            job_id=job.id,
            resume_id=application_package.get('recommended_resume_id'),
            status=ApplicationStatus.READY,
            match_score=match_result.get('match_score'),
            match_analysis=json.dumps(match_result),
            cover_letter=application_package.get('cover_letter', ''),
            screening_answers=json.dumps(application_package.get('screening_answers', {})),
            recruiter_email=application_package.get('recruiter_email', ''),
            application_url=job.application_url
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app
    
    def get_application(self, app_id: int, user_id: int) -> Optional[Application]:
        """Get application by ID for a user."""
        return self.db.query(Application).filter(
            Application.id == app_id,
            Application.user_id == user_id
        ).first()
    
    def list_applications(
        self,
        user_id: int,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List user's applications with optional status filter."""
        query = self.db.query(Application).filter(Application.user_id == user_id)
        
        if status:
            query = query.filter(Application.status == status)
        
        total = query.count()
        apps = query.order_by(desc(Application.created_at)).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            'items': apps,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def get_ready_applications(self, user_id: int) -> List[Application]:
        """Get applications ready for review (READY status)."""
        return self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.status == ApplicationStatus.READY
        ).order_by(desc(Application.match_score), desc(Application.created_at)).all()
    
    def approve_application(self, app_id: int, user_id: int) -> Application:
        """Approve an application for submission."""
        app = self.get_application(app_id, user_id)
        if not app:
            raise ValueError('Application not found')
        
        if app.status not in [ApplicationStatus.READY, ApplicationStatus.APPROVED]:
            raise ValueError(f'Cannot approve application in status: {app.status}')
        
        app.status = ApplicationStatus.APPROVED
        app.updated_at = dt.datetime.now(dt.timezone.utc)
        self.db.commit()
        self.db.refresh(app)
        return app
    
    def open_application(self, app_id: int, user_id: int) -> Application:
        """Mark application as opened (user clicked apply link)."""
        app = self.get_application(app_id, user_id)
        if not app:
            raise ValueError('Application not found')
        
        app.status = ApplicationStatus.APPLICATION_OPENED
        app.updated_at = dt.datetime.now(dt.timezone.utc)
        self.db.commit()
        self.db.refresh(app)
        return app
    
    def mark_applied(self, app_id: int, user_id: int, notes: str = '') -> Application:
        """Mark application as submitted."""
        app = self.get_application(app_id, user_id)
        if not app:
            raise ValueError('Application not found')
        
        app.status = ApplicationStatus.APPLIED
        app.applied_at = dt.datetime.now(dt.timezone.utc)
        if notes:
            app.notes = (app.notes + '\n' if app.notes else '') + f'Applied: {notes}'
        app.updated_at = dt.datetime.now(dt.timezone.utc)
        self.db.commit()
        self.db.refresh(app)
        return app
    
    def update_application_status(self, app_id: int, user_id: int, status: str, notes: str = '') -> Application:
        """Update application status."""
        app = self.get_application(app_id, user_id)
        if not app:
            raise ValueError('Application not found')
        
        valid_statuses = ApplicationStatus.ALL
        if status not in valid_statuses:
            raise ValueError(f'Invalid status: {status}. Valid: {valid_statuses}')
        
        app.status = status
        if notes:
            app.notes = (app.notes + '\n' if app.notes else '') + notes
        app.updated_at = dt.datetime.now(dt.timezone.utc)
        self.db.commit()
        self.db.refresh(app)
        return app
    
    def reject_application(self, app_id: int, user_id: int, reason: str = '') -> Application:
        """Reject an application."""
        return self.update_application_status(app_id, user_id, ApplicationStatus.REJECTED, f'Rejected: {reason}')
    
    def withdraw_application(self, app_id: int, user_id: int, reason: str = '') -> Application:
        """Withdraw an application."""
        return self.update_application_status(app_id, user_id, ApplicationStatus.WITHDRAWN, f'Withdrawn: {reason}')
    
    def get_application_stats(self, user_id: int) -> Dict[str, int]:
        """Get application statistics for a user."""
        from sqlalchemy import func
        
        stats = self.db.query(
            Application.status,
            func.count(Application.id)
        ).filter(Application.user_id == user_id).group_by(Application.status).all()
        
        result = {status.value: 0 for status in ApplicationStatus}
        for status, count in stats:
            result[status] = count
        
        return result
    
    def process_job_match(
        self,
        user: User,
        job: Job,
        model_id: Optional[int] = None
    ) -> Optional[Application]:
        """Full pipeline: match job -> prepare application -> create application record."""
        # Run matching
        match_result = self.matching_service.match_job(user, job, model_id)
        
        # Only prepare application if score meets threshold
        score = match_result.get('match_score', 0)
        if score < 70:  # REVIEW_THRESHOLD
            logger.info('Job %d below threshold for user %d: %d', job.id, user.id, score)
            # Still create application with DISCOVERED/MATCHED status for tracking
            app = Application(
                user_id=user.id,
                job_id=job.id,
                status=ApplicationStatus.MATCHED,
                match_score=score,
                match_analysis=json.dumps(match_result)
            )
            self.db.add(app)
            self.db.commit()
            return app
        
        # Prepare application package
        package = self.matching_service.prepare_application(user, job, match_result, model_id)
        
        # Create application
        app = self.create_application(user, job, match_result, package)
        
        return app


def get_application_service() -> ApplicationService:
    db = SessionLocal()
    try:
        return ApplicationService(db)
    finally:
        db.close()