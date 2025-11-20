"""A/B testing routes for model comparison"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.services.ab_testing import get_ab_manager, ModelVariant

router = APIRouter(prefix="/ab-tests", tags=["ab-testing"])


class VariantConfig(BaseModel):
    name: str
    model_name: str
    weight: float = 1.0
    config: Optional[dict] = None


class CreateTestRequest(BaseModel):
    test_id: str
    description: str = ""
    variants: list[VariantConfig]


@router.post("")
async def create_test(request: CreateTestRequest):
    """Create a new A/B test"""
    manager = get_ab_manager()

    variants = [
        ModelVariant(
            name=v.name,
            model_name=v.model_name,
            weight=v.weight,
            config=v.config or {},
        )
        for v in request.variants
    ]

    manager.create_test(
        test_id=request.test_id,
        variants=variants,
        description=request.description,
    )

    return {"status": "created", "test_id": request.test_id}


@router.get("")
async def list_tests():
    """List all A/B tests"""
    manager = get_ab_manager()
    return {"tests": manager.list_tests()}


@router.get("/{test_id}/results")
async def get_test_results(test_id: str):
    """Get results for an A/B test"""
    manager = get_ab_manager()
    results = manager.get_test_results(test_id)

    if not results:
        raise HTTPException(status_code=404, detail="Test not found")

    return results


@router.delete("/{test_id}")
async def deactivate_test(test_id: str):
    """Deactivate an A/B test"""
    manager = get_ab_manager()
    if not manager.deactivate_test(test_id):
        raise HTTPException(status_code=404, detail="Test not found")

    return {"status": "deactivated", "test_id": test_id}
