from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import SessionLocal
from backend.models import Job, JobPreferences, Resume, User, Application
from backend.schemas import (
    JobPreferencesIn, JobPreferencesOut,
    ResumeIn, ResumeLinkIn, ResumeOut,
    JobOut, JobListOut, JobImportIn, JobImportOut,
    JobMatchOut, JobPrepareOut, JobSourceOut,
    JobSourceCapabilities
)
from backend.security import get_current_user
from backend.services import get_job_service, get_matching_service, get_application_service, provider_registry
from backend.config import FREE_RESUME_LIMIT, PRO_RESUME_LIMIT
from backend.encryption import encrypt_plaintext
import os
import shutil
import datetime as dt
import json

router = APIRouter(prefix='/api/jobs', tags=['jobs'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- Job Preferences ----

@router.get('/preferences', response_model=JobPreferencesOut)
def get_job_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's job search preferences."""
    service = get_job_service()
    prefs = service.get_job_preferences(current_user.id)
    if not prefs:
        return JobPreferencesOut()
    
    return JobPreferencesOut(
        preferred_roles=json.loads(prefs.preferred_roles) if prefs.preferred_roles else [],
        preferred_locations=json.loads(prefs.preferred_locations) if prefs.preferred_locations else [],
        employment_types=json.loads(prefs.employment_types) if prefs.employment_types else [],
        experience_levels=json.loads(prefs.experience_levels) if prefs.experience_levels else [],
        skills=json.loads(prefs.skills) if prefs.skills else [],
        minimum_salary=prefs.minimum_salary,
        currency=prefs.currency,
        remote_preference=prefs.remote_preference,
        visa_sponsorship=prefs.visa_sponsorship,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None
    )


@router.put('/preferences', response_model=JobPreferencesOut)
def update_job_preferences(
    data: JobPreferencesIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's job search preferences."""
    service = get_job_service()
    prefs = service.update_job_preferences(current_user.id, data)
    
    return JobPreferencesOut(
        preferred_roles=json.loads(prefs.preferred_roles) if prefs.preferred_roles else [],
        preferred_locations=json.loads(prefs.preferred_locations) if prefs.preferred_locations else [],
        employment_types=json.loads(prefs.employment_types) if prefs.employment_types else [],
        experience_levels=json.loads(prefs.experience_levels) if prefs.experience_levels else [],
        skills=json.loads(prefs.skills) if prefs.skills else [],
        minimum_salary=prefs.minimum_salary,
        currency=prefs.currency,
        remote_preference=prefs.remote_preference,
        visa_sponsorship=prefs.visa_sponsorship,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None
    )


# ---- Resumes ----

@router.get('/resumes', response_model=List[ResumeOut])
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all resumes for current user."""
    service = get_job_service()
    resumes = service.get_resumes(current_user.id)
    
    result = []
    for r in resumes:
        try:
            skills = json.loads(r.skills) if r.skills else []
        except json.JSONDecodeError:
            skills = []
        result.append(ResumeOut(
            id=r.id,
            name=r.name,
            filename=r.filename,
            resume_type=r.resume_type,
            is_default=r.is_default,
            skills=skills,
            experience_years=r.experience_years,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None
        ))
    return result


@router.post('/resumes', response_model=ResumeOut)
async def upload_resume(
    name: str = Form(...),
    resume_type: str = Form('general'),
    is_default: bool = Form(False),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a resume PDF."""
    # Check resume limit
    from backend.models import Subscription
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    plan = sub.plan if sub else 'free'
    limit = PRO_RESUME_LIMIT if plan == 'pro' else FREE_RESUME_LIMIT
    
    current_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f'Resume limit reached ({limit} for {plan} plan). Upgrade or delete old resumes.'
        )
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files are allowed')
    
    # Save file
    upload_dir = os.getenv('RESUME_UPLOAD_DIR', os.path.join(os.getenv('UPLOAD_DIR', 'uploads'), 'resumes'))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f'{current_user.id}_{dt.datetime.now().timestamp()}_{file.filename}')
    with open(file_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    
    # Extract text
    text_content = ''
    skills = []
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text_content += page.extract_text() or ''
        
        # Extract skills from text
        common_skills = [
            'Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Java', 'C++', 'C#',
            'React', 'Vue', 'Angular', 'Next.js', 'Node.js', 'Django', 'Flask', 'FastAPI',
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'DynamoDB',
            'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
            'Git', 'CI/CD', 'Jenkins', 'GitHub Actions', 'GitLab CI',
            'GraphQL', 'REST', 'gRPC', 'Kafka', 'RabbitMQ',
        ]
        text_lower = text_content.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                skills.append(skill)
    except Exception:
        pass
    
    service = get_job_service()
    resume = service.create_resume(
        current_user.id,
        ResumeIn(name=name, filename=file.filename, resume_type=resume_type, is_default=is_default),
        file_path=file_path,
        text_content=text_content
    )
    resume.skills = json.dumps(skills)
    db.commit()
    
    return ResumeOut(
        id=resume.id,
        name=resume.name,
        filename=resume.filename,
        resume_type=resume.resume_type,
        is_default=resume.is_default,
        skills=skills,
        experience_years=resume.experience_years,
        created_at=resume.created_at.isoformat() if resume.created_at else None,
        updated_at=resume.updated_at.isoformat() if resume.updated_at else None
    )


@router.post('/resumes/link', response_model=ResumeOut)
def add_resume_link(
    data: ResumeLinkIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a resume link (Google Drive, Notion, personal site, etc.)."""
    from backend.models import Subscription
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    plan = sub.plan if sub else 'free'
    limit = PRO_RESUME_LIMIT if plan == 'pro' else FREE_RESUME_LIMIT
    
    current_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f'Resume limit reached ({limit} for {plan} plan).'
        )
    
    service = get_job_service()
    resume = service.create_resume(
        current_user.id,
        ResumeIn(name=data.name, resume_type=data.resume_type, is_default=data.is_default),
        file_path='',
        text_content=f'Resume link: {data.url}'
    )
    resume.filename = ''
    db.commit()
    
    return ResumeOut(
        id=resume.id,
        name=resume.name,
        filename='',
        resume_type=resume.resume_type,
        is_default=resume.is_default,
        skills=[],
        experience_years=None,
        created_at=resume.created_at.isoformat() if resume.created_at else None,
        updated_at=resume.updated_at.isoformat() if resume.updated_at else None
    )


@router.patch('/resumes/{resume_id}', response_model=ResumeOut)
def update_resume(
    resume_id: int,
    name: Optional[str] = Form(None),
    resume_type: Optional[str] = Form(None),
    is_default: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update resume metadata."""
    service = get_job_service()
    resume = service.get_resume(resume_id, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail='Resume not found')
    
    if name is not None:
        resume.name = name
    if resume_type is not None:
        resume.resume_type = resume_type
    if is_default is not None and is_default:
        service.set_default_resume(current_user.id, resume_id)
        db.refresh(resume)
    
    db.commit()
    db.refresh(resume)
    
    try:
        skills = json.loads(resume.skills) if resume.skills else []
    except json.JSONDecodeError:
        skills = []
    
    return ResumeOut(
        id=resume.id,
        name=resume.name,
        filename=resume.filename,
        resume_type=resume.resume_type,
        is_default=resume.is_default,
        skills=skills,
        experience_years=resume.experience_years,
        created_at=resume.created_at.isoformat() if resume.created_at else None,
        updated_at=resume.updated_at.isoformat() if resume.updated_at else None
    )


@router.post('/resumes/{resume_id}/default', response_model=ResumeOut)
def set_default_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set a resume as default."""
    service = get_job_service()
    resume = service.set_default_resume(current_user.id, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail='Resume not found')
    
    try:
        skills = json.loads(resume.skills) if resume.skills else []
    except json.JSONDecodeError:
        skills = []
    
    return ResumeOut(
        id=resume.id,
        name=resume.name,
        filename=resume.filename,
        resume_type=resume.resume_type,
        is_default=resume.is_default,
        skills=skills,
        experience_years=resume.experience_years,
        created_at=resume.created_at.isoformat() if resume.created_at else None,
        updated_at=resume.updated_at.isoformat() if resume.updated_at else None
    )


@router.delete('/resumes/{resume_id}')
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a resume."""
    service = get_job_service()
    success = service.delete_resume(current_user.id, resume_id)
    if not success:
        raise HTTPException(status_code=404, detail='Resume not found')
    
    # Delete file if exists
    resume = service.get_resume(resume_id, current_user.id)
    if resume and resume.stored_path and os.path.exists(resume.stored_path):
        try:
            os.remove(resume.stored_path)
        except Exception:
            pass
    
    return {'message': 'Resume deleted'}


# ---- Jobs ----

@router.get('', response_model=JobListOut)
def list_jobs(
    source: Optional[str] = Query(None),
    status: str = Query('active'),
    location: Optional[str] = Query(None),
    remote_type: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    min_salary: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List jobs with filters."""
    service = get_job_service()
    result = service.list_jobs(
        user_id=current_user.id,
        source=source,
        status=status,
        location=location,
        remote_type=remote_type,
        employment_type=employment_type,
        experience_level=experience_level,
        company=company,
        min_salary=min_salary,
        search=search,
        page=page,
        page_size=page_size
    )
    
    items = []
    for job in result['items']:
        try:
            skills = json.loads(job.skills) if job.skills else []
        except json.JSONDecodeError:
            skills = []
        items.append(JobOut(
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
        ))
    
    return JobListOut(
        items=items,
        total=result['total'],
        page=result['page'],
        page_size=result['page_size']
    )


@router.get('/sources', response_model=List[JobSourceOut])
def list_sources():
    """List all supported job sources and their capabilities."""
    sources = []
    for name in provider_registry.get_provider_names():
        provider = provider_registry.get_provider(name)
        provider_caps = provider.get_capabilities() if provider else None
        if provider_caps:
            caps = JobSourceCapabilities(
                search=provider_caps.search,
                job_details=provider_caps.job_details,
                application_api=provider_caps.application_api,
                candidate_apply_api=provider_caps.candidate_apply_api,
            )
        else:
            caps = JobSourceCapabilities()
        sources.append(JobSourceOut(name=name, capabilities=caps))
    return sources


@router.post('/import', response_model=JobImportOut)
def import_job(
    data: JobImportIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import a job from a URL."""
    service = get_job_service()
    
    try:
        job = service.import_job_from_url(data.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to import job: {str(e)}')
    
    # Run matching
    matching_service = get_matching_service()
    match_result = matching_service.match_job(current_user, job)
    
    # Create application if score is high enough
    application_service = get_application_service()
    application_service.process_job_match(current_user, job)
    
    return JobImportOut(
        job_id=job.id,
        is_new=True,  # Could check if it was newly created
        match_score=match_result.get('match_score'),
        message=f'Job imported successfully. Match score: {match_result.get("match_score")}%'
    )


@router.get('/{job_id}', response_model=JobOut)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job details."""
    service = get_job_service()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    
    try:
        skills = json.loads(job.skills) if job.skills else []
    except json.JSONDecodeError:
        skills = []
    
    return JobOut(
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


@router.post('/{job_id}/match', response_model=JobMatchOut)
def match_job(
    job_id: int,
    model_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-run AI matching for a job."""
    service = get_job_service()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    
    matching_service = get_matching_service()
    result = matching_service.match_job(current_user, job, model_id)
    
    return JobMatchOut(**result)


@router.post('/{job_id}/prepare', response_model=JobPrepareOut)
def prepare_application(
    job_id: int,
    model_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate application package for a job."""
    service = get_job_service()
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    
    matching_service = get_matching_service()
    match_result = matching_service.match_job(current_user, job, model_id)
    
    package = matching_service.prepare_application(current_user, job, match_result, model_id)
    
    # Create application record
    application_service = get_application_service()
    app = application_service.create_application(current_user, job, match_result, package)
    
    return JobPrepareOut(
        application_id=app.id,
        cover_letter=package['cover_letter'],
        screening_answers=package['screening_answers'],
        recruiter_email=package['recruiter_email'],
        recommended_resume_id=package['recommended_resume_id'],
        match_analysis=package['match_analysis']
    )