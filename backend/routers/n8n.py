from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.database import SessionLocal
from backend.models import User, Job, Application, JobPreferences, Resume, Subscription
from backend.services import get_job_service, get_matching_service, get_application_service
from backend.config import N8N_WEBHOOK_SECRET
import logging
import datetime as dt

logger = logging.getLogger('n8n')

router = APIRouter(prefix='/api/n8n', tags=['n8n'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_n8n_secret(x_n8n_secret: str = Header(...)):
    """Verify n8n webhook secret."""
    if x_n8n_secret != N8N_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail='Invalid n8n secret')
    return True


class JobDiscoveryRequest(BaseModel):
    user_id: Optional[int] = None
    sources: Optional[List[str]] = None
    search_params: Optional[dict] = None


class JobDiscoveryResponse(BaseModel):
    jobs_found: int
    jobs_new: int
    jobs_duplicate: int
    matches_triggered: int
    applications_created: int


class MatchAndPrepareRequest(BaseModel):
    job_id: int
    user_id: int


class NotificationRequest(BaseModel):
    user_id: int
    type: str  # job_match, application_ready, followup
    data: dict


@router.post('/webhook/job-discovery', response_model=JobDiscoveryResponse)
async def webhook_job_discovery(
    request: JobDiscoveryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """
    n8n webhook to trigger job discovery for users.
    Can run for all users or a specific user.
    """
    job_service = get_job_service()
    matching_service = get_matching_service()
    application_service = get_application_service()
    
    # Get users to process
    if request.user_id:
        users = db.query(User).filter(User.id == request.user_id).all()
    else:
        users = db.query(User).all()
    
    total_found = 0
    total_new = 0
    total_duplicate = 0
    total_matches = 0
    total_apps = 0
    
    for user in users:
        # Check daily match limit
        if not job_service.check_match_limit(user.id):
            logger.info('User %d exceeded daily match limit', user.id)
            continue
        
        # Get user's job preferences
        prefs = job_service.get_job_preferences(user.id)
        if not prefs:
            continue
        
        # Build search params from preferences
        try:
            preferred_roles = eval(prefs.preferred_roles) if prefs.preferred_roles else []
            preferred_locations = eval(prefs.preferred_locations) if prefs.preferred_locations else []
        except Exception:
            preferred_roles = []
            preferred_locations = []
        
        # Run discovery for each role/location combination
        sources = request.sources or ['greenhouse', 'lever', 'ashby', 'company']
        
        for source_name in sources:
            from backend.services.source_providers import provider_registry
            provider = provider_registry.get_provider(source_name)
            if not provider or not provider.capabilities.search:
                continue
            
            # Search with first role/location as query
            for role in preferred_roles[:3]:
                for location in preferred_locations[:3]:
                    from backend.services.source_providers.base import JobSearchParams
                    search_params = JobSearchParams(
                        query=role,
                        location=location,
                        limit=20
                    )
                    
                    try:
                        listings = await provider.search_jobs(search_params)
                        total_found += len(listings)
                        
                        for listing in listings:
                            job = job_service.create_job(listing, source_name)
                            if job.job_hash == listing.external_id:  # New job (simplified check)
                                total_new += 1
                            else:
                                total_duplicate += 1
                            
                            # Trigger matching
                            match_result = matching_service.match_job(user, job)
                            total_matches += 1
                            
                            if match_result.get('match_score', 0) >= 70:
                                app = application_service.process_job_match(user, job)
                                if app:
                                    total_apps += 1
                    except Exception as e:
                        logger.error('Error searching %s for user %d: %s', source_name, user.id, e)
                        job_service.log_source_run(source_name, 'failed', error=str(e))
                        continue
    
    return JobDiscoveryResponse(
        jobs_found=total_found,
        jobs_new=total_new,
        jobs_duplicate=total_duplicate,
        matches_triggered=total_matches,
        applications_created=total_apps
    )


@router.post('/webhook/match-and-prepare')
async def webhook_match_and_prepare(
    request: MatchAndPrepareRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Trigger match and application preparation for a specific job/user."""
    matching_service = get_matching_service()
    application_service = get_application_service()
    
    user = db.query(User).filter(User.id == request.user_id).first()
    job = db.query(Job).filter(Job.id == request.job_id).first()
    
    if not user or not job:
        raise HTTPException(status_code=404, detail='User or job not found')
    
    match_result = matching_service.match_job(user, job)
    app = application_service.process_job_match(user, job)
    
    return {
        'match_score': match_result.get('match_score'),
        'recommendation': match_result.get('recommendation'),
        'application_id': app.id if app else None,
        'status': app.status if app else 'no_application'
    }


@router.post('/webhook/notify')
async def webhook_notify(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Send notification to user."""
    from backend.services.notification_service import NotificationService
    notification_service = NotificationService(db)
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    
    if request.type == 'job_match':
        await notification_service.send_job_match_notification(user, request.data)
    elif request.type == 'application_ready':
        await notification_service.send_application_ready_notification(user, request.data)
    elif request.type == 'followup':
        await notification_service.send_followup_notification(user, request.data)
    
    return {'status': 'sent'}


@router.get('/users/active')
def get_active_users(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Get users who have job preferences configured."""
    users = db.query(User).join(JobPreferences).filter(
        JobPreferences.preferred_roles != '[]'
    ).all()
    
    return [
        {
            'id': u.id,
            'email': u.email,
            'plan': u.subscription.plan if u.subscription else 'free'
        }
        for u in users
    ]


@router.get('/jobs/pending-match')
def get_jobs_pending_match(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Get jobs that haven't been matched for users with preferences."""
    # Jobs discovered in last 24h without application
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    
    jobs = db.query(Job).filter(
        Job.discovered_at >= cutoff,
        ~Job.id.in_(
            db.query(Application.job_id).filter(Application.user_id == User.id)
        )
    ).limit(limit).all()
    
    return [
        {
            'id': j.id,
            'title': j.title,
            'company_name': j.company_name,
            'source': j.source,
            'discovered_at': j.discovered_at.isoformat()
        }
        for j in jobs
    ]


@router.post('/webhook/followup-check')
async def webhook_followup_check(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Check for applications needing follow-up."""
    from backend.services.notification_service import NotificationService
    notification_service = NotificationService(db)
    
    # Find applications in applied/screening status for > 7 days
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    
    apps = db.query(Application).filter(
        Application.status.in_(['applied', 'screening']),
        Application.applied_at <= cutoff
    ).all()
    
    count = 0
    for app in apps:
        await notification_service.send_followup_notification(app.user, {
            'application_id': app.id,
            'job_title': app.job.title,
            'company_name': app.job.company_name,
            'days_since_applied': (dt.datetime.now(dt.timezone.utc) - app.applied_at).days,
            'status': app.status
        })
        count += 1
    
    return {'followups_sent': count}


# ==================== AGENT WEBHOOKS ====================

class AgentRunRequest(BaseModel):
    user_id: Optional[int] = None
    platforms: Optional[List[str]] = None
    search_config: Optional[dict] = None
    dry_run: bool = True


class AgentRunResponse(BaseModel):
    users_processed: int
    jobs_found: int
    matches_triggered: int
    applications_created: int
    errors: List[str] = []


@router.post('/webhook/agent/run', response_model=AgentRunResponse)
async def webhook_agent_run(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """
    n8n webhook to trigger the browser-based job application agent.
    Runs job search, matching, and application preparation for users.
    """
    from backend.browser.session import get_session_manager
    from backend.providers import provider_registry
    from backend.providers.base import SearchConfig
    from backend.services import get_job_service, get_matching_service, get_application_service
    
    job_service = get_job_service()
    matching_service = get_matching_service()
    application_service = get_application_service()
    session_manager = get_session_manager()
    
    # Get users to process
    if request.user_id:
        users = db.query(User).filter(User.id == request.user_id).all()
    else:
        # Get all users with connected portals
        users = db.query(User).join(JobPreferences).filter(
            JobPreferences.preferred_roles != '[]'
        ).all()
    
    total_users = 0
    total_jobs = 0
    total_matches = 0
    total_apps = 0
    errors = []
    
    for user in users:
        try:
            # Check daily match limit
            if not job_service.check_match_limit(user.id):
                logger.info('User %d exceeded daily match limit', user.id)
                continue
            
            # Get user preferences
            prefs = job_service.get_job_preferences(user.id)
            if not prefs:
                continue
            
            # Parse preferences
            try:
                preferred_roles = eval(prefs.preferred_roles) if prefs.preferred_roles else []
                preferred_locations = eval(prefs.preferred_locations) if prefs.preferred_locations else []
                employment_types = eval(prefs.employment_types) if prefs.employment_types else []
                experience_levels = eval(prefs.experience_levels) if prefs.experience_levels else []
                skills = eval(prefs.skills) if prefs.skills else []
            except Exception:
                preferred_roles = []
                preferred_locations = []
                employment_types = []
                experience_levels = []
                skills = []
            
            # Use request config or user preferences
            platforms = request.platforms or ['linkedin', 'naukri', 'wellfound', 'hirist', 'instahyre']
            search_cfg = request.search_config or {}
            search_config = SearchConfig(
                keywords=search_cfg.get('keywords') if search_cfg else preferred_roles[:5],
                locations=search_cfg.get('locations') if search_cfg else preferred_locations[:5],
                remote=search_cfg.get('remote', prefs.remote_preference in ['remote_only', 'hybrid_or_remote']) if search_cfg else prefs.remote_preference in ['remote_only', 'hybrid_or_remote'],
                job_types=search_cfg.get('job_types') if search_cfg else employment_types,
            )
            
            # Process each connected platform
            for platform in platforms:
                provider = provider_registry.get(platform)
                if not provider or not provider.capabilities.job_search:
                    continue
                
                # Check session
                session = await session_manager.get_session_info(user.id, platform)
                if session.status != 'connected':
                    logger.info('User %d not connected to %s', user.id, platform)
                    continue
                
                # Create browser context and search
                try:
                    async with session_manager._browser_manager.persistent_context(user.id, platform) as context:
                        page = await context.new_page()
                        
                        # Search jobs on this platform
                        listings = await provider.search_jobs(page, search_config)
                        total_jobs += len(listings)
                        
                        for listing in listings:
                            job = job_service.create_job(listing, platform)
                            
                            # Check for duplicate application
                            existing_app = db.query(Application).filter(
                                Application.user_id == user.id,
                                Application.job_id == job.id
                            ).first()
                            if existing_app:
                                continue
                            
                            # Run AI matching
                            match_result = matching_service.match_job(user, job)
                            total_matches += 1
                            
                            # Only proceed if match score meets threshold
                            min_score = 70
                            if match_result.get('match_score', 0) >= min_score:
                                app = application_service.process_job_match(user, job)
                                if app:
                                    total_apps += 1
                        
                        await page.close()
                        
                except Exception as e:
                    logger.error('Error searching %s for user %d: %s', platform, user.id, e)
                    errors.append(f'{platform}: {str(e)}')
                    continue
            
            total_users += 1
            
        except Exception as e:
            logger.error('Error processing user %d: %s', user.id, e)
            errors.append(f'user_{user.id}: {str(e)}')
            continue
    
    return AgentRunResponse(
        users_processed=total_users,
        jobs_found=total_jobs,
        matches_triggered=total_matches,
        applications_created=total_apps,
        errors=errors
    )


@router.post('/webhook/agent/notify')
async def webhook_agent_notify(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Send agent-specific notifications (applications ready, errors, etc.)."""
    from backend.services.notification_service import NotificationService
    notification_service = NotificationService(db)
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    
    if request.type == 'applications_ready':
        await notification_service.send_applications_ready_notification(user, request.data)
    elif request.type == 'agent_error':
        await notification_service.send_agent_error_notification(user, request.data)
    elif request.type == 'agent_completed':
        await notification_service.send_agent_completed_notification(user, request.data)
    
    return {'status': 'sent'}


@router.get('/agent/users-with-portals')
def get_users_with_connected_portals(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_secret)
):
    """Get users who have at least one connected job portal."""
    from backend.models import JobPortalSession
    
    users = db.query(User).join(JobPortalSession).filter(
        JobPortalSession.status == 'connected'
    ).distinct().all()
    
    return [
        {
            'id': u.id,
            'email': u.email,
            'plan': u.subscription.plan if u.subscription else 'free',
            'connected_platforms': [
                s.platform for s in u.job_portal_sessions 
                if s.status == 'connected'
            ]
        }
        for u in users
    ]