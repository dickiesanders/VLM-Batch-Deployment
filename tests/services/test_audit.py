"""Tests for audit logging service"""
import pytest
from datetime import datetime, timedelta

from api.services.audit import AuditLogger, AuditAction


class TestAuditLogger:
    """Test audit logger functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.logger = AuditLogger()
        self.tenant_id = "test-tenant"

    @pytest.mark.asyncio
    async def test_log_event(self):
        """Test logging an audit event"""
        log = await self.logger.log(
            action=AuditAction.API_KEY_CREATED,
            tenant_id=self.tenant_id,
            user_id="user-123",
            resource_type="api_key",
            resource_id="key-456"
        )

        assert log.id is not None
        assert log.action == AuditAction.API_KEY_CREATED
        assert log.tenant_id == self.tenant_id
        assert log.success is True

    @pytest.mark.asyncio
    async def test_log_failure(self):
        """Test logging a failed event"""
        log = await self.logger.log(
            action=AuditAction.EXTRACTION_FAILED,
            tenant_id=self.tenant_id,
            success=False,
            error_message="Model not loaded"
        )

        assert log.success is False
        assert log.error_message == "Model not loaded"

    @pytest.mark.asyncio
    async def test_log_with_metadata(self):
        """Test logging with metadata"""
        log = await self.logger.log(
            action=AuditAction.BATCH_COMPLETED,
            tenant_id=self.tenant_id,
            metadata={
                "total_files": 100,
                "processed": 95,
                "failed": 5
            }
        )

        assert log.metadata["total_files"] == 100
        assert log.metadata["processed"] == 95

    @pytest.mark.asyncio
    async def test_query_by_tenant(self):
        """Test querying logs by tenant"""
        # Log events for different tenants
        await self.logger.log(
            action=AuditAction.LOGIN,
            tenant_id="tenant-a"
        )
        await self.logger.log(
            action=AuditAction.LOGIN,
            tenant_id="tenant-b"
        )

        logs = await self.logger.query(tenant_id="tenant-a")
        assert all(log.tenant_id == "tenant-a" for log in logs)

    @pytest.mark.asyncio
    async def test_query_by_action(self):
        """Test querying logs by action"""
        await self.logger.log(
            action=AuditAction.SCHEMA_CREATED,
            tenant_id=self.tenant_id
        )
        await self.logger.log(
            action=AuditAction.SCHEMA_DELETED,
            tenant_id=self.tenant_id
        )

        logs = await self.logger.query(
            tenant_id=self.tenant_id,
            action=AuditAction.SCHEMA_CREATED
        )
        assert all(log.action == AuditAction.SCHEMA_CREATED for log in logs)

    @pytest.mark.asyncio
    async def test_query_by_user(self):
        """Test querying logs by user"""
        await self.logger.log(
            action=AuditAction.EXTRACTION_COMPLETED,
            tenant_id=self.tenant_id,
            user_id="user-specific"
        )

        logs = await self.logger.query(
            tenant_id=self.tenant_id,
            user_id="user-specific"
        )
        assert all(log.user_id == "user-specific" for log in logs)

    @pytest.mark.asyncio
    async def test_query_by_resource(self):
        """Test querying logs by resource"""
        await self.logger.log(
            action=AuditAction.MODEL_LOADED,
            tenant_id=self.tenant_id,
            resource_type="model",
            resource_id="model-123"
        )

        logs = await self.logger.query(
            tenant_id=self.tenant_id,
            resource_type="model",
            resource_id="model-123"
        )
        assert len(logs) > 0
        assert logs[0].resource_id == "model-123"

    @pytest.mark.asyncio
    async def test_query_by_time_range(self):
        """Test querying logs by time range"""
        await self.logger.log(
            action=AuditAction.PAYMENT_SUCCEEDED,
            tenant_id=self.tenant_id
        )

        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow() + timedelta(hours=1)

        logs = await self.logger.query(
            tenant_id=self.tenant_id,
            start_time=start_time,
            end_time=end_time
        )
        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_query_by_success(self):
        """Test querying logs by success status"""
        await self.logger.log(
            action=AuditAction.PAYMENT_FAILED,
            tenant_id=self.tenant_id,
            success=False
        )

        logs = await self.logger.query(
            tenant_id=self.tenant_id,
            success=False
        )
        assert all(log.success is False for log in logs)

    @pytest.mark.asyncio
    async def test_query_pagination(self):
        """Test query pagination"""
        # Log multiple events
        for i in range(10):
            await self.logger.log(
                action=AuditAction.EXTRACTION_COMPLETED,
                tenant_id=self.tenant_id
            )

        logs = await self.logger.query(
            tenant_id=self.tenant_id,
            limit=5,
            offset=0
        )
        assert len(logs) == 5

    @pytest.mark.asyncio
    async def test_export_json(self):
        """Test exporting logs as JSON"""
        await self.logger.log(
            action=AuditAction.TEAM_CREATED,
            tenant_id=self.tenant_id
        )

        export = await self.logger.export(
            tenant_id=self.tenant_id,
            format="json"
        )

        assert isinstance(export, str)
        assert "team.created" in export

    @pytest.mark.asyncio
    async def test_export_csv(self):
        """Test exporting logs as CSV"""
        await self.logger.log(
            action=AuditAction.MEMBER_INVITED,
            tenant_id=self.tenant_id
        )

        export = await self.logger.export(
            tenant_id=self.tenant_id,
            format="csv"
        )

        assert isinstance(export, str)
        assert "timestamp" in export
        assert "action" in export

    def test_get_stats(self):
        """Test getting audit statistics"""
        stats = self.logger.get_stats(self.tenant_id)

        assert "total_events" in stats
        assert "error_count" in stats
        assert "action_counts" in stats

    @pytest.mark.asyncio
    async def test_log_trimming(self):
        """Test that old logs are trimmed when limit exceeded"""
        self.logger._max_logs = 10

        for i in range(15):
            await self.logger.log(
                action=AuditAction.EXTRACTION_COMPLETED,
                tenant_id=self.tenant_id
            )

        assert len(self.logger._logs) == 10
