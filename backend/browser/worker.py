import asyncio
import logging
import uuid
from typing import Optional, List, Dict, Any
from enum import Enum

import redis.asyncio as redis

from backend.config import REDIS_URL
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
        task_queue: TaskQueue,
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
        """Start the worker."""
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
        """Dequeue and process a batch of tasks."""
        if not self._semaphore:
            return

        # Check available slots
        available = self.max_concurrent - len(self._tasks)
        if available <= 0:
            return

        tasks = await self.task_queue.dequeue(self.worker_id, available)

        for task in tasks:
            if not self._running:
                break

            # Create task coroutine
            coro = self._execute_task(task)
            asyncio_task = asyncio.create_task(coro)
            self._tasks[task.id] = asyncio_task

            # Clean up completed tasks
            asyncio_task.add_done_callback(
                lambda t, tid=task.id: self._tasks.pop(tid, None)
            )

    async def _execute_task(self, task: Task):
        """Execute a single task."""
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
        """Stop the worker gracefully."""
        self._running = False

        # Wait for running tasks to complete (with timeout)
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
    from backend.browser.session import get_session_manager

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

            # This just verifies the session can be opened
            # The actual page interaction would be done by the caller
            page = await session_manager.open_managed_browser(user_id, platform, url)
            current_url = page.url
            await page.close()
            return {'url': current_url}

    class SearchJobsHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            from backend.providers import provider_registry
            from backend.providers.base import SearchConfig
            from backend.services import get_job_service, get_application_service
            from backend.database import SessionLocal
            from backend.models import User
            
            user_id = task.user_id
            platform = task.platform
            search_config = task.payload.get('search_config', {})
            
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            
            provider = provider_registry.get(platform)
            if not provider or not provider.capabilities.job_search:
                return {'error': f'Platform {platform} does not support job search'}
            
            # Check session
            from backend.browser.session import get_session_manager
            session_manager = get_session_manager()
            session = await session_manager.get_session_info(user_id, platform)
            if session.status != 'connected':
                return {'error': f'Not logged in to {platform}'}
            
            db = SessionLocal()
            try:
                # Get user preferences
                job_service = get_job_service()
                matching_service = get_matching_service()
                application_service = get_application_service()
                
                prefs = job_service.get_job_preferences(user_id)
                if not prefs:
                    return {'error': 'No job preferences configured'}
                
                # Build search config
                search_config = SearchConfig(
                    keywords=search_config.get('keywords', []),
                    locations=search_config.get('locations', []),
                    remote=search_config.get('remote', False),
                    job_types=search_config.get('job_types', []),
                    salary_min=search_config.get('salary_min'),
                )
                
                # Create browser context and search
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
                            
                            # Check for existing application
                            existing_app = db.query(Application).filter(
                                Application.user_id == user_id,
                                Application.job_id == job.id
                            ).first()
                            if existing_app:
                                continue
                            
                            # Run AI matching
                            user = db.query(User).filter(User.id == user_id).first()
                            match_result = matching_service.match_job(user, job)
                            total_matches += 1
                            
                            # Only proceed if match score meets threshold
                            min_score = 70
                            if match_result.get('match_score', 0) >= min_score:
                                app = application_service.process_job_match(user, job)
                                if app:
                                    applications += 1
                                    matches += 1
                        
                        return {
                            'jobs_found': total_jobs,
                            'matches': matches,
                            'applications_created': applications,
                        }
                    finally:
                        await page.close()
                        db.close()
                        
            except Exception as e:
                logger.error('Error searching jobs on %s for user %d: %s', platform, user_id, e)
                return {'error': str(e)}
    
    class ExtractJobHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            return {'error': 'ExtractJobHandler not yet implemented'}
    
    class ApplyJobHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            from backend.providers import provider_registry
            from backend.services import get_application_service
            from backend.database import SessionLocal
            from backend.models import Application
            
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
                application_service = get_application_service()
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
                
                # Get job and candidate info
                from backend.services import get_job_service
                job_service = get_job_service()
                job = job_service.get_job(app.job_id)
                
                # Get candidate profile
                from backend.services import get_job_service as get_job_service2
                # Build candidate profile from user preferences and resume
                from backend.models import Resume, JobPreferences
                prefs = db.query(JobPreferences).filter(JobPreferences.user_id == user_id).first()
                resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_default == True).first()
                
                candidate = CandidateProfile(
                    full_name='',
                    email='',
                    phone='',
                    linkedin_url='',
                    github_url='',
                    portfolio_url='',
                    years_experience=0,
                    skills=[],
                    current_company='',
                    current_role='',
                    notice_period='',
                    work_authorization='',
                    willing_to_relocate=False,
                    salary_expectation=None,
                    preferred_locations=[],
                    resume_files={}
                )
                
                if prefs:
                    try:
                        import json
                        candidate.skills = json.loads(prefs.skills) if prefs.skills else []
                        candidate.preferred_locations = json.loads(prefs.preferred_locations) if prefs.preferred_locations else []
                        candidate.years_experience = 5  # Default
                    except Exception:
                        pass
                
                if resume:
                    candidate.resume_files = {'default': resume.stored_path}
                
                # Get job URL
                job_url = app.job.application_url
                
                # Create browser context and apply
                from backend.browser.session import get_session_manager
                session_manager = get_session_manager()
                
                async with session_manager._browser_manager.persistent_context(user_id, platform) as context:
                    page = await context.new_page()
                    
                    try:
                        # Navigate to job
                        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(2000)
                        
                        # Check if can apply
                        if not await provider.can_apply(page, job):
                            return {'error': 'Cannot apply to this job'}
                        
                        # Prepare application
                        if not await provider.prepare_application(page, job, candidate):
                            return {'error': 'Failed to prepare application'}
                        
                        # Submit application
                        result = await provider.submit_application(page)
                        
                        # Update application status
                        if result.success:
                            application_service.update_application_status(
                                application_id, 'applied', 'Applied via browser agent'
                            )
                        
                        return {
                            'success': result.success,
                            'status': result.status,
                            'message': result.message,
                        }
                    finally:
                        await page.close()
                        db.close()
                        
            except Exception as e:
                logger.error('Error applying to job on %s: %s', platform, e)
                return {'error': str(e)}

    return {
        TaskType.VERIFY_SESSION: VerifySessionHandler(),
        TaskType.ENSURE_LOGIN: EnsureLoginHandler(),
        TaskType.DISCONNECT: DisconnectHandler(),
        TaskType.OPEN_BROWSER: OpenBrowserHandler(),
        TaskType.SEARCH_JOBS: SearchJobsHandler(),
        TaskType.EXTRACT_JOB: ExtractJobHandler(),
        TaskType.APPLY_JOB: ApplyJobHandler(),
    }


