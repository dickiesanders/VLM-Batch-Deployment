"""Audit log routes"""
from datetime import datetime
from fastapi import APIRouter, Header, Response
from typing import Optional

from api.services.audit import get_audit_logger, AuditAction

router = APIRouter(prefix="/audit", tags=["audit"])


async def get_tenant_id(x_api_key: str = Header(...)) -> str:
    if ":" in x_api_key:
        return x_api_key.split(":")[0]
    return "default-tenant"


@router.get("/logs")
async def query_logs(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    success: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    x_api_key: str = Header(...),
):
    """Query audit logs"""
    tenant_id = await get_tenant_id(x_api_key)
    audit = get_audit_logger()

    action_enum = AuditAction(action) if action else None

    logs = await audit.query(
        tenant_id=tenant_id,
        action=action_enum,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
        success=success,
        limit=limit,
        offset=offset,
    )

    return {
        "logs": [log.model_dump() for log in logs],
        "count": len(logs),
    }


@router.get("/logs/export")
async def export_logs(
    format: str = "json",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    x_api_key: str = Header(...),
):
    """Export audit logs for compliance"""
    tenant_id = await get_tenant_id(x_api_key)
    audit = get_audit_logger()

    content = await audit.export(
        tenant_id=tenant_id,
        format=format,
        start_time=start_time,
        end_time=end_time,
    )

    media_type = "application/json" if format == "json" else "text/csv"
    filename = f"audit_logs_{tenant_id}.{format}"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/stats")
async def get_stats(x_api_key: str = Header(...)):
    """Get audit log statistics"""
    tenant_id = await get_tenant_id(x_api_key)
    audit = get_audit_logger()

    return audit.get_stats(tenant_id)
