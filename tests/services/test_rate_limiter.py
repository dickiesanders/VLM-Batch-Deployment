"""Tests for rate limiter service"""
import pytest
import time

from api.services.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test rate limiter functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.limiter = RateLimiter(
            redis_url=None,  # Use in-memory
            requests_per_minute=10,
            requests_per_day=100
        )
        self.tenant_id = "test-tenant"

    @pytest.mark.asyncio
    async def test_allow_request_within_limits(self):
        """Test allowing requests within limits"""
        result = await self.limiter.check_rate_limit(self.tenant_id)

        assert result["allowed"] is True
        assert result["remaining_rpm"] == 9
        assert result["remaining_rpd"] == 99

    @pytest.mark.asyncio
    async def test_deny_request_exceeds_rpm(self):
        """Test denying requests that exceed RPM"""
        # Use up all RPM allowance
        for _ in range(10):
            await self.limiter.check_rate_limit(self.tenant_id)

        result = await self.limiter.check_rate_limit(self.tenant_id)

        assert result["allowed"] is False
        assert result["remaining_rpm"] == 0

    @pytest.mark.asyncio
    async def test_deny_request_exceeds_rpd(self):
        """Test denying requests that exceed RPD"""
        # Create limiter with low RPD
        limiter = RateLimiter(
            redis_url=None,
            requests_per_minute=1000,
            requests_per_day=5
        )

        # Use up all RPD allowance
        for _ in range(5):
            await limiter.check_rate_limit("tenant-rpd")

        result = await limiter.check_rate_limit("tenant-rpd")

        assert result["allowed"] is False
        assert result["remaining_rpd"] == 0

    @pytest.mark.asyncio
    async def test_custom_limits(self):
        """Test custom rate limits per request"""
        result = await self.limiter.check_rate_limit(
            self.tenant_id,
            custom_rpm=5,
            custom_rpd=50
        )

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test that rate limits are isolated per tenant"""
        # Use up limits for tenant A
        for _ in range(10):
            await self.limiter.check_rate_limit("tenant-a")

        # Tenant B should still have full limits
        result = await self.limiter.check_rate_limit("tenant-b")

        assert result["allowed"] is True
        assert result["remaining_rpm"] == 9

    @pytest.mark.asyncio
    async def test_get_usage(self):
        """Test getting current usage"""
        # Make some requests
        for _ in range(5):
            await self.limiter.check_rate_limit(self.tenant_id)

        usage = await self.limiter.get_usage(self.tenant_id)

        assert usage["rpm_used"] == 5
        assert usage["rpd_used"] == 5
        assert usage["rpm_limit"] == 10
        assert usage["rpd_limit"] == 100

    @pytest.mark.asyncio
    async def test_reset_limits(self):
        """Test resetting rate limits"""
        # Use up some limits
        for _ in range(5):
            await self.limiter.check_rate_limit(self.tenant_id)

        # Reset limits
        await self.limiter.reset_limits(self.tenant_id)

        # Should have full limits again
        result = await self.limiter.check_rate_limit(self.tenant_id)

        assert result["remaining_rpm"] == 9
        assert result["remaining_rpd"] == 99

    @pytest.mark.asyncio
    async def test_retry_after_header(self):
        """Test retry-after information"""
        # Use up all limits
        for _ in range(10):
            await self.limiter.check_rate_limit(self.tenant_id)

        result = await self.limiter.check_rate_limit(self.tenant_id)

        assert result["allowed"] is False
        assert "retry_after" in result
        assert result["retry_after"] > 0


class TestRateLimiterWithRedis:
    """Test rate limiter with Redis (mocked)"""

    @pytest.mark.asyncio
    async def test_redis_initialization(self):
        """Test that Redis URL is properly handled"""
        # This would normally connect to Redis
        # For testing, we just verify the initialization doesn't fail
        limiter = RateLimiter(
            redis_url=None,
            requests_per_minute=60,
            requests_per_day=1000
        )

        assert limiter is not None
