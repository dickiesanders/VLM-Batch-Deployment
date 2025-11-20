"""Rate limiting and usage quota management"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter with quota support"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        requests_per_minute: int = 60,
        requests_per_day: int = 1000,
    ):
        self._redis_url = redis_url
        self._rpm = requests_per_minute
        self._rpd = requests_per_day
        self._local_buckets: dict[str, dict] = {}

    async def check_rate_limit(
        self,
        tenant_id: str,
        cost: int = 1,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limits.

        Returns:
            (allowed, info) - allowed is True if request can proceed
        """
        if self._redis_url:
            return await self._check_redis(tenant_id, cost)
        return self._check_local(tenant_id, cost)

    def _check_local(self, tenant_id: str, cost: int) -> tuple[bool, dict]:
        """Local in-memory rate limiting"""
        now = time.time()
        minute_key = int(now / 60)
        day_key = int(now / 86400)

        if tenant_id not in self._local_buckets:
            self._local_buckets[tenant_id] = {
                "minute_key": minute_key,
                "minute_count": 0,
                "day_key": day_key,
                "day_count": 0,
            }

        bucket = self._local_buckets[tenant_id]

        # Reset counters if time window changed
        if bucket["minute_key"] != minute_key:
            bucket["minute_key"] = minute_key
            bucket["minute_count"] = 0

        if bucket["day_key"] != day_key:
            bucket["day_key"] = day_key
            bucket["day_count"] = 0

        # Check limits
        info = {
            "requests_remaining_minute": self._rpm - bucket["minute_count"],
            "requests_remaining_day": self._rpd - bucket["day_count"],
            "reset_minute": (minute_key + 1) * 60,
            "reset_day": (day_key + 1) * 86400,
        }

        if bucket["minute_count"] + cost > self._rpm:
            return False, {**info, "error": "Rate limit exceeded (per minute)"}

        if bucket["day_count"] + cost > self._rpd:
            return False, {**info, "error": "Daily quota exceeded"}

        # Increment counters
        bucket["minute_count"] += cost
        bucket["day_count"] += cost

        info["requests_remaining_minute"] -= cost
        info["requests_remaining_day"] -= cost

        return True, info

    async def _check_redis(self, tenant_id: str, cost: int) -> tuple[bool, dict]:
        """Redis-based distributed rate limiting"""
        import redis.asyncio as redis

        r = redis.from_url(self._redis_url)
        now = time.time()
        minute_key = f"ratelimit:{tenant_id}:minute:{int(now / 60)}"
        day_key = f"ratelimit:{tenant_id}:day:{int(now / 86400)}"

        try:
            pipe = r.pipeline()

            # Get current counts
            pipe.get(minute_key)
            pipe.get(day_key)
            results = await pipe.execute()

            minute_count = int(results[0] or 0)
            day_count = int(results[1] or 0)

            info = {
                "requests_remaining_minute": self._rpm - minute_count,
                "requests_remaining_day": self._rpd - day_count,
            }

            if minute_count + cost > self._rpm:
                return False, {**info, "error": "Rate limit exceeded (per minute)"}

            if day_count + cost > self._rpd:
                return False, {**info, "error": "Daily quota exceeded"}

            # Increment counters
            pipe = r.pipeline()
            pipe.incr(minute_key, cost)
            pipe.expire(minute_key, 60)
            pipe.incr(day_key, cost)
            pipe.expire(day_key, 86400)
            await pipe.execute()

            info["requests_remaining_minute"] -= cost
            info["requests_remaining_day"] -= cost

            return True, info

        finally:
            await r.close()

    async def get_usage(self, tenant_id: str) -> dict:
        """Get current usage stats for tenant"""
        if self._redis_url:
            import redis.asyncio as redis

            r = redis.from_url(self._redis_url)
            now = time.time()
            day_key = f"ratelimit:{tenant_id}:day:{int(now / 86400)}"

            try:
                count = await r.get(day_key)
                return {
                    "tenant_id": tenant_id,
                    "requests_today": int(count or 0),
                    "quota": self._rpd,
                }
            finally:
                await r.close()

        bucket = self._local_buckets.get(tenant_id, {})
        return {
            "tenant_id": tenant_id,
            "requests_today": bucket.get("day_count", 0),
            "quota": self._rpd,
        }


# Global rate limiter instance
_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def initialize_rate_limiter(
    redis_url: Optional[str] = None,
    requests_per_minute: int = 60,
    requests_per_day: int = 1000,
) -> RateLimiter:
    global _limiter
    _limiter = RateLimiter(redis_url, requests_per_minute, requests_per_day)
    return _limiter
