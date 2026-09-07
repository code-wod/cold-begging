import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict, field
import uuid

import redis.asyncio as redis

from backend.config import REDIS_URL

logger = logging.getLogger('task_queue')


class TaskType(Enum):
    """Types of tasks the browser worker can execute."""
    VERIFY_SESSION = 'verify_session'
    ENSURE_LOGIN = 'ensure_login'
    SEARCH_JOBS = 'search_jobs'
    EXTRACT_JOB = 'extract_job'
    APPLY_JOB = 'apply_job'
    DISCONNECT = 'disconnect'
    OPEN_BROWSER = 'open_browser'


class TaskStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Task:
    id: str
    type: str
    user_id: int
    platform: str
    payload: Dict[str, Any]
    status: str = TaskStatus.PENDING.value
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(**data)


class TaskQueue:
    """Redis-based task queue for browser worker communication."""
    
    QUEUE_KEY = 'browser:task_queue'
    PROCESSING_KEY = 'browser:processing'
    RESULTS_KEY = 'browser:results'
    TASK_PREFIX = 'browser:task:'
    
    def __init__(self, redis_url: str = REDIS_URL):
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis."""
        if self._connected:
            return
        
        self._redis = redis.from_url(
            self._redis_url,
            encoding='utf-8',
            decode_responses=True,
            max_connections=10
        )
        await self._redis.ping()
        self._connected = True
        logger.info('TaskQueue connected to Redis at %s', self._redis_url)
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info('TaskQueue disconnected from Redis')
    
    def is_connected(self) -> bool:
        return self._connected
    
    async def enqueue(self, task: Task) -> str:
        """Add a task to the queue."""
        if not self._connected:
            await self.connect()
        
        task_key = f'{self.TASK_PREFIX}{task.id}'
        
        # Store task data
        await self._redis.set(task_key, json.dumps(task.to_dict()))
        
        # Add to queue (sorted by creation time for FIFO)
        await self._redis.zadd(self.QUEUE_KEY, {task.id: task.created_at})
        
        logger.debug('Enqueued task %s (%s)', task.id, task.type)
        return task.id
    
    async def dequeue(self, worker_id: str, count: int = 1) -> List[Task]:
        """Atomically dequeue tasks for processing."""
        if not self._connected:
            await self.connect()
        
        tasks = []
        
        for _ in range(count):
            # Use Lua script for atomic pop
            # ZPOPMIN returns [member, score] array, so we need task_id[1] for member
            lua_script = """
            local result = redis.call('ZPOPMIN', KEYS[1], 1)
            if result and #result > 0 then
                local task_id = result[1]
                local task_key = KEYS[2] .. task_id
                local task_data = redis.call('GET', task_key)
                if task_data then
                    redis.call('ZADD', KEYS[3], ARGV[1], task_id)
                    return task_data
                end
            end
            return nil
            """
            
            script = self._redis.register_script(lua_script)
            task_data = await script(
                keys=[self.QUEUE_KEY, self.TASK_PREFIX, self.PROCESSING_KEY],
                args=[datetime.now(timezone.utc).isoformat()]
            )
            
            if task_data:
                task = Task.from_dict(json.loads(task_data))
                task.status = TaskStatus.RUNNING.value
                task.started_at = datetime.now(timezone.utc).isoformat()
                await self._update_task(task)
                tasks.append(task)
            else:
                break
        
        return tasks
    
    async def _update_task(self, task: Task):
        """Update task in Redis."""
        task_key = f'{self.TASK_PREFIX}{task.id}'
        await self._redis.set(task_key, json.dumps(task.to_dict()))
    
    async def complete_task(self, task_id: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Mark task as completed or failed."""
        if not self._connected:
            await self.connect()
        
        task_key = f'{self.TASK_PREFIX}{task_id}'
        task_data = await self._redis.get(task_key)
        
        if not task_data:
            logger.warning('Task not found for completion: %s', task_id)
            return
        
        task = Task.from_dict(json.loads(task_data))
        
        if error:
            task.status = TaskStatus.FAILED.value
            task.error = error
        else:
            task.status = TaskStatus.COMPLETED.value
            task.result = result
        
        task.completed_at = datetime.now(timezone.utc).isoformat()
        
        # Move from processing to results
        await self._redis.zrem(self.PROCESSING_KEY, task_id)
        await self._redis.zadd(self.RESULTS_KEY, {task_id: task.completed_at})
        await self._redis.set(task_key, json.dumps(task.to_dict()))
        
        # Set TTL on result (7 days)
        await self._redis.expire(task_key, 604800)
        
        logger.debug('Task %s completed with status: %s', task_id, task.status)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        if not self._connected:
            await self.connect()
        
        task_key = f'{self.TASK_PREFIX}{task_id}'
        task_data = await self._redis.get(task_key)
        
        if task_data:
            return Task.from_dict(json.loads(task_data))
        return None
    
    async def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status."""
        task = await self.get_task(task_id)
        return task.status if task else None
    
    async def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result."""
        task = await self.get_task(task_id)
        if task and task.status == TaskStatus.COMPLETED.value:
            return task.result
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if not self._connected:
            await self.connect()
        
        task = await self.get_task(task_id)
        if not task:
            return False
        
        if task.status not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
            return False
        
        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.now(timezone.utc).isoformat()
        
        await self._redis.zrem(self.QUEUE_KEY, task_id)
        await self._redis.zrem(self.PROCESSING_KEY, task_id)
        await self._update_task(task)
        
        return True
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        if not self._connected:
            await self.connect()
        
        pending = await self._redis.zcard(self.QUEUE_KEY)
        processing = await self._redis.zcard(self.PROCESSING_KEY)
        results = await self._redis.zcard(self.RESULTS_KEY)
        
        return {
            'pending': pending,
            'processing': processing,
            'completed': results,
        }
    
    async def cleanup_stale_tasks(self, max_age_seconds: int = 3600) -> int:
        """Clean up tasks stuck in processing for too long."""
        if not self._connected:
            await self.connect()
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Get all processing tasks
        processing_tasks = await self._redis.zrange(self.PROCESSING_KEY, 0, -1)
        cleaned = 0
        
        for task_id in processing_tasks:
            task = await self.get_task(task_id)
            if task and task.started_at:
                from dateutil import parser
                started = parser.isoparse(task.started_at)
                age = (datetime.now(timezone.utc) - started).total_seconds()
                
                if age > max_age_seconds:
                    # Re-queue the task
                    await self._redis.zrem(self.PROCESSING_KEY, task_id)
                    task.status = TaskStatus.PENDING.value
                    task.started_at = None
                    task.retries += 1
                    
                    if task.retries <= task.max_retries:
                        await self._redis.zadd(self.QUEUE_KEY, {task_id: now})
                        await self._update_task(task)
                        cleaned += 1
                        logger.warning('Re-queued stale task %s (retry %d)', task_id, task.retries)
                    else:
                        # Max retries exceeded
                        await self.complete_task(task_id, error='Max retries exceeded')
                        logger.error('Task %s exceeded max retries', task_id)
        
        return cleaned


_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get or create the global TaskQueue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue