from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class Schema(BaseModel):
    """User-defined extraction schema"""
    id: str
    name: str
    description: Optional[str] = None
    tenant_id: str
    json_schema: dict[str, Any]
    prompt_template: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "invoice-v1",
                "name": "Invoice Schema",
                "description": "Extract invoice data",
                "tenant_id": "tenant-123",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string"},
                        "vendor": {"type": "string"},
                        "total": {"type": "number"},
                        "line_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "unit_price": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        }


class SchemaCreate(BaseModel):
    """Request to create a new schema"""
    name: str
    description: Optional[str] = None
    json_schema: dict[str, Any]
    prompt_template: Optional[str] = None


class SchemaUpdate(BaseModel):
    """Request to update a schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    json_schema: Optional[dict[str, Any]] = None
    prompt_template: Optional[str] = None


class APIKey(BaseModel):
    """API key for authentication"""
    key: str
    tenant_id: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class Tenant(BaseModel):
    """Tenant/organization in the SaaS platform"""
    id: str
    name: str
    email: str
    plan: str = "free"  # free, pro, enterprise
    created_at: datetime = Field(default_factory=datetime.utcnow)
    usage_quota: int = 1000  # Monthly requests
    usage_current: int = 0
