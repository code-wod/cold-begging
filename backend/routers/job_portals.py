from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.database import SessionLocal
from backend.models import User, JobPortalSession
from backend.security import get_current_user
from backend.browser.session import get_session_manager
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
    email: Optional[str] = None
    password: Optional[str] = None


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


@router.post('/{platform}/connect')
async def connect_portal(
    platform: str,
    request: ConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect to a job portal. Executes login directly, then auto-searches jobs."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')

    session_manager = get_session_manager()

    # Build credentials dict
    credentials = None
    if request.email and request.password:
        credentials = {'email': request.email, 'password': request.password}

    try:
        success = await session_manager.ensure_login(
            current_user.id,
            platform,
            headless=request.headless,
            credentials=credentials
        )

        if success:
            # Trigger auto-search + apply in background
            from backend.routers.agent import _auto_search_and_apply
            from backend.models import JobPreferences, Resume
            import json as _json

            prefs = db.query(JobPreferences).filter(JobPreferences.user_id == current_user.id).first()
            keywords = []
            locations = []
            if prefs:
                try:
                    keywords = _json.loads(prefs.preferred_roles) if prefs.preferred_roles else []
                except Exception:
                    pass
                try:
                    locations = _json.loads(prefs.preferred_locations) if prefs.preferred_locations else []
                except Exception:
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
                [platform],
                search_config,
            )

            return {
                'status': 'connected',
                'message': f'Successfully connected to {platform}. Auto-search started.',
                'platform': platform,
            }
        else:
            return {
                'status': 'login_required',
                'message': f'Login required for {platform}. Please complete login in the browser.',
                'platform': platform,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to connect: {str(e)}')


@router.post('/{platform}/verify')
async def verify_portal_session(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify if portal session is still valid."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')

    session_manager = get_session_manager()

    try:
        session_status = await session_manager.verify_session(current_user.id, platform)
        return {
            'status': session_status.value,
            'platform': platform,
            'message': f'Session status: {session_status.value}',
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Verification failed: {str(e)}')


@router.post('/{platform}/disconnect')
async def disconnect_portal(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect from a job portal (clear session)."""
    provider = provider_registry.get(platform)
    if not provider:
        raise HTTPException(status_code=404, detail=f'Platform not supported: {platform}')

    session_manager = get_session_manager()

    try:
        success = await session_manager.disconnect(current_user.id, platform)
        return {
            'status': 'disconnected' if success else 'error',
            'platform': platform,
            'message': f'Disconnected from {platform}' if success else 'Failed to disconnect',
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Disconnect failed: {str(e)}')


@router.get('/{platform}/open')
async def open_portal_browser(
    platform: str,
    url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Open a managed browser page for the portal."""
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
