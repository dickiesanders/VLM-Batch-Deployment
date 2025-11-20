"""Job tracking with Redis support for distributed systems"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from api.models import BatchJob, JobStatus

logger = logging.getLogger(__name__)


class JobTracker(ABC):
    """Abstract job tracker interface"""

    @abstractmethod
    async def create_job(self, job: BatchJob) -> None:
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[BatchJob]:
        pass

    @abstractmethod
    async def update_job(self, job: BatchJob) -> None:
        pass

    @abstractmethod
    async def delete_job(self, job_id: str) -> None:
        pass


class InMemoryJobTracker(JobTracker):
    """In-memory job tracker for single-instance deployments"""

    def __init__(self):
        self._jobs: dict[str, BatchJob] = {}

    async def create_job(self, job: BatchJob) -> None:
        self._jobs[job.job_id] = job

    async def get_job(self, job_id: str) -> Optional[BatchJob]:
        return self._jobs.get(job_id)

    async def update_job(self, job: BatchJob) -> None:
        self._jobs[job.job_id] = job

    async def delete_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)


class RedisJobTracker(JobTracker):
    """Redis-based job tracker for distributed deployments"""

    def __init__(self, redis_url: str, ttl_seconds: int = 86400):
        import redis.asyncio as redis
        self._redis = redis.from_url(redis_url)
        self._ttl = ttl_seconds
        self._prefix = "ocr:job:"

    async def create_job(self, job: BatchJob) -> None:
        key = f"{self._prefix}{job.job_id}"
        data = job.model_dump_json()
        await self._redis.setex(key, self._ttl, data)

    async def get_job(self, job_id: str) -> Optional[BatchJob]:
        key = f"{self._prefix}{job_id}"
        data = await self._redis.get(key)
        if data:
            return BatchJob.model_validate_json(data)
        return None

    async def update_job(self, job: BatchJob) -> None:
        key = f"{self._prefix}{job.job_id}"
        data = job.model_dump_json()
        await self._redis.setex(key, self._ttl, data)

    async def delete_job(self, job_id: str) -> None:
        key = f"{self._prefix}{job_id}"
        await self._redis.delete(key)

    async def close(self):
        await self._redis.close()


# Global tracker instance
_tracker: Optional[JobTracker] = None


def get_job_tracker() -> JobTracker:
    global _tracker
    if _tracker is None:
        _tracker = InMemoryJobTracker()
    return _tracker


def initialize_job_tracker(redis_url: Optional[str] = None) -> JobTracker:
    global _tracker
    if redis_url:
        _tracker = RedisJobTracker(redis_url)
        logger.info("Using Redis job tracker")
    else:
        _tracker = InMemoryJobTracker()
        logger.info("Using in-memory job tracker")
    return _tracker
