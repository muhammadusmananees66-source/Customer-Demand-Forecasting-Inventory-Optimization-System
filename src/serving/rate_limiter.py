"""
Redis-based rate limiter for API
"""

import os
import time

import redis.asyncio as redis
import structlog
from fastapi import HTTPException, Request

logger = structlog.get_logger()

# Configuration
REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT: int = int(os.environ.get("REDIS_PORT", 6379))
DEFAULT_LIMIT: int = int(os.environ.get("RATE_LIMIT", 100))
DEFAULT_WINDOW: int = int(os.environ.get("RATE_WINDOW", 60))

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """
    Get Redis client singleton.

    Returns:
        Redis client instance or None if connection fails
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await _redis_client.ping()
            logger.info("Redis rate limiter connected")
        except Exception as e:
            logger.warning(f"Redis rate limiter connection failed: {e}")
            _redis_client = None
    return _redis_client


class RateLimiter:
    """
    Rate limiter using Redis for distributed rate limiting.

    Features:
    - Distributed rate limiting across multiple pods
    - Configurable limit and window
    - Returns rate limit headers
    """

    def __init__(self, limit: int = DEFAULT_LIMIT, window: int = DEFAULT_WINDOW) -> None:
        """
        Initialize rate limiter.

        Args:
            limit: Maximum number of requests per window
            window: Time window in seconds
        """
        self.limit: int = limit
        self.window: int = window
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis | None:
        """Get Redis client."""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def __call__(self, request: Request) -> bool:
        """
        Check rate limit for the request.

        Args:
            request: FastAPI request object

        Returns:
            True if request is allowed

        Raises:
            HTTPException: If rate limit is exceeded
        """
        client_ip: str = request.client.host if request.client else "unknown"
        key: str = f"rate_limit:{client_ip}"

        redis_client = await self._get_redis()

        # If Redis is not available, allow the request (fail open)
        if redis_client is None:
            logger.warning("Rate limiter unavailable, allowing request")
            return True

        try:
            # Get current count
            current: int = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, self.window)

            # Add rate limit headers
            remaining: int = max(0, self.limit - current)
            reset_time: int = int(time.time()) + self.window

            request.state.rate_limit = {
                "limit": self.limit,
                "remaining": remaining,
                "reset": reset_time,
                "window": self.window,
            }

            # Check if rate limit is exceeded
            if current > self.limit:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    limit=self.limit,
                    window=self.window,
                    current=current,
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Limit: {self.limit} requests per {self.window} seconds",
                    headers={
                        "X-RateLimit-Limit": str(self.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(self.window),
                    },
                )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open if Redis errors
            return True

    async def get_remaining(self, request: Request) -> tuple[int, int]:
        """
        Get remaining rate limit for a request.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (remaining, reset_time)
        """
        client_ip: str = request.client.host if request.client else "unknown"
        key: str = f"rate_limit:{client_ip}"

        redis_client = await self._get_redis()
        if redis_client is None:
            return self.limit, int(time.time()) + self.window

        try:
            current_raw = await redis_client.get(key)
            current: int | None = int(current_raw) if current_raw is not None else None
            if current is None:
                return self.limit, int(time.time()) + self.window

            current_int: int = int(current)
            remaining: int = max(0, self.limit - current_int)
            ttl: int = await redis_client.ttl(key)
            reset_time: int = int(time.time()) + max(0, ttl)

            return remaining, reset_time

        except Exception:
            return self.limit, int(time.time()) + self.window


# Default instance
rate_limiter: RateLimiter = RateLimiter()


# Dependency for FastAPI
async def get_rate_limiter() -> RateLimiter:
    """
    Dependency to get rate limiter instance.

    Returns:
        RateLimiter instance
    """
    return rate_limiter


__all__ = [
    "rate_limiter",
    "get_rate_limiter",
    "RateLimiter",
]
