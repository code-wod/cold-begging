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
    }