def get_worker_pool() -> 'WorkerPool':
    """Get or create the global WorkerPool instance."""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = WorkerPool()
    return _worker_pool


_worker_pool: Optional['WorkerPool'] = None


class WorkerPool:
    """Manages a pool of browser workers."""

    def __init__(
        self,
        max_workers: int = 3,
        poll_interval: float = 5.0,
        max_concurrent_per_worker: int = 1
    ):
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.max_concurrent_per_worker = max_concurrent_per_worker
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._task_queue: Optional[TaskQueue] = None
        self._handlers: Dict[str, object] = {}
        self._running = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the worker pool."""
        self._task_queue = get_task_queue()
        await self._task_queue.connect()
        self._handlers = create_default_handlers()
        logger.info('WorkerPool initialized (max_workers=%d)', self.max_workers)

    async def start(self, initial_workers: Optional[int] = None):
        """Start the worker pool."""
        if self._running:
            return

        self._running = True
        initial = initial_workers or min(1, self.max_workers)

        for i in range(initial):
            await self._add_worker()

        # Start monitor task
        asyncio.create_task(self._monitor())

        logger.info('WorkerPool started with %d workers', len(self._workers))

    async def _add_worker(self) -> str:
        """Add a new worker to the pool."""
        async with self._lock:
            if len(self._workers) >= self.max_workers:
                raise RuntimeError('Max workers reached')

            worker_id = f'worker-{uuid.uuid4().hex[:8]}'
            worker = BrowserWorker(
                worker_id=worker_id,
                task_queue=self._task_queue,
                handlers=self._handlers,
                poll_interval=self.poll_interval,
                max_concurrent=self.max_concurrent_per_worker
            )

            task = asyncio.create_task(worker.start())

            self._workers[worker_id] = {
                'worker': worker,
                'task': task,
                'started_at': asyncio.get_event_loop().time()
            }

            logger.info('Added worker: %s (total: %d)', worker_id, len(self._workers))
            return worker_id

    async def remove_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """Remove a worker from the pool."""
        async with self._lock:
            info = self._workers.pop(worker_id, None)
            if not info:
                return False

            if graceful:
                await info['worker'].stop()
            else:
                info['task'].cancel()
                try:
                    await info['task']
                except asyncio.CancelledError:
                    pass

            logger.info('Removed worker: %s (total: %d)', worker_id, len(self._workers))
            return True

    async def scale_to(self, target_workers: int):
        """Scale the pool to target number of workers."""
        target = max(0, min(target_workers, self.max_workers))
        current = len(self._workers)

        if target > current:
            for _ in range(target - current):
                await self._add_worker()
        elif target < current:
            # Remove excess workers (oldest first)
            sorted_workers = sorted(
                self._workers.items(),
                key=lambda x: x[1]['started_at']
            )
            for worker_id, _ in sorted_workers[:current - target]:
                await self.remove_worker(worker_id)

        logger.info('Scaled worker pool to %d workers', len(self._workers))

    async def _monitor(self):
        """Monitor worker health and restart failed workers."""
        while self._running:
            try:
                await asyncio.sleep(30)

                async with self._lock:
                    dead_workers = []
                    for worker_id, info in self._workers.items():
                        if info['task'].done():
                            try:
                                await info['task']
                            except Exception as e:
                                logger.error('Worker %s died: %s', worker_id, e)
                            dead_workers.append(worker_id)

                    for worker_id in dead_workers:
                        logger.warning('Restarting dead worker: %s', worker_id)
                        self._workers.pop(worker_id, None)
                        await self._add_worker()

            except Exception as e:
                logger.error('WorkerPool monitor error: %s', e)

    async def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        async with self._lock:
            return {
                'total_workers': len(self._workers),
                'max_workers': self.max_workers,
                'running': self._running,
                'workers': {
                    wid: {
                        'started_at': info['started_at'],
                        'alive': not info['task'].done()
                    }
                    for wid, info in self._workers.items()
                }
            }

    async def shutdown(self):
        """Shutdown all workers."""
        self._running = False

        for worker_id, info in list(self._workers.items()):
            await info['worker'].stop()

        if self._task_queue:
            await self._task_queue.disconnect()

        logger.info('WorkerPool shutdown complete')


async def get_worker_pool() -> WorkerPool:
    """Get or create the global WorkerPool instance."""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = WorkerPool()
        await _worker_pool.initialize()
    return _worker_pool


async def shutdown_worker_pool():
    """Shutdown the global worker pool."""
    global _worker_pool
    if _worker_pool:
        await _worker_pool.shutdown()
        _worker_pool = None


async def run_worker(worker_id: str = None, poll_interval: float = 5.0, max_concurrent: int = 1):
    """Run a single browser worker."""
    task_queue = get_task_queue()
    await task_queue.connect()
    
    handlers = create_default_handlers()
    
    worker_id = worker_id or f'worker-{uuid.uuid4().hex[:8]}'
    worker = BrowserWorker(
        worker_id=worker_id,
        task_queue=task_queue,
        handlers=create_default_handlers(),
        poll_interval=5.0,
        max_concurrent=1
    )
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info('Worker interrupted')
    finally:
        await worker.stop()
        await task_queue.disconnect()


if __name__ == '__main__':
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the worker
    asyncio.run(run_worker())