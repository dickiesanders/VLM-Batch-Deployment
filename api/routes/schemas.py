import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from api.models.tenant import Schema, SchemaCreate, SchemaUpdate

router = APIRouter(prefix="/schemas", tags=["schemas"])

# In-memory storage (use PostgreSQL/DynamoDB in production)
_schemas: dict[str, Schema] = {}


async def get_tenant_id(x_api_key: str = Header(...)) -> str:
    """
    Extract tenant ID from API key.

    In production, this would:
    1. Validate the API key against database
    2. Return the associated tenant_id
    3. Check rate limits and quotas
    """
    # Placeholder - implement proper auth
    # Format: tenant_id:secret_key
    if ":" in x_api_key:
        return x_api_key.split(":")[0]
    return "default-tenant"


@router.post("", response_model=Schema)
async def create_schema(
    request: SchemaCreate,
    tenant_id: str = Depends(get_tenant_id),
) -> Schema:
    """Create a new extraction schema for the tenant"""
    schema_id = str(uuid.uuid4())

    schema = Schema(
        id=schema_id,
        tenant_id=tenant_id,
        name=request.name,
        description=request.description,
        json_schema=request.json_schema,
        prompt_template=request.prompt_template,
    )

    _schemas[schema_id] = schema
    return schema


@router.get("", response_model=list[Schema])
async def list_schemas(
    tenant_id: str = Depends(get_tenant_id),
) -> list[Schema]:
    """List all schemas for the tenant"""
    return [s for s in _schemas.values() if s.tenant_id == tenant_id]


@router.get("/{schema_id}", response_model=Schema)
async def get_schema(
    schema_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> Schema:
    """Get a specific schema by ID"""
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail="Schema not found")

    schema = _schemas[schema_id]
    if schema.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return schema


@router.put("/{schema_id}", response_model=Schema)
async def update_schema(
    schema_id: str,
    request: SchemaUpdate,
    tenant_id: str = Depends(get_tenant_id),
) -> Schema:
    """Update an existing schema"""
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail="Schema not found")

    schema = _schemas[schema_id]
    if schema.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    if request.name is not None:
        schema.name = request.name
    if request.description is not None:
        schema.description = request.description
    if request.json_schema is not None:
        schema.json_schema = request.json_schema
    if request.prompt_template is not None:
        schema.prompt_template = request.prompt_template

    schema.updated_at = datetime.utcnow()
    return schema


@router.delete("/{schema_id}")
async def delete_schema(
    schema_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a schema"""
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail="Schema not found")

    schema = _schemas[schema_id]
    if schema.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    del _schemas[schema_id]
    return {"deleted": True}


# Helper for OCR routes to use saved schemas
def get_schema_by_id(schema_id: str, tenant_id: str) -> Optional[Schema]:
    """Get schema by ID for use in OCR extraction"""
    if schema_id not in _schemas:
        return None
    schema = _schemas[schema_id]
    if schema.tenant_id != tenant_id:
        return None
    return schema
