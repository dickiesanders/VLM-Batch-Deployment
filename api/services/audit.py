"""Audit logging for compliance and security"""
import json
import logging
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    # Auth
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    API_KEY_CREATED = "auth.api_key_created"
    API_KEY_ROTATED = "auth.api_key_rotated"
    API_KEY_REVOKED = "auth.api_key_revoked"

    # OCR
    EXTRACTION_STARTED = "ocr.extraction_started"
    EXTRACTION_COMPLETED = "ocr.extraction_completed"
    EXTRACTION_FAILED = "ocr.extraction_failed"
    BATCH_STARTED = "ocr.batch_started"
    BATCH_COMPLETED = "ocr.batch_completed"

    # Schemas
    SCHEMA_CREATED = "schema.created"
    SCHEMA_UPDATED = "schema.updated"
    SCHEMA_DELETED = "schema.deleted"

    # Models
    MODEL_REGISTERED = "model.registered"
    MODEL_LOADED = "model.loaded"
    MODEL_DELETED = "model.deleted"

    # Teams
    TEAM_CREATED = "team.created"
    TEAM_DELETED = "team.deleted"
    MEMBER_INVITED = "team.member_invited"
    MEMBER_JOINED = "team.member_joined"
    MEMBER_REMOVED = "team.member_removed"
    MEMBER_ROLE_CHANGED = "team.member_role_changed"

    # Billing
    SUBSCRIPTION_CREATED = "billing.subscription_created"
    SUBSCRIPTION_CANCELLED = "billing.subscription_cancelled"
    PAYMENT_SUCCEEDED = "billing.payment_succeeded"
    PAYMENT_FAILED = "billing.payment_failed"


class AuditLog(BaseModel):
    """Audit log entry"""
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: AuditAction
    tenant_id: str
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None


class AuditLogger:
    """Audit logging service"""

    def __init__(self):
        self._logs: list[AuditLog] = []
        self._max_logs = 100000  # In-memory limit

    async def log(
        self,
        action: AuditAction,
        tenant_id: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Log an audit event"""
        import uuid

        log_entry = AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            success=success,
            error_message=error_message,
        )

        self._logs.append(log_entry)

        # Trim old logs if exceeding limit
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]

        # Also log to standard logger
        log_msg = f"AUDIT: {action.value} tenant={tenant_id}"
        if resource_type:
            log_msg += f" resource={resource_type}/{resource_id}"
        if not success:
            log_msg += f" error={error_message}"

        logger.info(log_msg)

        return log_entry

    async def query(
        self,
        tenant_id: str,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query audit logs with filters"""
        results = []

        for log in reversed(self._logs):
            # Apply filters
            if log.tenant_id != tenant_id:
                continue
            if action and log.action != action:
                continue
            if user_id and log.user_id != user_id:
                continue
            if resource_type and log.resource_type != resource_type:
                continue
            if resource_id and log.resource_id != resource_id:
                continue
            if start_time and log.timestamp < start_time:
                continue
            if end_time and log.timestamp > end_time:
                continue
            if success is not None and log.success != success:
                continue

            results.append(log)

        # Apply pagination
        return results[offset:offset + limit]

    async def export(
        self,
        tenant_id: str,
        format: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Export audit logs for compliance"""
        logs = await self.query(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            limit=self._max_logs,
        )

        if format == "json":
            return json.dumps(
                [log.model_dump() for log in logs],
                default=str,
                indent=2,
            )
        elif format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                "timestamp", "action", "user_id", "resource_type",
                "resource_id", "ip_address", "success", "error_message"
            ])

            # Rows
            for log in logs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    log.action.value,
                    log.user_id,
                    log.resource_type,
                    log.resource_id,
                    log.ip_address,
                    log.success,
                    log.error_message,
                ])

            return output.getvalue()

        raise ValueError(f"Unknown format: {format}")

    def get_stats(self, tenant_id: str) -> dict:
        """Get audit log statistics"""
        tenant_logs = [l for l in self._logs if l.tenant_id == tenant_id]

        action_counts: dict[str, int] = {}
        error_count = 0

        for log in tenant_logs:
            action_counts[log.action.value] = action_counts.get(log.action.value, 0) + 1
            if not log.success:
                error_count += 1

        return {
            "total_events": len(tenant_logs),
            "error_count": error_count,
            "action_counts": action_counts,
        }


# Global audit logger
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
