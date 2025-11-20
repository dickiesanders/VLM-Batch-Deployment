"""Routes for model management (BYOM)"""
import uuid
from fastapi import APIRouter, HTTPException, Header

from api.services.model_registry import (
    get_model_registry,
    ModelConfig,
    ModelCreate,
    ModelUpdate,
)

router = APIRouter(prefix="/models", tags=["models"])


async def get_tenant_id(x_api_key: str = Header(...)) -> str:
    """Extract tenant ID from API key"""
    if ":" in x_api_key:
        return x_api_key.split(":")[0]
    return "default-tenant"


@router.post("", response_model=dict)
async def register_model(
    request: ModelCreate,
    x_api_key: str = Header(...),
):
    """
    Register a custom model for your tenant.

    Supports:
    - HuggingFace models (public or gated with token)
    - Local model paths
    - External inference endpoints
    """
    tenant_id = await get_tenant_id(x_api_key)
    registry = get_model_registry()

    model_id = str(uuid.uuid4())
    model = registry.register(model_id, tenant_id, request)

    # Don't expose tokens in response
    response = model.model_dump()
    response.pop("hf_token", None)
    response.pop("api_key", None)

    return response


@router.get("", response_model=list)
async def list_models(x_api_key: str = Header(...)):
    """List all registered models for your tenant"""
    tenant_id = await get_tenant_id(x_api_key)
    registry = get_model_registry()

    models = registry.list(tenant_id)

    # Don't expose tokens
    return [
        {
            **m.model_dump(),
            "hf_token": "***" if m.hf_token else None,
            "api_key": "***" if m.api_key else None,
        }
        for m in models
    ]


@router.get("/{model_id}")
async def get_model(
    model_id: str,
    x_api_key: str = Header(...),
):
    """Get details of a registered model"""
    tenant_id = await get_tenant_id(x_api_key)
    registry = get_model_registry()

    model = registry.get(model_id, tenant_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    response = model.model_dump()
    response["hf_token"] = "***" if model.hf_token else None
    response["api_key"] = "***" if model.api_key else None

    return response


@router.put("/{model_id}")
async def update_model(
    model_id: str,
    request: ModelUpdate,
    x_api_key: str = Header(...),
):
    """Update a registered model"""
    tenant_id = await get_tenant_id(x_api_key)
    registry = get_model_registry()

    model = registry.update(model_id, tenant_id, request)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    response = model.model_dump()
    response["hf_token"] = "***" if model.hf_token else None
    response["api_key"] = "***" if model.api_key else None

    return response


@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    x_api_key: str = Header(...),
):
    """Delete a registered model"""
    tenant_id = await get_tenant_id(x_api_key)
    registry = get_model_registry()

    if not registry.delete(model_id, tenant_id):
        raise HTTPException(status_code=404, detail="Model not found")

    return {"deleted": True, "model_id": model_id}


@router.post("/{model_id}/load")
async def load_model(
    model_id: str,
    x_api_key: str = Header(...),
):
    """
    Pre-load a model into memory.

    This is useful for reducing first-request latency.
    Note: Loading models consumes GPU memory.
    """
    tenant_id = await get_tenant_id(x_api_key)
    registry = get_model_registry()

    model = registry.get(model_id, tenant_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        engine = registry.get_engine(model_id, tenant_id)
        if engine:
            return {"status": "loaded", "model_id": model_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to load model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")
