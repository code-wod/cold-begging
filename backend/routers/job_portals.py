from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User, JobPortalSession
from backend.security import get_current_user
from backend.browser.session import get_session_manager
from backend.browser.queue import get_task_queue, TaskQueue, Task, TaskType
from backend.providers import provider_registry
from backend.providers.base import PortalCapabilities

router = APIRouter(prefix='/api/job-portals', tags=['job-portals'])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PortalStatusResponse(BaseModel):
    platform: str
    status: str
    last_verified: Optional[str] = None
    login_url: Optional[str] = None
    home_url: Optional[str] = None
    capabilities: dict = {}


class ConnectRequest(BaseModel):
    headless: bool = False


class TaskResponse(BaseModel):
    id: str
    type: str
    user_id: int
    platform: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str


class QueueStatsResponse(BaseModel):
    pending: int
    processing: int
    completed: int


@router.get('', response_model=List[PortalStatusResponse])
async def list_job_portals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all supported job portals with connection status."""
    session_manager = get_session_manager()
    sessions = await session_manager.get_all_sessions(current_user.id)
    
    portals = []
    for session in sessions:
        provider = provider_registry.get(session.platform)
        caps = provider.get_capabilities() if provider else PortalCapabilities()
        
        portals.append(PortalStatusResponse(
            platform=session.platform,
            status=session.status,
            last_verified=session.last_verified,
            login_url=session.login_url,
            home_url=session.home_url,
            capabilities={cap: getattr(caps, cap) for cap in [
                'job_search', 'easy_apply', 'one_click_apply', 
                'multi_step_form', 'resume_upload', 'cover_letter',
                'screening_questions', 'external_redirect'
            ]}
        ))
    
    return portals


@router.get('/{platform}/status', response_model=PortalStatusResponse)
async def get_portal_status(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get connection status for a specific platform."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')
    
    session_manager = get_session_manager()
    session = await session_manager.get_session_info(current_user.id, platform)
    
    caps = provider.get_capabilities()
    
    return PortalStatusResponse(
        platform=session.platform,
        status=session.status,
        last_verified=session.last_verified,
        login_url=session.login_url,
        home_url=session.home_url,
        capabilities={cap: getattr(caps, cap) for cap in [
            'job_search', 'easy_apply', 'one_click_apply',
            'multi_step_form', 'resume_upload', 'cover_letter',
            'screening_questions', 'external_redirect'
        ]}
    )


@router.post('/{platform}/connect', response_model=TaskResponse)
async def connect_portal(
    platform: str,
    request: ConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect to a job portal (launch browser for login if needed)."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')
    
    task_queue = get_task_queue()
    
    task = Task(
        type=TaskType.ENSURE_LOGIN.value,
        user_id=current_user.id,
        platform=platform,
        payload={'headless': request.headless}
    )
    
    await task_queue.enqueue(task)
    
    return TaskResponse(
        id=task.id,
        type=task.type,
        user_id=task.user_id,
        platform=task.platform,
        status=task.status,
        created_at=task.created_at
    )


@router.post('/{platform}/verify', response_model=TaskResponse)
async def verify_portal_session(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify if portal session is still valid."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')
    
    task_queue = get_task_queue()
    
    task = Task(
        type=TaskType.VERIFY_SESSION.value,
        user_id=current_user.id,
        platform=platform,
        payload={}
    )
    
    await task_queue.enqueue(task)
    
    return TaskResponse(
        id=task.id,
        type=task.type,
        user_id=task.user_id,
        platform=task.platform,
        status=task.status,
        created_at=task.created_at
    )


@router.post('/{platform}/disconnect', response_model=TaskResponse)
async def disconnect_portal(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect from a job portal (clear session)."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')
    
    task_queue = get_task_queue()
    
    task = Task(
        type=TaskType.DISCONNECT.value,
        user_id=current_user.id,
        platform=platform,
        payload={}
    )
    
    await task_queue.enqueue(task)
    
    return TaskResponse(
        id=task.id,
        type=task.type,
        user_id=task.user_id,
        platform=task.platform,
        status=task.status,
        created_at=task.created_at
    )


@router.get('/{platform}/open')
async def open_portal_browser(
    platform: str,
    url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Open a managed browser page for the portal."""
    from backend.browser.session import get_session_manager
    
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')
    
    session_manager = get_session_manager()
    
    try:
        page = await session_manager.open_managed_browser(current_user.id, platform, url)
        current_url = page.url
        await page.close()
        return {'url': current_url, 'message': 'Browser opened successfully'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to open browser: {str(e)}')


@router.get('/capabilities')
async def list_platform_capabilities():
    """Get capabilities for all supported platforms."""
    result = {}
    for name in provider_registry.get_names():
        provider = provider_registry.get(name)
        if provider:
            caps = provider.get_capabilities()
            result[name] = {cap: getattr(caps, cap) for cap in [
                'job_search', 'easy_apply', 'one_click_apply',
                'multi_step_form', 'resume_upload', 'cover_letter',
                'screening_questions', 'external_redirect'
            ]}
    return result