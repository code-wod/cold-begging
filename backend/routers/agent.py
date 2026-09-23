import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.database import SessionLocal
from backend.models import User, JobPortalSession, JobPreferences, Resume, Application
from backend.security import get_current_user
from backend.browser.session import get_session_manager, SessionStatus
from backend.browser.queue import get_task_queue, TaskQueue, Task, TaskType
from backend.providers import provider_registry
from backend.providers.base import SearchConfig, CandidateProfile

logger = logging.getLogger('agent')

router = APIRouter(prefix='/api/agent', tags=['agent'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AgentStatusResponse(BaseModel):
    running: bool
    daily_limit: int
    daily_used: int
    min_match_score: int
    dry_run: bool
    workers: int
    queue_stats: dict


class AgentControlRequest(BaseModel):
    action: str
    config: Optional[dict] = None


class SearchJobsRequest(BaseModel):
    platforms: List[str] = []
    keywords: List[str] = []
    locations: List[str] = []
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    remote: bool = False
    job_types: List[str] = []
    salary_min: Optional[int] = None
    max_results: int = 50


class TaskResponse(BaseModel):
    id: str
    type: str
    user_id: int
    platform: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str


@router.get('/status', response_model=AgentStatusResponse)
async def get_agent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.config import DEFAULT_DAILY_APPLICATION_LIMIT, DEFAULT_MIN_MATCH_SCORE, DRY_RUN
    from backend.models import Application

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_used = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.created_at >= today_start
    ).count()

    task_queue = get_task_queue()
    try:
        queue_stats = await task_queue.get_queue_stats()
    except Exception:
        queue_stats = {'pending': 0, 'processing': 0, 'completed': 0}

    return AgentStatusResponse(
        running=False,
        daily_limit=DEFAULT_DAILY_APPLICATION_LIMIT,
        daily_used=daily_used,
        min_match_score=DEFAULT_MIN_MATCH_SCORE,
        dry_run=DRY_RUN,
        workers=0,
        queue_stats=queue_stats
    )


@router.post('/control')
async def control_agent(
    request: AgentControlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {'message': f'Agent {request.action} requested', 'action': request.action}


@router.post('/search')
async def search_jobs(
    request: SearchJobsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for jobs across connected platforms. Executes directly if possible."""
    session_manager = get_session_manager()

    if not request.platforms:
        sessions = await session_manager.get_all_sessions(current_user.id)
        request.platforms = [s.platform for s in sessions if s.status == 'connected']

    if not request.platforms:
        raise HTTPException(status_code=400, detail='No connected platforms. Connect at least one job portal first.')

    results = {}

    for platform in request.platforms:
        provider = provider_registry.get(platform)
        if not provider:
            results[platform] = {'error': 'Platform not supported'}
            continue

        session = await session_manager.get_session_info(current_user.id, platform)
        if session.status != 'connected':
            results[platform] = {'error': 'Platform not connected'}
            continue

        # Execute search directly in-process
        try:
            search_config = SearchConfig(
                keywords=request.keywords,
                locations=request.locations,
                remote=request.remote,
                job_types=request.job_types,
                salary_min=request.salary_min,
                max_results=request.max_results,
            )

            from backend.database import SessionLocal
            from backend.services.job_service import JobService
            from backend.services.matching_service import MatchingService
            from backend.models import Application

            svc_db = SessionLocal()
            try:
                job_service = JobService(svc_db)
                matching_service = MatchingService(svc_db)

                async with session_manager._browser_manager.persistent_context(current_user.id, platform) as context:
                    page = await context.new_page()
                    try:
                        listings = await provider.search_jobs(page, search_config)
                        total_jobs = len(listings)
                        jobs_created = 0
                        matches = 0

                        for listing in listings:
                            job = job_service.create_job(listing, platform)
                            jobs_created += 1

                            existing_app = svc_db.query(Application).filter(
                                Application.user_id == current_user.id,
                                Application.job_id == job.id
                            ).first()
                            if existing_app:
                                continue

                            match_result = matching_service.match_job(current_user, job)
                            if match_result.get('match_score', 0) >= 70:
                                matches += 1

                        results[platform] = {
                            'status': 'completed',
                            'jobs_found': total_jobs,
                            'jobs_created': jobs_created,
                            'matches': matches,
                        }
                    finally:
                        await page.close()
            finally:
                svc_db.close()

        except Exception as e:
            results[platform] = {'error': str(e)}

    return results


@router.get('/tasks/{task_id}', response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_queue = get_task_queue()
    task = await task_queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail='Task not found')

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not your task')

    return TaskResponse(
        id=task.id,
        type=task.type,
        user_id=task.user_id,
        platform=task.platform,
        status=task.status,
        result=task.result,
        error=task.error,
        created_at=task.created_at
    )


@router.get('/logs')
async def get_agent_logs(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {'logs': [], 'message': 'Logging not yet implemented'}


@router.get('/queue/stats')
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_queue = get_task_queue()
    try:
        stats = await task_queue.get_queue_stats()
    except Exception:
        stats = {'pending': 0, 'processing': 0, 'completed': 0}
    return stats


@router.post('/queue/cleanup')
async def cleanup_stale_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_queue = get_task_queue()
    try:
        cleaned = await task_queue.cleanup_stale_tasks()
    except Exception:
        cleaned = 0
    return {'cleaned': cleaned}


@router.post('/search-auto')
async def search_and_apply(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-search connected platforms using user's job preferences and prepare applications."""
    session_manager = get_session_manager()
    sessions = await session_manager.get_all_sessions(current_user.id)
    connected = [s.platform for s in sessions if s.status == 'connected']

    if not connected:
        raise HTTPException(status_code=400, detail='No connected platforms.')

    # Read user preferences
    prefs = db.query(JobPreferences).filter(JobPreferences.user_id == current_user.id).first()
    default_resume = db.query(Resume).filter(
        Resume.user_id == current_user.id, Resume.is_default.is_(True)
    ).first()

    keywords = []
    locations = []
    if prefs:
        try:
            keywords = json.loads(prefs.preferred_roles) if prefs.preferred_roles else []
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            locations = json.loads(prefs.preferred_locations) if prefs.preferred_locations else []
        except (json.JSONDecodeError, TypeError):
            pass

    search_config = {
        'keywords': keywords,
        'locations': locations,
        'remote': prefs.remote_preference == 'any' if prefs else True,
        'salary_min': int(prefs.minimum_salary) if prefs and prefs.minimum_salary else None,
        'max_results': 30,
    }

    background_tasks.add_task(
        _auto_search_and_apply,
        current_user.id,
        connected,
        search_config,
    )

    return {
        'status': 'started',
        'platforms': connected,
        'keywords': keywords,
        'locations': locations,
        'message': f'Auto-search started on {len(connected)} platform(s). Results will appear in Applications.',
    }


async def _auto_search_and_apply(user_id: int, platforms: list, search_config: dict):
    """Background task: search → match → prepare → (optionally) apply."""
    import hashlib
    from backend.config import DRY_RUN, DEFAULT_MIN_MATCH_SCORE
    from backend.services.matching_service import MatchingService
    from backend.services.application_service import ApplicationService

    session_manager = get_session_manager()
    svc_db = SessionLocal()
    try:
        user = svc_db.query(User).filter(User.id == user_id).first()
        if not user:
            return

        matching_service = MatchingService(svc_db)
        application_service = ApplicationService(svc_db)

        logger.info('Auto-search: user=%d, platforms=%s, DRY_RUN=%s, keywords=%s, locations=%s',
                     user_id, platforms, DRY_RUN, search_config.get('keywords'), search_config.get('locations'))

        for platform in platforms:
            provider = provider_registry.get(platform)
            if not provider:
                continue

            logger.info('Auto-search starting for user %d on %s', user_id, platform)

            try:
                # Verify login first — skip if not authenticated
                status = await session_manager.verify_session(user_id, platform)
                if status != SessionStatus.CONNECTED:
                    logger.warning('Skipping %s for user %d — not connected (status=%s)', platform, user_id, status)
                    continue

                async with session_manager._browser_manager.persistent_context(user_id, platform) as context:
                    # Use existing pages[0] instead of new_page() to avoid opening a second tab
                    pages = context.pages
                    page = pages[0] if pages else await context.new_page()
                    try:
                        sc = SearchConfig(
                            keywords=search_config.get('keywords', []),
                            locations=search_config.get('locations', []),
                            remote=search_config.get('remote', False),
                            salary_min=search_config.get('salary_min'),
                            max_results=search_config.get('max_results', 30),
                        )
                        listings = await provider.search_jobs(page, sc)
                        logger.info('Found %d jobs on %s for user %d', len(listings), platform, user_id)

                        created = 0
                        matched = 0
                        applied = 0

                        for listing in listings:
                            # Create Job directly from JobCard (bypass source_providers registry)
                            job_hash = hashlib.sha256(
                                f'{platform}:{listing.title}:{listing.company}:{listing.location or ""}'.encode()
                            ).hexdigest()

                            existing_job = svc_db.query(Job).filter(Job.job_hash == job_hash).first()
                            if existing_job:
                                job = existing_job
                            else:
                                job = Job(
                                    source=platform,
                                    external_id=listing.external_id,
                                    title=listing.title,
                                    company_name=listing.company or 'Unknown',
                                    location=listing.location or '',
                                    application_url=listing.url,
                                    job_hash=job_hash,
                                    source_data=json.dumps(getattr(listing, 'metadata', {})),
                                    status='active',
                                )
                                svc_db.add(job)
                                svc_db.flush()
                                created += 1

                            # Skip if user already has an application for this job
                            existing = svc_db.query(Application).filter(
                                Application.user_id == user_id,
                                Application.job_id == job.id
                            ).first()
                            if existing:
                                continue

                            # Match against user profile
                            match_result = matching_service.match_job(user, job)
                            score = match_result.get('match_score', 0)
                            logger.info('Job %d "%s" match_score=%d (threshold=%d)', job.id, job.title[:50], score, DEFAULT_MIN_MATCH_SCORE)
                            if score < DEFAULT_MIN_MATCH_SCORE:
                                logger.debug('Job %d score %d below threshold, skipping', job.id, score)
                                continue

                            matched += 1
                            try:
                                package = matching_service.prepare_application(user, job, match_result)
                            except Exception as e:
                                logger.warning('Failed to prepare application for job %d: %s', job.id, e)
                                continue

                            app = application_service.create_application(user, job, match_result, package)

                            # Auto-apply if score >= 80 and not DRY_RUN
                            logger.info('Job %d: DRY_RUN=%s, score=%d, will_apply=%s', job.id, DRY_RUN, score, not DRY_RUN and score >= 80)
                            if not DRY_RUN and score >= 80:
                                try:
                                    if listing.url:
                                        await page.goto(listing.url, wait_until='domcontentloaded', timeout=30000)
                                        await page.wait_for_timeout(3000)

                                    provider_result = await provider.submit_application(page)
                                    if provider_result and provider_result.success:
                                        app.status = 'applied'
                                        app.applied_at = datetime.now(timezone.utc)
                                        applied += 1
                                        logger.info('Auto-applied to job %d on %s', job.id, platform)
                                except Exception as e:
                                    logger.warning('Auto-apply failed for job %d: %s', job.id, e)

                            svc_db.commit()

                        logger.info(
                            'Auto-search done for user %d on %s: %d found, %d matched, %d applied',
                            user_id, platform, created, matched, applied,
                        )
                    finally:
                        await page.close()
            except Exception as e:
                logger.error('Auto-search failed for user %d on %s: %s', user_id, platform, e)
    finally:
        svc_db.close()
