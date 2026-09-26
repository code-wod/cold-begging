import asyncio
import logging
import uuid
from typing import Optional, List, Dict, Any
from enum import Enum

from backend.browser.queue import TaskQueue, get_task_queue, Task, TaskType, TaskStatus
from backend.browser.manager import get_browser_manager
from backend.browser.session import get_session_manager
from backend.providers import provider_registry
from backend.providers.base import SearchConfig, CandidateProfile
from backend.config import DRY_RUN

logger = logging.getLogger('browser_worker')


class TaskHandler:
    """Base class for task handlers."""

    async def handle(self, task: Task) -> Dict[str, Any]:
        raise NotImplementedError


class BrowserWorker:
    """Main browser worker that processes tasks from the queue."""

    def __init__(
        self,
        worker_id: str,
        task_queue,
        handlers: Dict[TaskType, TaskHandler],
        poll_interval: float = 5.0,
        max_concurrent: int = 1
    ):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.handlers = handlers
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def start(self):
        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        logger.info('BrowserWorker %s started', self.worker_id)

        while self._running:
            try:
                await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error('Worker %s error: %s', self.worker_id, e)

            await asyncio.sleep(self.poll_interval)

    async def _process_batch(self):
        if not self._semaphore:
            return

        available = self.max_concurrent - len(self._tasks)
        if available <= 0:
            return

        tasks = await self.task_queue.dequeue(self.worker_id, available)

        for task in tasks:
            if not self._running:
                break

            coro = self._execute_task(task)
            asyncio_task = asyncio.create_task(coro)
            self._tasks[task.id] = asyncio_task

            asyncio_task.add_done_callback(
                lambda t, tid=task.id: self._tasks.pop(tid, None)
            )

    async def _execute_task(self, task: Task):
        handler_type = TaskType(task.type)
        handler = self.handlers.get(handler_type)

        if not handler:
            logger.warning('No handler for task type: %s', task.type)
            await self.task_queue.complete_task(
                task.id,
                error=f'No handler for task type: {task.type}'
            )
            return

        logger.info('Worker %s executing task %s (%s)', self.worker_id, task.id, task.type)

        try:
            async with self._semaphore:
                result = await handler.handle(task)

            await self.task_queue.complete_task(task.id, result=result)
            logger.info('Worker %s completed task %s', self.worker_id, task.id)

        except asyncio.CancelledError:
            logger.info('Task %s cancelled', task.id)
            raise
        except Exception as e:
            logger.error('Worker %s task %s failed: %s', self.worker_id, task.id, e)
            await self.task_queue.complete_task(task.id, error=str(e))

    async def stop(self):
        self._running = False
        if self._tasks:
            logger.info('Worker %s waiting for %d tasks to complete', self.worker_id, len(self._tasks))
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks.values(), return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning('Worker %s timeout waiting for tasks', self.worker_id)
        logger.info('BrowserWorker %s stopped', self.worker_id)


