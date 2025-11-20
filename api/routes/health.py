import torch
from fastapi import APIRouter

from api.models import HealthResponse
from api.services.ocr_engine import get_engine

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    engine = get_engine()

    return HealthResponse(
        status="healthy",
        model_loaded=engine.is_loaded,
        gpu_available=torch.cuda.is_available(),
        version="1.0.0",
    )


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes/Cloud Run"""
    engine = get_engine()
    if not engine.is_loaded:
        return {"ready": False, "reason": "Model not loaded"}
    return {"ready": True}
