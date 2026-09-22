import asyncio
import logging
import os
import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from backend.browser.queue import TaskQueue, get_task_queue
from backend.browser.worker import BrowserWorker, create_default_handlers
from backend.config import MAX_BROWSER_WORKERS

logger = logging.getLogger('worker_pool')


@dataclass
class WorkerInfo:
    worker_id: str
    worker: BrowserWorker
    task: asyncio.Task
    started_at: float


class WorkerPool:
    """Manages a pool of browser workers."""
    
    def __init__(
        self,
        max_workers: int = MAX_BROWSER_WORKERS,
        poll_interval: float = 5.0,
        max_concurrent_per_worker: int = 1
    ):
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.max_concurrent_per_worker = max_concurrent_per_worker
        self._workers: Dict[str, WorkerInfo] = {}
        self._task_queue: Optional[TaskQueue] = None
        self._handlers: Dict[str, Any] = {}
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
            
            self._workers[worker_id] = WorkerInfo(
                worker_id=worker_id,
                worker=worker,
                task=task,
                started_at=asyncio.get_event_loop().time()
            )
            
            logger.info('Added worker: %s (total: %d)', worker_id, len(self._workers))
            return worker_id
    
    async def remove_worker(self, worker_id: str, graceful: bool = True) -> bool:
        """Remove a worker from the pool."""
        async with self._lock:
            info = self._workers.pop(worker_id, None)
            if not info:
                return False
            
            if graceful:
                await info.worker.stop()
            else:
                info.task.cancel()
                try:
                    await info.task
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
                key=lambda x: x[1].started_at
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
                        if info.task.done():
                            try:
                                await info.task
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
                        'started_at': info.started_at,
                        'alive': not info.task.done()
                    }
                    for wid, info in self._workers.items()
                }
            }
    
    async def shutdown(self):
        """Shutdown all workers."""
        self._running = False
        
        async with self._lock:
            for worker_id, info in self._workers.items():
                await info.worker.stop()
            
            self._workers.clear()
        
        if self._task_queue:
            await self._task_queue.disconnect()
        
        logger.info('WorkerPool shutdown complete')


_worker_pool: Optional[WorkerPool] = None


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