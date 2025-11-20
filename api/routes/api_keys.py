"""API key management routes"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from api.services.api_keys import get_api_key_manager, KeyScope

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    name: str
    scopes: list[str] = ["read", "write"]
    expires_days: Optional[int] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_rpd: Optional[int] = None


class UpdateScopesRequest(BaseModel):
    scopes: list[str]


async def get_tenant_id(x_api_key: str = Header(...)) -> str:
    if ":" in x_api_key:
        return x_api_key.split(":")[0]
    return "default-tenant"


@router.post("")
async def create_key(
    request: CreateKeyRequest,
    x_api_key: str = Header(...),
):
    """
    Create a new API key.

    Returns the plaintext key once - store it securely!
    """
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    scopes = [KeyScope(s) for s in request.scopes]

    plaintext_key, api_key = manager.generate_key(
        tenant_id=tenant_id,
        name=request.name,
        scopes=scopes,
        expires_days=request.expires_days,
        rate_limit_rpm=request.rate_limit_rpm,
        rate_limit_rpd=request.rate_limit_rpd,
    )

    return {
        "key": plaintext_key,  # Only returned once!
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.key_prefix,
        "scopes": [s.value for s in api_key.scopes],
        "expires_at": api_key.expires_at,
        "created_at": api_key.created_at,
    }


@router.get("")
async def list_keys(x_api_key: str = Header(...)):
    """List all API keys for the tenant"""
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    keys = manager.list_keys(tenant_id)
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "prefix": k.key_prefix,
                "scopes": [s.value for s in k.scopes],
                "created_at": k.created_at,
                "expires_at": k.expires_at,
                "last_used_at": k.last_used_at,
                "is_active": k.is_active,
            }
            for k in keys
        ]
    }


@router.get("/{key_id}")
async def get_key(key_id: str, x_api_key: str = Header(...)):
    """Get API key details"""
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    key = manager.get_key(key_id, tenant_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    return {
        "id": key.id,
        "name": key.name,
        "prefix": key.key_prefix,
        "scopes": [s.value for s in key.scopes],
        "created_at": key.created_at,
        "expires_at": key.expires_at,
        "last_used_at": key.last_used_at,
        "is_active": key.is_active,
        "rate_limit_rpm": key.rate_limit_rpm,
        "rate_limit_rpd": key.rate_limit_rpd,
    }


@router.post("/{key_id}/rotate")
async def rotate_key(key_id: str, x_api_key: str = Header(...)):
    """
    Rotate an API key.

    Creates a new key and revokes the old one.
    Returns the new plaintext key once - store it securely!
    """
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    result = manager.rotate_key(key_id, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Key not found")

    plaintext_key, new_key = result

    return {
        "key": plaintext_key,  # Only returned once!
        "id": new_key.id,
        "name": new_key.name,
        "prefix": new_key.key_prefix,
        "scopes": [s.value for s in new_key.scopes],
        "old_key_id": key_id,
    }


@router.put("/{key_id}/scopes")
async def update_scopes(
    key_id: str,
    request: UpdateScopesRequest,
    x_api_key: str = Header(...),
):
    """Update API key scopes"""
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    scopes = [KeyScope(s) for s in request.scopes]
    key = manager.update_scopes(key_id, tenant_id, scopes)

    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    return {
        "id": key.id,
        "scopes": [s.value for s in key.scopes],
    }


@router.post("/{key_id}/revoke")
async def revoke_key(key_id: str, x_api_key: str = Header(...)):
    """Revoke an API key (can be re-enabled)"""
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    if not manager.revoke_key(key_id, tenant_id):
        raise HTTPException(status_code=404, detail="Key not found")

    return {"status": "revoked", "key_id": key_id}


@router.delete("/{key_id}")
async def delete_key(key_id: str, x_api_key: str = Header(...)):
    """Permanently delete an API key"""
    tenant_id = await get_tenant_id(x_api_key)
    manager = get_api_key_manager()

    if not manager.delete_key(key_id, tenant_id):
        raise HTTPException(status_code=404, detail="Key not found")

    return {"status": "deleted", "key_id": key_id}
