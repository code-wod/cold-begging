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
    return AutofillApplicationOut.model_validate(app)


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
        'items': [AutofillApplicationOut.model_validate(a) for a in result['items']],
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
    return AutofillApplicationOut.model_validate(app)


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
    return [AutofillApplicationOut.model_validate(a) for a in apps]


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