def create_default_handlers() -> Dict[TaskType, TaskHandler]:
    """Create default task handlers using browser services."""

    class VerifySessionHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.user_id
            platform = task.platform
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            status = await session_manager.verify_session(user_id, platform)
            return {'status': status.value}

    class EnsureLoginHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.user_id
            platform = task.platform
            headless = task.payload.get('headless', False)
            credentials = task.payload.get('credentials')
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            success = await session_manager.ensure_login(user_id, platform, headless, credentials)
            return {'success': success}

    class DisconnectHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.user_id
            platform = task.platform
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            success = await session_manager.disconnect(user_id, platform)
            return {'success': success}

    class OpenBrowserHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.user_id
            platform = task.platform
            url = task.payload.get('url')
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            page = await session_manager.open_managed_browser(user_id, platform, url)
            current_url = page.url
            await page.close()
            return {'url': current_url}

    class SearchJobsHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            from backend.database import SessionLocal
            from backend.models import User, Application
            from backend.services.job_service import JobService
            from backend.services.matching_service import MatchingService

            user_id = task.user_id
            platform = task.platform
            search_config_data = task.payload.get('search_config', task.payload)

            if not user_id or not platform:
                return {'error': 'user_id and platform required'}

            provider = provider_registry.get(platform)
            if not provider or not provider.capabilities.job_search:
                return {'error': f'Platform {platform} does not support job search'}

            session_manager = get_session_manager()
            session = await session_manager.get_session_info(user_id, platform)
            if session.status != 'connected':
                return {'error': f'Not logged in to {platform}'}

            db = SessionLocal()
            try:
                job_service = JobService(db)
                matching_service = MatchingService(db)

                prefs = job_service.get_job_preferences(user_id)

                search_config = SearchConfig(
                    keywords=search_config_data.get('keywords', []),
                    locations=search_config_data.get('locations', []),
                    remote=search_config_data.get('remote', False),
                    job_types=search_config_data.get('job_types', []),
                    salary_min=search_config_data.get('salary_min'),
                    max_results=search_config_data.get('max_results', 50),
                )

                async with session_manager._browser_manager.persistent_context(user_id, platform) as context:
                    page = await context.new_page()
                    try:
                        listings = await provider.search_jobs(page, search_config)
                        total_jobs = len(listings)

                        jobs_created = 0
                        matches = 0
                        applications = 0

                        for listing in listings:
                            job = job_service.create_job(listing, platform)
                            jobs_created += 1

                            existing_app = db.query(Application).filter(
                                Application.user_id == user_id,
                                Application.job_id == job.id
                            ).first()
                            if existing_app:
                                continue

                            user = db.query(User).filter(User.id == user_id).first()
                            match_result = matching_service.match_job(user, job)

                            min_score = 70
                            if match_result.get('match_score', 0) >= min_score:
                                app = matching_service.prepare_application(user, job, match_result)
                                matches += 1

                        return {
                            'jobs_found': total_jobs,
                            'jobs_created': jobs_created,
                            'matches': matches,
                        }
                    finally:
                        await page.close()
            except Exception as e:
                logger.error('Error searching jobs on %s for user %d: %s', platform, user_id, e)
                return {'error': str(e)}
            finally:
                db.close()

    class ExtractJobHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            return {'error': 'ExtractJobHandler not yet implemented'}

    class AutofillHandler(TaskHandler):
        """Handles the full autofill flow: navigate, detect ATS, extract fields, map, fill."""
        async def handle(self, task: Task) -> Dict[str, Any]:
            from backend.database import SessionLocal
            from backend.services.job_profile_service import AutofillApplicationService
            from backend.services.job_profile_service import JobProfileService

            app_id = task.payload.get('application_id')
            job_url = task.payload.get('job_url')
            user_id = task.user_id
            resume_id = task.payload.get('resume_id')

            if not app_id or not job_url:
                return {'error': 'Missing application_id or job_url'}

            db = SessionLocal()
            try:
                svc = AutofillApplicationService(db)
                profile_svc = JobProfileService(db)
                app = svc.get(app_id, user_id)
                if not app:
                    return {'error': 'Application not found'}

                profile = profile_svc.get(user_id)
                if not profile:
                    svc.update_status(app_id, user_id, 'failed', error_message='No job profile found')
                    return {'error': 'No job profile found. Create one at /job-profile.'}

                svc.update_status(app_id, user_id, 'filling')

                from backend.ats.detector import detect_ats, get_adapter
                from backend.ats.field_mapper import map_fields
                from backend.config import AUTOFILL_UPLOAD_DIR

                import os
                os.makedirs(AUTOFILL_UPLOAD_DIR, exist_ok=True)

                browser_mgr = get_browser_manager()
                try:
                    async with browser_mgr.ephemeral_context() as context:
                        page = await context.new_page()
                        try:
                            await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
                            await page.wait_for_timeout(3000)

                            # Detect CAPTCHA / login required
                            page_html = await page.content()
                            page_lower = page_html.lower()
                            if 'captcha' in page_lower or 'recaptcha' in page_lower:
                                svc.update_status(app_id, user_id, 'failed',
                                    error_code='CAPTCHA_REQUIRED',
                                    error_message='CAPTCHA detected on the application page',
                                    requires_user_action='captcha_required')
                                return {'error': 'CAPTCHA required', 'requires_user_action': 'captcha_required'}

                            if 'sign in' in page_lower or 'log in' in page_lower:
                                if 'application' not in page_lower:
                                    svc.update_status(app_id, user_id, 'failed',
                                        error_code='LOGIN_REQUIRED',
                                        error_message='Login required to access the application',
                                        requires_user_action='login_required')
                                    return {'error': 'Login required', 'requires_user_action': 'login_required'}

                            # Detect ATS platform
                            ats_platform = detect_ats(job_url, page)
                            app.ats_platform = ats_platform

                            # Extract company/role from page title or URL
                            try:
                                title = await page.title()
                                if title:
                                    parts = title.split(' - ') if ' - ' in title else title.split(' | ')
                                    if len(parts) >= 2:
                                        app.role_title = parts[0].strip()
                                        app.company_name = parts[-1].strip()
                                    elif title:
                                        app.role_title = title.strip()
                            except Exception:
                                pass

                            db.commit()

                            # Get adapter
                            adapter = get_adapter(ats_platform)

                            # Extract fields using adapter or generic extractor
                            if adapter:
                                fields_data = await adapter.extract_fields(page)
                            else:
                                from backend.ats.field_extractor import extract_fields
                                fields_data = await extract_fields(page, ats_platform)

                            # Map fields to profile
                            profile_dict = profile.to_dict()
                            mapped_fields = map_fields(fields_data, profile_dict)

                            # AI field mapping for low-confidence fields
                            low_confidence = [f for f in mapped_fields if f.get('confidence', 1.0) < 0.7 and not f.get('user_value')]
                            if low_confidence:
                                try:
                                    from backend.config import GEMINI_API_KEY, OPENAI_API_KEY
                                    from backend.ats.ai_field_mapper import create_ai_mapper
                                    api_key = GEMINI_API_KEY or OPENAI_API_KEY
                                    provider = 'gemini' if GEMINI_API_KEY else 'openai'
                                    if api_key:
                                        mapper = create_ai_mapper(api_key=api_key, provider=provider)
                                        job_info = {'url': job_url, 'title': app.role_title, 'company': app.company_name}
                                        resume_text = ''
                                        if resume_id:
                                            from backend.models import Resume
                                            resume = db.query(Resume).filter(Resume.id == resume_id).first()
                                            if resume:
                                                resume_text = resume.extracted_text or ''
                                        mapped_fields = await mapper.map_fields(mapped_fields, profile_dict, job_info, resume_text)
                                except Exception as e:
                                    logger.warning('AI field mapping failed (falling back to deterministic): %s', e)

                            # Auto-fill high-confidence fields (>= 0.90) using the adapter
                            filled_count = 0
                            if adapter:
                                for mf in mapped_fields:
                                    confidence = mf.get('confidence', 0)
                                    mapped_val = mf.get('mapped_value', '')
                                    field_type = mf.get('field_type', 'text')
                                    requires_review = mf.get('requires_review', True)

                                    if confidence >= 0.90 and mapped_val and field_type != 'file' and not requires_review:
                                        try:
                                            success = await adapter.fill_field(page, mf, mapped_val)
                                            if success:
                                                mf['status'] = 'filled'
                                                filled_count += 1
                                        except Exception as e:
                                            logger.warning('Auto-fill failed for %s: %s', mf.get('field_label'), e)

                            # Try to upload resume if adapter supports it
                            if adapter and resume_id:
                                try:
                                    from backend.models import Resume
                                    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
                                    if resume and resume.stored_path and os.path.exists(resume.stored_path):
                                        await adapter.upload_resume(page, resume.stored_path)
                                        app.resume_path = resume.stored_path
                                except Exception as e:
                                    logger.warning('Resume upload failed: %s', e)

                            # Take screenshot for review
                            try:
                                screenshot_path = os.path.join(AUTOFILL_UPLOAD_DIR, f'app_{app_id}_review.png')
                                await page.screenshot(path=screenshot_path, full_page=False)
                                app.screenshot_path = screenshot_path
                            except Exception as e:
                                logger.warning('Screenshot failed: %s', e)

                            # Store fields
                            svc.set_fields(app_id, mapped_fields)

                            # Update stats
                            stats = svc.get_stats(app_id)
                            new_status = 'needs_review' if stats['needs_review'] > 0 else 'ready'
                            svc.update_status(app_id, user_id, new_status,
                                total_fields=stats['total_fields'],
                                auto_filled=stats['auto_filled'] + filled_count,
                                needs_review=stats['needs_review'],
                                unanswered=stats['unanswered'])

                            return {
                                'success': True,
                                'ats_platform': ats_platform,
                                'stats': stats,
                                'filled_count': filled_count,
                            }
                        finally:
                            await page.close()
                except Exception as e:
                    logger.error('Autofill error for app %s: %s', app_id, e)
                    svc.update_status(app_id, user_id, 'failed', error_message=str(e))
                    return {'error': str(e)}
            finally:
                db.close()

    class SubmitHandler(TaskHandler):
        """Handles final submission after user confirmation."""
        async def handle(self, task: Task) -> Dict[str, Any]:
            from backend.database import SessionLocal
            from backend.services.job_profile_service import AutofillApplicationService

            app_id = task.payload.get('application_id')
            job_url = task.payload.get('job_url')
            user_id = task.user_id

            if not app_id:
                return {'error': 'Missing application_id'}

            db = SessionLocal()
            try:
                svc = AutofillApplicationService(db)
                app = svc.get(app_id, user_id)
                if not app:
                    return {'error': 'Application not found'}

                svc.update_status(app_id, user_id, 'submitting')

                # Check DRY_RUN
                from backend.config import DRY_RUN
                if DRY_RUN:
                    from backend.models_job_application import AutofillApplication
                    import datetime as dt
                    app.status = 'ready'
                    db.commit()
                    return {'success': True, 'status': 'dry_run', 'message': 'DRY_RUN mode - not actually submitting'}

                # Navigate to URL and submit via adapter
                from backend.ats.detector import get_adapter
                adapter = get_adapter(app.ats_platform)

                browser_mgr = get_browser_manager()
                try:
                    async with browser_mgr.ephemeral_context() as context:
                        page = await context.new_page()
                        try:
                            await page.goto(app.job_url, wait_until='domcontentloaded', timeout=30000)
                            await page.wait_for_timeout(3000)

                            if adapter:
                                # Fill all fields from stored data
                                fields = svc.get_fields(app_id)
                                for f in fields:
                                    val = f.user_value or f.mapped_value
                                    if val and not f.skipped and f.field_type != 'file':
                                        try:
                                            await adapter.fill_field(page, f.to_dict(), val)
                                        except Exception:
                                            pass

                                # Upload resume if path exists
                                if app.resume_path:
                                    try:
                                        await adapter.upload_resume(page, app.resume_path)
                                    except Exception:
                                        pass

                                # Validate
                                validation = await adapter.validate(page)
                                if not validation['valid']:
                                    svc.update_status(app_id, user_id, 'failed',
                                        error_code='VALIDATION_FAILED',
                                        error_message='; '.join(validation.get('errors', [])))
                                    return {'success': False, 'errors': validation.get('errors', [])}

                                # Submit
                                result = await adapter.submit(page)
                                if result['success']:
                                    import datetime as dt
                                    app.status = 'submitted'
                                    app.submitted_at = dt.datetime.now(dt.timezone.utc)
                                    db.commit()
                                    return {'success': True, 'status': 'submitted'}
                                else:
                                    svc.update_status(app_id, user_id, 'failed',
                                        error_code='SUBMIT_FAILED',
                                        error_message=result.get('message', 'Submit failed'))
                                    return {'success': False, 'message': result.get('message')}
                            else:
                                # No adapter - just mark as submitted
                                import datetime as dt
                                app.status = 'submitted'
                                app.submitted_at = dt.datetime.now(dt.timezone.utc)
                                db.commit()
                                return {'success': True, 'status': 'submitted'}
                        finally:
                            await page.close()
                except Exception as e:
                    svc.update_status(app_id, user_id, 'failed', error_message=str(e))
                    return {'error': str(e)}
            finally:
                db.close()

    class ApplyJobHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            from backend.database import SessionLocal
            from backend.models import Application, Resume, JobPreferences, User
            from backend.services.application_service import ApplicationService

            if DRY_RUN:
                return {
                    'status': 'dry_run',
                    'message': 'DRY_RUN mode - application not submitted',
                    'would_apply': True
                }

            user_id = task.user_id
            platform = task.platform
            application_id = task.payload.get('application_id')

            if not user_id or not platform or not application_id:
                return {'error': 'user_id, platform, and application_id required'}

            db = SessionLocal()
            try:
                application_service = ApplicationService(db)
                app = db.query(Application).filter(
                    Application.id == application_id,
                    Application.user_id == user_id
                ).first()

                if not app:
                    return {'error': 'Application not found'}

                if app.status not in ['ready', 'approved']:
                    return {'error': f'Application not ready for submission: {app.status}'}

                provider = provider_registry.get(platform)
                if not provider:
                    return {'error': f'Platform {platform} not supported'}

                job = app.job if app.job else None
                if not job:
                    return {'error': 'Job not found for application'}

                prefs = db.query(JobPreferences).filter(JobPreferences.user_id == user_id).first()
                resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_default == True).first()
                user = db.query(User).filter(User.id == user_id).first()

                candidate = CandidateProfile(
                    full_name=user.full_name if user else '',
                    email=user.email if user else '',
                    phone='',
                    location='',
                    years_experience=5,
                    skills=[],
                    resume_files={'default': resume.stored_path} if resume and resume.stored_path else {}
                )

                if prefs:
                    try:
                        import json as _json
                        candidate.skills = _json.loads(prefs.skills) if prefs.skills else []
                        candidate.preferred_locations = _json.loads(prefs.preferred_locations) if prefs.preferred_locations else []
                    except Exception:
                        pass

                job_url = app.application_url or job.application_url
                if not job_url:
                    return {'error': 'No application URL available'}

                from backend.browser.session import get_session_manager
                session_manager = get_session_manager()

                async with session_manager._browser_manager.persistent_context(user_id, platform) as context:
                    page = await context.new_page()
                    try:
                        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(2000)

                        if not await provider.can_apply(page, job):
                            return {'error': 'Cannot apply to this job'}

                        if not await provider.prepare_application(page, job, candidate):
                            return {'error': 'Failed to prepare application'}

                        result = await provider.submit_application(page)

                        if result.success:
                            application_service.update_application_status(
                                application_id, user_id, 'applied', 'Applied via browser agent'
                            )

                        return {
                            'success': result.success,
                            'status': result.status,
                            'message': result.message,
                        }
                    finally:
                        await page.close()
            except Exception as e:
                logger.error('Error applying to job on %s: %s', platform, e)
                return {'error': str(e)}
            finally:
                db.close()

    return {
        TaskType.VERIFY_SESSION: VerifySessionHandler(),
        TaskType.ENSURE_LOGIN: EnsureLoginHandler(),
        TaskType.DISCONNECT: DisconnectHandler(),
        TaskType.OPEN_BROWSER: OpenBrowserHandler(),
        TaskType.SEARCH_JOBS: SearchJobsHandler(),
        TaskType.EXTRACT_JOB: ExtractJobHandler(),
        TaskType.APPLY_JOB: ApplyJobHandler(),
        TaskType.AUTOFILL_APPLICATION: AutofillHandler(),
        TaskType.SUBMIT_APPLICATION: SubmitHandler(),
    }
