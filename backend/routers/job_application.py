import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.security import get_current_user
from backend.models import User
from backend.schemas import (
    JobProfileIn, JobProfileOut,
    AutofillApplicationCreate, AutofillApplicationOut, AutofillFieldOut, AutofillFieldUpdate,
    AutofillSubmitRequest,
)
from backend.services.job_profile_service import JobProfileService, AutofillApplicationService

logger = logging.getLogger('job_application_router')

router = APIRouter(prefix='/api/job-applications', tags=['job-applications'])


def _app_out(app) -> AutofillApplicationOut:
    """Convert model instance to schema, serializing datetimes to strings."""
    d = {
        'id': app.id,
        'user_id': app.user_id,
        'job_url': app.job_url,
        'company_name': app.company_name or '',
        'role_title': app.role_title or '',
        'ats_platform': app.ats_platform or '',
        'status': app.status or 'preparing',
        'total_fields': app.total_fields or 0,
        'auto_filled': app.auto_filled or 0,
        'needs_review': app.needs_review or 0,
        'unanswered': app.unanswered or 0,
        'error_code': app.error_code or '',
        'error_message': app.error_message or '',
        'requires_user_action': app.requires_user_action or '',
        'screenshot_path': app.screenshot_path or '',
        'resume_id': app.resume_id,
        'created_at': app.created_at.isoformat() if app.created_at else None,
        'updated_at': app.updated_at.isoformat() if app.updated_at else None,
        'submitted_at': app.submitted_at.isoformat() if app.submitted_at else None,
    }
    return AutofillApplicationOut(**d)


# ── Job Profile ──────────────────────────────────────────────────────────────

@router.get('/profile', response_model=JobProfileOut)
def get_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = JobProfileService(db)
    profile = svc.get_or_create(user.id)
    return JobProfileOut(**profile.to_dict())


