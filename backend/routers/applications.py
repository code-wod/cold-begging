from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import SessionLocal
from backend.models import Application, Job, User, Resume, ApplicationStatus
from backend.schemas import ApplicationOut, ApplicationUpdate, ApplicationListOut, JobOut
from backend.security import get_current_user
from backend.services import get_application_service, get_job_service
import json

router = APIRouter(prefix='/api/applications', tags=['applications'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get('', response_model=ApplicationListOut)
def list_applications(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's applications with optional status filter."""
    service = get_application_service()
    result = service.list_applications(current_user.id, status, page, page_size)
    
    items = []
    for app in result['items']:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        job_out = None
        if job:
            try:
                skills = json.loads(job.skills) if job.skills else []
            except json.JSONDecodeError:
                skills = []
            job_out = JobOut(
                id=job.id,
                source=job.source,
                external_id=job.external_id,
                title=job.title,
                company_name=job.company_name,
                company_url=job.company_url,
                location=job.location,
                remote_type=job.remote_type,
                employment_type=job.employment_type,
                experience_level=job.experience_level,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                currency=job.currency,
                description=job.description,
                requirements=job.requirements,
                skills=skills,
                application_url=job.application_url,
                posted_at=job.posted_at.isoformat() if job.posted_at else None,
                discovered_at=job.discovered_at.isoformat() if job.discovered_at else None,
                status=job.status,
                created_at=job.created_at.isoformat() if job.created_at else None
            )
        
        try:
            screening = json.loads(app.screening_answers) if app.screening_answers else {}
        except json.JSONDecodeError:
            screening = {}
        
        try:
            match_analysis = json.loads(app.match_analysis) if app.match_analysis else {}
        except json.JSONDecodeError:
            match_analysis = {}
        
        items.append(ApplicationOut(
            id=app.id,
            job_id=app.job_id,
            job=job_out,
            resume_id=app.resume_id,
            status=app.status,
            match_score=app.match_score,
            cover_letter=app.cover_letter,
            screening_answers=screening,
            recruiter_email=app.recruiter_email,
            application_url=app.application_url,
            notes=app.notes,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            created_at=app.created_at.isoformat() if app.created_at else None,
            updated_at=app.updated_at.isoformat() if app.updated_at else None
        ))
    
    return ApplicationListOut(
        items=items,
        total=result['total'],
        page=result['page'],
        page_size=result['page_size']
    )


@router.get('/ready', response_model=ApplicationListOut)
def get_ready_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get applications ready for review."""
    service = get_application_service()
    apps = service.get_ready_applications(current_user.id)
    
    items = []
    for app in apps:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        job_out = None
        if job:
            try:
                skills = json.loads(job.skills) if job.skills else []
            except json.JSONDecodeError:
                skills = []
            job_out = JobOut(
                id=job.id,
                source=job.source,
                external_id=job.external_id,
                title=job.title,
                company_name=job.company_name,
                company_url=job.company_url,
                location=job.location,
                remote_type=job.remote_type,
                employment_type=job.employment_type,
                experience_level=job.experience_level,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                currency=job.currency,
                description=job.description,
                requirements=job.requirements,
                skills=skills,
                application_url=job.application_url,
                posted_at=job.posted_at.isoformat() if job.posted_at else None,
                discovered_at=job.discovered_at.isoformat() if job.discovered_at else None,
                status=job.status,
                created_at=job.created_at.isoformat() if job.created_at else None
            )
        
        try:
            screening = json.loads(app.screening_answers) if app.screening_answers else {}
        except json.JSONDecodeError:
            screening = {}
        
        items.append(ApplicationOut(
            id=app.id,
            job_id=app.job_id,
            job=job_out,
            resume_id=app.resume_id,
            status=app.status,
            match_score=app.match_score,
            cover_letter=app.cover_letter,
            screening_answers=screening,
            recruiter_email=app.recruiter_email,
            application_url=app.application_url,
            notes=app.notes,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            created_at=app.created_at.isoformat() if app.created_at else None,
            updated_at=app.updated_at.isoformat() if app.updated_at else None
        ))
    
    return ApplicationListOut(
        items=items,
        total=len(items),
        page=1,
        page_size=len(items)
    )


@router.get('/stats')
def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get application statistics."""
    service = get_application_service()
    return service.get_application_stats(current_user.id)


@router.get('/{app_id}', response_model=ApplicationOut)
def get_application(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get application detail."""
    service = get_application_service()
    app = service.get_application(app_id, current_user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    
    job = db.query(Job).filter(Job.id == app.job_id).first()
    job_out = None
    if job:
        try:
            skills = json.loads(job.skills) if job.skills else []
        except json.JSONDecodeError:
            skills = []
        job_out = JobOut(
            id=job.id,
            source=job.source,
            external_id=job.external_id,
            title=job.title,
            company_name=job.company_name,
            company_url=job.company_url,
            location=job.location,
            remote_type=job.remote_type,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            currency=job.currency,
            description=job.description,
            requirements=job.requirements,
            skills=skills,
            application_url=job.application_url,
            posted_at=job.posted_at.isoformat() if job.posted_at else None,
            discovered_at=job.discovered_at.isoformat() if job.discovered_at else None,
            status=job.status,
            created_at=job.created_at.isoformat() if job.created_at else None
        )
    
    try:
        screening = json.loads(app.screening_answers) if app.screening_answers else {}
    except json.JSONDecodeError:
        screening = {}
    
    try:
        match_analysis = json.loads(app.match_analysis) if app.match_analysis else {}
    except json.JSONDecodeError:
        match_analysis = {}
    
    return ApplicationOut(
        id=app.id,
        job_id=app.job_id,
        job=job_out,
        resume_id=app.resume_id,
        status=app.status,
        match_score=app.match_score,
        cover_letter=app.cover_letter,
        screening_answers=screening,
        recruiter_email=app.recruiter_email,
        application_url=app.application_url,
        notes=app.notes,
        applied_at=app.applied_at.isoformat() if app.applied_at else None,
        created_at=app.created_at.isoformat() if app.created_at else None,
        updated_at=app.updated_at.isoformat() if app.updated_at else None
    )


@router.patch('/{app_id}', response_model=ApplicationOut)
def update_application(
    app_id: int,
    data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application (status, notes)."""
    service = get_application_service()
    
    if data.status:
        app = service.update_application_status(app_id, current_user.id, data.status, data.notes or '')
    else:
        app = service.get_application(app_id, current_user.id)
        if not app:
            raise HTTPException(status_code=404, detail='Application not found')
        if data.notes is not None:
            app.notes = data.notes
            app.updated_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
            db.commit()
            db.refresh(app)
    
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    
    job = db.query(Job).filter(Job.id == app.job_id).first()
    job_out = None
    if job:
        try:
            skills = json.loads(job.skills) if job.skills else []
        except json.JSONDecodeError:
            skills = []
        job_out = JobOut(
            id=job.id,
            source=job.source,
            external_id=job.external_id,
            title=job.title,
            company_name=job.company_name,
            company_url=job.company_url,
            location=job.location,
            remote_type=job.remote_type,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            currency=job.currency,
            description=job.description,
            requirements=job.requirements,
            skills=skills,
            application_url=job.application_url,
            posted_at=job.posted_at.isoformat() if job.posted_at else None,
            discovered_at=job.discovered_at.isoformat() if job.discovered_at else None,
            status=job.status,
            created_at=job.created_at.isoformat() if job.created_at else None
        )
    
    try:
        screening = json.loads(app.screening_answers) if app.screening_answers else {}
    except json.JSONDecodeError:
        screening = {}
    
    return ApplicationOut(
        id=app.id,
        job_id=app.job_id,
        job=job_out,
        resume_id=app.resume_id,
        status=app.status,
        match_score=app.match_score,
        cover_letter=app.cover_letter,
        screening_answers=screening,
        recruiter_email=app.recruiter_email,
        application_url=app.application_url,
        notes=app.notes,
        applied_at=app.applied_at.isoformat() if app.applied_at else None,
        created_at=app.created_at.isoformat() if app.created_at else None,
        updated_at=app.updated_at.isoformat() if app.updated_at else None
    )


@router.post('/{app_id}/approve', response_model=ApplicationOut)
def approve_application(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve application for submission."""
    service = get_application_service()
    try:
        app = service.approve_application(app_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _format_application_response(app, db)


@router.post('/{app_id}/open', response_model=ApplicationOut)
def open_application(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark application as opened (user clicked apply link)."""
    service = get_application_service()
    try:
        app = service.open_application(app_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _format_application_response(app, db)


@router.post('/{app_id}/mark-applied', response_model=ApplicationOut)
def mark_applied(
    app_id: int,
    notes: str = '',
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark application as submitted."""
    service = get_application_service()
    try:
        app = service.mark_applied(app_id, current_user.id, notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _format_application_response(app, db)


@router.post('/{app_id}/reject', response_model=ApplicationOut)
def reject_application(
    app_id: int,
    reason: str = '',
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject an application."""
    service = get_application_service()
    try:
        app = service.reject_application(app_id, current_user.id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _format_application_response(app, db)


@router.post('/{app_id}/withdraw', response_model=ApplicationOut)
def withdraw_application(
    app_id: int,
    reason: str = '',
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Withdraw an application."""
    service = get_application_service()
    try:
        app = service.withdraw_application(app_id, current_user.id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _format_application_response(app, db)


def _format_application_response(app: Application, db: Session):
    """Helper to format application response."""
    job = db.query(Job).filter(Job.id == app.job_id).first()
    job_out = None
    if job:
        try:
            skills = json.loads(job.skills) if job.skills else []
        except json.JSONDecodeError:
            skills = []
        job_out = JobOut(
            id=job.id,
            source=job.source,
            external_id=job.external_id,
            title=job.title,
            company_name=job.company_name,
            company_url=job.company_url,
            location=job.location,
            remote_type=job.remote_type,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            currency=job.currency,
            description=job.description,
            requirements=job.requirements,
            skills=skills,
            application_url=job.application_url,
            posted_at=job.posted_at.isoformat() if job.posted_at else None,
            discovered_at=job.discovered_at.isoformat() if job.discovered_at else None,
            status=job.status,
            created_at=job.created_at.isoformat() if job.created_at else None
        )
    
    try:
        screening = json.loads(app.screening_answers) if app.screening_answers else {}
    except json.JSONDecodeError:
        screening = {}
    
    return ApplicationOut(
        id=app.id,
        job_id=app.job_id,
        job=job_out,
        resume_id=app.resume_id,
        status=app.status,
        match_score=app.match_score,
        cover_letter=app.cover_letter,
        screening_answers=screening,
        recruiter_email=app.recruiter_email,
        application_url=app.application_url,
        notes=app.notes,
        applied_at=app.applied_at.isoformat() if app.applied_at else None,
        created_at=app.created_at.isoformat() if app.created_at else None,
        updated_at=app.updated_at.isoformat() if app.updated_at else None
    )