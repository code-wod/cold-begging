import json
import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict, field
import uuid
import threading

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
    AUTOFILL_APPLICATION = 'autofill_application'
    SUBMIT_APPLICATION = 'submit_application'


class TaskStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Task:
    type: str
    user_id: int
    platform: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
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


class InMemoryTaskQueue:
    """In-memory task queue fallback when Redis is unavailable."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._queue: List[str] = []  # ordered task ids (FIFO)
        self._processing: Dict[str, str] = {}  # task_id -> worker_id
        self._lock = threading.Lock()
        self._connected = True

    def is_connected(self) -> bool:
        return True

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def enqueue(self, task: Task) -> str:
        with self._lock:
            self._tasks[task.id] = task
            self._queue.append(task.id)
        logger.debug('Enqueued task %s (%s) [memory]', task.id, task.type)
        return task.id

    async def dequeue(self, worker_id: str, count: int = 1) -> List[Task]:
        tasks = []
        with self._lock:
            for _ in range(count):
                if not self._queue:
                    break
                task_id = self._queue.pop(0)
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING.value:
                    task.status = TaskStatus.RUNNING.value
                    task.started_at = datetime.now(timezone.utc).isoformat()
                    self._processing[task_id] = worker_id
                    tasks.append(task)
        return tasks

    async def complete_task(self, task_id: str, result=None, error=None):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            if error:
                task.status = TaskStatus.FAILED.value
                task.error = error
            else:
                task.status = TaskStatus.COMPLETED.value
                task.result = result
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self._processing.pop(task_id, None)

    async def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    async def get_task_status(self, task_id: str) -> Optional[str]:
        task = self._tasks.get(task_id)
        return task.status if task else None

    async def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.COMPLETED.value:
            return task.result
        return None

    async def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status not in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
                return False
            task.status = TaskStatus.CANCELLED.value
            task.completed_at = datetime.now(timezone.utc).isoformat()
            if task_id in self._queue:
                self._queue.remove(task_id)
            self._processing.pop(task_id, None)
            return True

    async def get_queue_stats(self) -> Dict[str, int]:
        with self._lock:
            pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING.value)
            processing = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING.value)
            completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED.value)
        return {'pending': pending, 'processing': processing, 'completed': completed}

    async def cleanup_stale_tasks(self, max_age_seconds: int = 3600) -> int:
        now = datetime.now(timezone.utc)
        cleaned = 0
        with self._lock:
            for task_id, task in list(self._tasks.items()):
                if task.status == TaskStatus.RUNNING.value and task.started_at:
                    try:
                        started = datetime.fromisoformat(task.started_at)
                        if started.tzinfo is None:
                            started = started.replace(tzinfo=timezone.utc)
                        age = (now - started).total_seconds()
                        if age > max_age_seconds:
                            task.status = TaskStatus.PENDING.value
                            task.started_at = None
                            task.retries += 1
                            if task.retries <= task.max_retries:
                                self._queue.append(task_id)
                                cleaned += 1
                            else:
                                task.status = TaskStatus.FAILED.value
                                task.error = 'Max retries exceeded'
                                task.completed_at = now.isoformat()
                            self._processing.pop(task_id, None)
                    except Exception:
                        pass
        return cleaned


class RedisTaskQueue:
    """Redis-based task queue for browser worker communication."""

    QUEUE_KEY = 'browser:task_queue'
    PROCESSING_KEY = 'browser:processing'
    RESULTS_KEY = 'browser:results'
    TASK_PREFIX = 'browser:task:'

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis = None
        self._connected = False

    async def connect(self):
        if self._connected:
            return
        import redis.asyncio as redis
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
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info('TaskQueue disconnected from Redis')

    def is_connected(self) -> bool:
        return self._connected

    async def enqueue(self, task: Task) -> str:
        if not self._connected:
            await self.connect()
        task_key = f'{self.TASK_PREFIX}{task.id}'
        await self._redis.set(task_key, json.dumps(task.to_dict()))
        score = datetime.fromisoformat(task.created_at.replace('Z', '+00:00')).timestamp()
        await self._redis.zadd(self.QUEUE_KEY, {task.id: score})
        logger.debug('Enqueued task %s (%s)', task.id, task.type)
        return task.id

    async def dequeue(self, worker_id: str, count: int = 1) -> List[Task]:
        if not self._connected:
            await self.connect()
        tasks = []
        for _ in range(count):
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
            now_timestamp = time.time()
            script = self._redis.register_script(lua_script)
            task_data = await script(
                keys=[self.QUEUE_KEY, self.TASK_PREFIX, self.PROCESSING_KEY],
                args=[str(now_timestamp)]
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
        task_key = f'{self.TASK_PREFIX}{task.id}'
        await self._redis.set(task_key, json.dumps(task.to_dict()))

    async def complete_task(self, task_id: str, result=None, error=None):
        if not self._connected:
            await self.connect()
        task_key = f'{self.TASK_PREFIX}{task_id}'
        task_data = await self._redis.get(task_key)
        if not task_data:
            return
        task = Task.from_dict(json.loads(task_data))
        if error:
            task.status = TaskStatus.FAILED.value
            task.error = error
        else:
            task.status = TaskStatus.COMPLETED.value
            task.result = result
        task.completed_at = datetime.now(timezone.utc).isoformat()
        await self._redis.zrem(self.PROCESSING_KEY, task_id)
        await self._redis.zadd(self.RESULTS_KEY, {task_id: time.time()})
        await self._redis.set(task_key, json.dumps(task.to_dict()))
        await self._redis.expire(task_key, 604800)

    async def get_task(self, task_id: str) -> Optional[Task]:
        if not self._connected:
            await self.connect()
        task_key = f'{self.TASK_PREFIX}{task_id}'
        task_data = await self._redis.get(task_key)
        if task_data:
            return Task.from_dict(json.loads(task_data))
        return None

    async def get_task_status(self, task_id: str) -> Optional[str]:
        task = await self.get_task(task_id)
        return task.status if task else None

    async def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = await self.get_task(task_id)
        if task and task.status == TaskStatus.COMPLETED.value:
            return task.result
        return None

    async def cancel_task(self, task_id: str) -> bool:
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
        if not self._connected:
            await self.connect()
        pending = await self._redis.zcard(self.QUEUE_KEY)
        processing = await self._redis.zcard(self.PROCESSING_KEY)
        results = await self._redis.zcard(self.RESULTS_KEY)
        return {'pending': pending, 'processing': processing, 'completed': results}

    async def cleanup_stale_tasks(self, max_age_seconds: int = 3600) -> int:
        if not self._connected:
            await self.connect()
        now = datetime.now(timezone.utc)
        processing_tasks = await self._redis.zrange(self.PROCESSING_KEY, 0, -1)
        cleaned = 0
        for task_id in processing_tasks:
            task = await self.get_task(task_id)
            if task and task.started_at:
                try:
                    started = datetime.fromisoformat(task.started_at)
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                    age = (now - started).total_seconds()
                    if age > max_age_seconds:
                        await self._redis.zrem(self.PROCESSING_KEY, task_id)
                        task.status = TaskStatus.PENDING.value
                        task.started_at = None
                        task.retries += 1
                        if task.retries <= task.max_retries:
                            await self._redis.zadd(self.QUEUE_KEY, {task_id: now.timestamp()})
                            await self._update_task(task)
                            cleaned += 1
                        else:
                            await self.complete_task(task_id, error='Max retries exceeded')
                except Exception:
                    pass
        return cleaned


# Backward-compatible alias: TaskQueue refers to whichever implementation is active
TaskQueue = InMemoryTaskQueue

_task_queue: Optional[object] = None


def get_task_queue():
    """Get or create the global TaskQueue instance.
    Tries Redis first, falls back to in-memory queue.
    """
    global _task_queue
    if _task_queue is None:
        from backend.config import REDIS_URL
        try:
            import redis.asyncio as aioredis
            test_redis = aioredis.from_url(REDIS_URL, encoding='utf-8', decode_responses=True)
            # We can't actually ping synchronously, so just try creating the Redis queue
            queue = RedisTaskQueue(REDIS_URL)
            _task_queue = queue
        except Exception:
            _task_queue = InMemoryTaskQueue()
    return _task_queue
