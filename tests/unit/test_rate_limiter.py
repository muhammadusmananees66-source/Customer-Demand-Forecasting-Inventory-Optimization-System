# tests/unit/test_rate_limiter.py - NEW FILE
"""
Unit tests for Rate Limiter module
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from src.serving.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test RateLimiter class"""

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.state = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_rate_limiter_success(self, mock_request):
        """Test successful rate limit check"""
        limiter = RateLimiter(limit=10, window=60)
        with patch("src.serving.rate_limiter.get_redis", return_value=AsyncMock()):
            result = await limiter(mock_request)
            assert result is True

    @pytest.mark.asyncio
    async def test_rate_limiter_exceeded(self, mock_request):
        """Test rate limit exceeded"""
        limiter = RateLimiter(limit=1, window=60)
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=2)

        with patch("src.serving.rate_limiter.get_redis", return_value=mock_redis):
            with pytest.raises(HTTPException) as exc:
                await limiter(mock_request)
            assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limiter_redis_unavailable(self, mock_request):
        """Test rate limiter when Redis is unavailable"""
        limiter = RateLimiter(limit=10, window=60)
        with patch("src.serving.rate_limiter.get_redis", return_value=None):
            result = await limiter(mock_request)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_remaining(self, mock_request):
        """Test get_remaining method"""
        limiter = RateLimiter(limit=10, window=60)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="5")
        mock_redis.ttl = AsyncMock(return_value=30)

        with patch("src.serving.rate_limiter.get_redis", return_value=mock_redis):
            remaining, reset = await limiter.get_remaining(mock_request)
            assert remaining == 5
            assert reset > 0

    @pytest.mark.asyncio
    async def test_get_remaining_no_redis(self, mock_request):
        """Test get_remaining when Redis is unavailable"""
        limiter = RateLimiter(limit=10, window=60)
        with patch("src.serving.rate_limiter.get_redis", return_value=None):
            remaining, reset = await limiter.get_remaining(mock_request)
            assert remaining == 10
            assert reset > 0
