from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.database import SessionLocal
from backend.models import User, JobPortalSession
from backend.security import get_current_user
from backend.browser.session import get_session_manager
from backend.browser.queue import get_task_queue, TaskQueue, Task, TaskType
from backend.browser.pool import get_worker_pool
from backend.providers import provider_registry
from backend.providers.base import SearchConfig, CandidateProfile

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
    action: str  # start, pause, resume, stop
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
    """Get agent status and statistics."""
    from backend.config import DEFAULT_DAILY_APPLICATION_LIMIT, DEFAULT_MIN_MATCH_SCORE, DRY_RUN
    from backend.models import Application
    
    # Get daily application count
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_used = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.created_at >= today_start
    ).count()
    
    # Get worker pool stats
    worker_pool = await get_worker_pool()
    pool_stats = await worker_pool.get_stats()
    
    # Get queue stats
    task_queue = get_task_queue()
    queue_stats = await task_queue.get_queue_stats()
    
    return AgentStatusResponse(
        running=False,  # TODO: track agent running state
        daily_limit=DEFAULT_DAILY_APPLICATION_LIMIT,
        daily_used=daily_used,
        min_match_score=DEFAULT_MIN_MATCH_SCORE,
        dry_run=True,  # from config
        workers=pool_stats['total_workers'],
        queue_stats=queue_stats
    )


@router.post('/control')
async def control_agent(
    request: AgentControlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Control the job application agent (start/pause/resume/stop)."""
    # TODO: Implement agent state management
    return {'message': f'Agent {request.action} requested', 'action': request.action}


@router.post('/search', response_model=List[dict])
async def search_jobs(
    request: SearchJobsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for jobs across connected platforms."""
    from backend.browser.session import get_session_manager
    from backend.providers import provider_registry
    
    if not request.platforms:
        # Use all connected platforms
        session_manager = get_session_manager()
        sessions = await session_manager.get_all_sessions(current_user.id)
        request.platforms = [s.platform for s in sessions if s.status == 'connected']
    
    if not request.platforms:
        raise HTTPException(status_code=400, detail='No connected platforms. Connect at least one job portal first.')
    
    results = {}
    session_manager = get_session_manager()
    
    for platform in request.platforms:
        provider = provider_registry.get(platform)
        if not provider:
            results[platform] = {'error': 'Platform not supported'}
            continue
        
        # Check session
        session = await session_manager.get_session_info(current_user.id, platform)
        if session.status != 'connected':
            results[platform] = {'error': 'Platform not connected'}
            continue
        
        # Create search task
        task_queue = get_task_queue()
        task = Task(
            type='search_jobs',
            user_id=current_user.id,
            platform=platform,
            payload={
                'keywords': request.keywords,
                'locations': request.locations,
                'experience_min': request.experience_min,
                'experience_max': request.experience_max,
                'remote': request.remote,
                'job_types': request.job_types,
                'salary_min': request.salary_min,
                'max_results': request.max_results,
            }
        )
        
        await task_queue.enqueue(task)
        results[platform] = {'task_id': task.id, 'status': 'queued'}
    
    return results


@router.get('/tasks/{task_id}', response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of a background task."""
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
    """Get recent agent activity logs."""
    # TODO: Implement proper logging storage
    return {'logs': [], 'message': 'Logging not yet implemented'}


@router.get('/queue/stats')
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get task queue statistics."""
    task_queue = get_task_queue()
    stats = await task_queue.get_queue_stats()
    return stats


@router.post('/queue/cleanup')
async def cleanup_stale_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clean up stale tasks in the queue."""
    task_queue = get_task_queue()
    cleaned = await task_queue.cleanup_stale_tasks()
    return {'cleaned': cleaned}