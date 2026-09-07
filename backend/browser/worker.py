import asyncio
import logging
import signal
import sys
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime, timezone

from backend.browser.queue import TaskQueue, get_task_queue, Task, TaskType, TaskStatus
from backend.browser.manager import get_browser_manager
from backend.browser.session import get_session_manager
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
            user_id = task.payload.get('user_id')
            platform = task.payload.get('platform')
            
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            
            status = await session_manager.verify_session(user_id, platform)
            return {'status': status.value}
    
    class EnsureLoginHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.payload.get('user_id')
            platform = task.payload.get('platform')
            headless = task.payload.get('headless', False)
            
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            
            success = await session_manager.ensure_login(user_id, platform, headless)
            return {'success': success}
    
    class DisconnectHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.payload.get('user_id')
            platform = task.payload.get('platform')
            
            if not user_id or not platform:
                return {'error': 'user_id and platform required'}
            
            success = await session_manager.disconnect(user_id, platform)
            return {'success': success}
    
    class OpenBrowserHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            session_manager = get_session_manager()
            user_id = task.payload.get('user_id')
            platform = task.payload.get('platform')
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
            # This will be implemented with provider integration
            return {'error': 'SearchJobsHandler not yet implemented'}
    
    class ExtractJobHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            return {'error': 'ExtractJobHandler not yet implemented'}
    
    class ApplyJobHandler(TaskHandler):
        async def handle(self, task: Task) -> Dict[str, Any]:
            if DRY_RUN:
                return {
                    'status': 'dry_run',
                    'message': 'DRY_RUN mode - application not submitted',
                    'would_apply': True
                }
            return {'error': 'ApplyJobHandler not yet implemented'}
    
    return {
        TaskType.VERIFY_SESSION: VerifySessionHandler(),
        TaskType.ENSURE_LOGIN: EnsureLoginHandler(),
        TaskType.DISCONNECT: DisconnectHandler(),
        TaskType.OPEN_BROWSER: OpenBrowserHandler(),
        TaskType.SEARCH_JOBS: SearchJobsHandler(),
        TaskType.EXTRACT_JOB: ExtractJobHandler(),
        TaskType.APPLY_JOB: ApplyJobHandler(),
    }


async def run_worker(
    worker_id: str = 'worker-1',
    poll_interval: float = 5.0,
    max_concurrent: int = 1
):
    """Run a browser worker."""
    task_queue = get_task_queue()
    await task_queue.connect()
    
    handlers = create_default_handlers()
    worker = BrowserWorker(
        worker_id=worker_id,
        task_queue=task_queue,
        handlers=handlers,
        poll_interval=poll_interval,
        max_concurrent=max_concurrent
    )
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info('Received shutdown signal')
        asyncio.create_task(worker.stop())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    try:
        await worker.start()
    finally:
        await task_queue.disconnect()
        logger.info('Worker %s shutdown complete', worker_id)


if __name__ == '__main__':
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    worker_id = os.getenv('WORKER_ID', 'worker-1')
    poll_interval = float(os.getenv('POLL_INTERVAL', '5.0'))
    max_concurrent = int(os.getenv('MAX_CONCURRENT', '1'))
    
    asyncio.run(run_worker(worker_id, poll_interval, max_concurrent))