@router.put('/profile', response_model=JobProfileOut)
def update_profile(
    data: JobProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = JobProfileService(db)
    profile = svc.update(user.id, data.model_dump())
    return JobProfileOut(**profile.to_dict())


# ── Applications ─────────────────────────────────────────────────────────────

@router.post('', response_model=AutofillApplicationOut)
def create_application(
    data: AutofillApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new autofill application from a job URL."""
    if not data.job_url.strip():
        raise HTTPException(status_code=400, detail='Job URL is required')

    url = data.job_url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    svc = AutofillApplicationService(db)
    app = svc.create(user.id, url, data.resume_id)
    return _app_out(app)


@router.post('/extract-fields')
async def extract_fields_from_url(
    data: AutofillApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extract form fields from a job URL using Playwright (for side-by-side UI)."""
    if not data.job_url.strip():
        raise HTTPException(status_code=400, detail='Job URL is required')

    url = data.job_url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    from backend.ats.detector import detect_ats, get_adapter
    from backend.ats.field_extractor import extract_fields
    from backend.browser.worker import get_browser_manager
    from backend.services.job_profile_service import JobProfileService
    from backend.ats.field_mapper import map_fields

    profile_svc = JobProfileService(db)
    profile = profile_svc.get_or_create(user.id)
    profile_dict = profile.to_dict()

    browser_mgr = get_browser_manager()
    try:
        async with browser_mgr.ephemeral_context() as context:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                # Get page info
                title = await page.title()
                company = ''
                role = ''
                if title:
                    parts = title.split(' - ') if ' - ' in title else title.split(' | ')
                    if len(parts) >= 2:
                        role = parts[0].strip()
                        company = parts[-1].strip()
                    elif title:
                        role = title.strip()

                # Detect ATS
                ats_platform = await detect_ats(url, page)
                adapter = get_adapter(ats_platform)

                # Extract fields
                if adapter:
                    fields_data = await adapter.extract_fields(page)
                else:
                    fields_data = await extract_fields(page, ats_platform)

                # Map to profile
                mapped_fields = map_fields(fields_data, profile_dict)

                # Try to get a screenshot
                import os, tempfile
                screenshot_b64 = None
                try:
                    screenshot_bytes = await page.screenshot(full_page=False)
                    import base64
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                except Exception:
                    pass

                return {
                    'success': True,
                    'ats_platform': ats_platform,
                    'company_name': company,
                    'role_title': role,
                    'fields': mapped_fields,
                    'screenshot': screenshot_b64,
                }
            finally:
                await page.close()
    except Exception as e:
        logger.error('Extract fields error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/auto-fill')
async def auto_fill(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Open page in Playwright, auto-fill ALL steps from profile, return results.

    This is the simple one-click approach: paste URL, we fill everything we can,
    navigate through steps, and return the final state.
    """
    job_url = data.get('job_url', '')
    if not job_url:
        raise HTTPException(status_code=400, detail='job_url is required')

    from backend.ats.detector import detect_ats, get_adapter
    from backend.ats.field_extractor import extract_fields
    from backend.ats.field_mapper import map_fields
    from backend.browser.worker import get_browser_manager
    from backend.services.job_profile_service import JobProfileService

    profile_svc = JobProfileService(db)
    profile = profile_svc.get_or_create(user.id)
    profile_dict = profile.to_dict() if profile else {}

    browser_mgr = get_browser_manager()
    all_steps = []

    try:
        async with browser_mgr.ephemeral_context() as context:
            page = await context.new_page()
            try:
                await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                # Detect ATS
                ats_platform = await detect_ats(job_url, page)
                adapter = get_adapter(ats_platform)
                title = await page.title()

                max_steps = 10
                for step_num in range(1, max_steps + 1):
                    # Extract fields on current page
                    if adapter:
                        fields_data = await adapter.extract_fields(page)
                    else:
                        fields_data = await extract_fields(page, ats_platform)

                    # Map to profile
                    mapped = map_fields(fields_data, profile_dict)

                    # Auto-fill high confidence fields
                    filled = 0
                    for f in mapped:
                        val = f.get('user_value') or f.get('mapped_value', '')
                        conf = f.get('confidence', 0)
                        if val and conf >= 0.7 and f.get('field_type') != 'file' and adapter:
                            try:
                                ok = await adapter.fill_field(page, f, val)
                                if ok:
                                    f['status'] = 'filled'
                                    filled += 1
                            except Exception:
                                pass

                    # Upload resume if we have one
                    if adapter and step_num == 1:
                        try:
                            from backend.models import Resume
                            resume = db.query(Resume).filter(Resume.user_id == user.id).first()
                            if resume and resume.stored_path and os.path.exists(resume.stored_path):
                                await adapter.upload_resume(page, resume.stored_path)
                        except Exception:
                            pass

                    # Take screenshot
                    import base64
                    screenshot_b64 = ''
                    try:
                        ss = await page.screenshot(full_page=False)
                        screenshot_b64 = base64.b64encode(ss).decode('utf-8')
                    except Exception:
                        pass

                    # Check for CAPTCHA/login
                    page_html = await page.content()
                    page_lower = page_html.lower()
                    blocked = 'captcha' in page_lower or 'recaptcha' in page_lower

                    step_info = {
                        'step': step_num,
                        'fields': mapped,
                        'total_fields': len(mapped),
                        'filled': filled,
                        'screenshot': screenshot_b64,
                        'blocked': blocked,
                    }
                    all_steps.append(step_info)

                    # If blocked or no fields, stop
                    if blocked or len(mapped) == 0:
                        break

                    # Try to click Next/Continue
                    if adapter:
                        try:
                            result = await adapter.handle_multi_step(page, max_steps=1)
                            if result.get('steps_completed', 0) == 0:
                                break
                        except Exception:
                            break
                    else:
                        # Generic next button click
                        clicked = await page.evaluate('''() => {
                            const btns = document.querySelectorAll('button, a, [role="button"]');
                            for (const b of btns) {
                                if (b.offsetParent === null) continue;
                                const t = b.textContent.trim().toLowerCase();
                                if (t.includes('next') || t.includes('continue')) {
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        if not clicked:
                            break
                        await page.wait_for_timeout(3000)

                    await page.wait_for_timeout(1000)

            finally:
                await page.close()

    except Exception as e:
        logger.error('Auto-fill error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))

    total_filled = sum(s['filled'] for s in all_steps)
    total_fields = sum(s['total_fields'] for s in all_steps)

    return {
        'success': True,
        'ats_platform': ats_platform if all_steps else 'unknown',
        'total_steps': len(all_steps),
        'total_fields': total_fields,
        'total_filled': total_filled,
        'steps': [{k: v for k, v in s.items() if k != 'screenshot'} for s in all_steps],
        'screenshots': [s['screenshot'] for s in all_steps if s['screenshot']],
    }


@router.post('/save-and-fill')
async def save_and_fill(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save mapped fields and fill the actual form via Playwright."""
    job_url = data.get('job_url', '')
    fields = data.get('fields', [])
    resume_id = data.get('resume_id')

    if not job_url:
        raise HTTPException(status_code=400, detail='job_url is required')

    # Create application
    svc = AutofillApplicationService(db)
    app = svc.create(user.id, job_url, resume_id)

    # Store fields
    svc.set_fields(app.id, fields)

    # Update stats
    stats = svc.get_stats(app.id)
    new_status = 'needs_review' if stats['needs_review'] > 0 else 'ready'
    svc.update_status(app.id, user.id, new_status,
        total_fields=stats['total_fields'],
        auto_filled=stats['auto_filled'],
        needs_review=stats['needs_review'],
        unanswered=stats['unanswered'])

    return _app_out(app)


@router.post('/fill-remote')
async def fill_remote(
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fill a form on a remote page via Playwright and return updated screenshot."""
    job_url = data.get('job_url', '')
    fields = data.get('fields', [])

    if not job_url:
        raise HTTPException(status_code=400, detail='job_url is required')

    from backend.ats.detector import detect_ats, get_adapter
    from backend.browser.worker import get_browser_manager

    browser_mgr = get_browser_manager()
    try:
        async with browser_mgr.ephemeral_context() as context:
            page = await context.new_page()
            try:
                await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                ats_platform = await detect_ats(job_url, page)
                adapter = get_adapter(ats_platform)

                filled_count = 0
                if adapter:
                    for f in fields:
                        val = f.get('user_value') or f.get('mapped_value', '')
                        conf = f.get('confidence', 0)
                        if val and conf >= 0.7 and f.get('field_type') != 'file':
                            try:
                                success = await adapter.fill_field(page, f, val)
                                if success:
                                    filled_count += 1
                            except Exception:
                                pass

                # Take screenshot
                import base64
                screenshot_b64 = None
                try:
                    screenshot_bytes = await page.screenshot(full_page=False)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                except Exception:
                    pass

                return {
                    'success': True,
                    'filled_count': filled_count,
                    'screenshot': screenshot_b64,
                }
            finally:
                await page.close()
    except Exception as e:
        logger.error('Fill remote error: %s', e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('', response_model=dict)
def list_applications(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = AutofillApplicationService(db)
    result = svc.list_user_applications(user.id, status=status, limit=limit, offset=offset)
    return {
        'items': [_app_out(a) for a in result['items']],
        'total': result['total'],
    }


@router.get('/{application_id}', response_model=AutofillApplicationOut)
def get_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    return _app_out(app)


@router.get('/{application_id}/fields', response_model=list[AutofillFieldOut])
def get_application_fields(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    fields = svc.get_fields(application_id)
    return [AutofillFieldOut.model_validate(f) for f in fields]


@router.patch('/{application_id}/fields/{field_id}', response_model=AutofillFieldOut)
def update_field(
    application_id: int,
    field_id: int,
    data: AutofillFieldUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    field = svc.update_field(field_id, application_id, user_value=data.user_value, skipped=data.skipped)
    if not field:
        raise HTTPException(status_code=404, detail='Field not found')
    return AutofillFieldOut.model_validate(field)


@router.post('/{application_id}/start')
def start_autofill(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enqueue the autofill task for browser processing."""
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    if app.status not in ('preparing', 'failed'):
        raise HTTPException(status_code=400, detail=f'Cannot start application in status: {app.status}')

    # Update status to analyzing
    svc.update_status(application_id, user.id, 'analyzing')

    # Enqueue browser task
    try:
        from backend.browser.queue import Task, TaskType, get_task_queue
        task = Task(
            type=TaskType.AUTOFILL_APPLICATION.value,
            user_id=user.id,
            platform='autofill',
            payload={
                'application_id': application_id,
                'job_url': app.job_url,
                'resume_id': app.resume_id,
            },
        )
        queue = get_task_queue()
        queue.enqueue(task)
        svc.update_status(application_id, user.id, 'analyzing', task_id=task.id)
        return {'message': 'Autofill task queued', 'task_id': task.id, 'application_id': application_id}
    except Exception as e:
        logger.error('Failed to enqueue autofill task: %s', e)
        svc.update_status(application_id, user.id, 'failed', error_message=str(e))
        raise HTTPException(status_code=500, detail=f'Failed to start autofill: {e}')


@router.post('/{application_id}/validate')
def validate_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate that all required fields are filled."""
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')

    fields = svc.get_fields(application_id)
    missing = []
    for f in fields:
        if f.skipped:
            continue
        val = f.user_value or f.mapped_value
        if f.field_type == 'file':
            continue  # Files handled separately
        if not val and f.field_label.lower() not in ('divider', 'section', 'header'):
            missing.append({'id': f.id, 'label': f.field_label, 'type': f.field_type})

    stats = svc.get_stats(application_id)
    return {
        'valid': len(missing) == 0,
        'missing_fields': missing,
        'stats': stats,
    }


@router.post('/{application_id}/submit')
def submit_application(
    application_id: int,
    data: AutofillSubmitRequest = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit the application after user confirmation."""
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    if app.status not in ('ready', 'needs_review'):
        raise HTTPException(status_code=400, detail=f'Cannot submit application in status: {app.status}')

    if data and not data.confirmed:
        raise HTTPException(status_code=400, detail='Must confirm submission')

    # Update status to submitting
    svc.update_status(application_id, user.id, 'submitting')

    # Enqueue submission task
    try:
        from backend.browser.queue import Task, TaskType, get_task_queue
        task = Task(
            type=TaskType.SUBMIT_APPLICATION.value,
            user_id=user.id,
            platform='autofill',
            payload={
                'application_id': application_id,
                'job_url': app.job_url,
            },
        )
        queue = get_task_queue()
        queue.enqueue(task)
        return {'message': 'Submission queued', 'task_id': task.id}
    except Exception as e:
        logger.error('Failed to enqueue submit task: %s', e)
        svc.update_status(application_id, user.id, 'failed', error_message=str(e))
        raise HTTPException(status_code=500, detail=f'Failed to submit: {e}')


@router.post('/{application_id}/cancel')
def cancel_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    if app.status in ('submitted', 'cancelled'):
        raise HTTPException(status_code=400, detail=f'Cannot cancel application in status: {app.status}')

    svc.update_status(application_id, user.id, 'cancelled')
    return {'message': 'Application cancelled'}


@router.get('/{application_id}/screenshot')
def get_screenshot(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the screenshot of the application page."""
    from fastapi.responses import FileResponse
    import os

    svc = AutofillApplicationService(db)
    app = svc.get(application_id, user.id)
    if not app:
        raise HTTPException(status_code=404, detail='Application not found')
    if not app.screenshot_path or not os.path.exists(app.screenshot_path):
        raise HTTPException(status_code=404, detail='No screenshot available')
    return FileResponse(app.screenshot_path, media_type='image/png')


@router.get('/history', response_model=List[AutofillApplicationOut])
def get_application_history(
    status: str = None,
    ats_platform: str = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get application history with optional filters."""
    from backend.models_job_application import AutofillApplication
    from backend.models import User as UserModel

    q = db.query(AutofillApplication).filter(AutofillApplication.user_id == user.id)
    if status:
        q = q.filter(AutofillApplication.status == status)
    if ats_platform:
        q = q.filter(AutofillApplication.ats_platform == ats_platform)

    apps = q.order_by(AutofillApplication.created_at.desc()).offset(offset).limit(limit).all()
    return [_app_out(a) for a in apps]


@router.post('/cleanup')
def cleanup_old_applications(
    max_age_days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clean up old completed applications and their files."""
    from backend.models_job_application import AutofillApplication
    import datetime as dt
    import os
    from backend.config import AUTOFILL_UPLOAD_DIR

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)
    old_apps = db.query(AutofillApplication).filter(
        AutofillApplication.user_id == user.id,
        AutofillApplication.status.in_(['submitted', 'cancelled', 'failed']),
        AutofillApplication.updated_at < cutoff,
    ).all()

    deleted = 0
    for app in old_apps:
        # Delete files
        if app.screenshot_path and os.path.exists(app.screenshot_path):
            try:
                os.remove(app.screenshot_path)
            except Exception:
                pass
        if app.resume_path and os.path.exists(app.resume_path):
            # Don't delete shared resume files
            pass

        # Delete field records
        from backend.models_job_application import AutofillField
        db.query(AutofillField).filter(AutofillField.application_id == app.id).delete()
        db.delete(app)
        deleted += 1

    db.commit()
    return {'deleted': deleted, 'cutoff_date': cutoff.isoformat()}


@router.get('/stats')
def get_application_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get aggregated application statistics."""
    from backend.models_job_application import AutofillApplication
    from sqlalchemy import func

    total = db.query(AutofillApplication).filter(AutofillApplication.user_id == user.id).count()
    by_status = db.query(
        AutofillApplication.status,
        func.count(AutofillApplication.id)
    ).filter(
        AutofillApplication.user_id == user.id
    ).group_by(AutofillApplication.status).all()

    by_platform = db.query(
        AutofillApplication.ats_platform,
        func.count(AutofillApplication.id)
    ).filter(
        AutofillApplication.user_id == user.id
    ).group_by(AutofillApplication.ats_platform).all()

    return {
        'total': total,
        'by_status': {s: c for s, c in by_status},
        'by_platform': {p: c for p, c in by_platform},
    }
