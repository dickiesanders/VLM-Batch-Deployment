"""Model registry for BYOM (Bring Your Own Model) support"""
import logging
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelSource(str, Enum):
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    EXTERNAL = "external"


class ModelConfig(BaseModel):
    """Configuration for a registered model"""
    id: str
    tenant_id: str
    name: str
    source: ModelSource
    model_id: str  # HF model ID or local path
    description: Optional[str] = None

    # Authentication
    hf_token: Optional[str] = None  # For gated HF models
    api_key: Optional[str] = None   # For external endpoints

    # For external endpoints
    endpoint_url: Optional[str] = None

    # GPU configuration
    gpu_memory_utilization: float = 0.85
    max_model_len: int = 4096
    max_num_seqs: int = 4

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    is_default: bool = False

    # Usage tracking
    total_requests: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-fine-tuned-ocr",
                "source": "huggingface",
                "model_id": "myorg/custom-vlm",
                "hf_token": "hf_xxx",
                "gpu_memory_utilization": 0.8,
                "max_model_len": 8192
            }
        }


class ModelCreate(BaseModel):
    """Request to register a new model"""
    name: str
    source: ModelSource
    model_id: str
    description: Optional[str] = None
    hf_token: Optional[str] = None
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    gpu_memory_utilization: float = 0.85
    max_model_len: int = 4096
    max_num_seqs: int = 4
    is_default: bool = False


class ModelUpdate(BaseModel):
    """Request to update a model"""
    name: Optional[str] = None
    description: Optional[str] = None
    hf_token: Optional[str] = None
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    gpu_memory_utilization: Optional[float] = None
    max_model_len: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ModelRegistry:
    """Registry for managing tenant models"""

    def __init__(self):
        self._models: dict[str, ModelConfig] = {}
        self._loaded_engines: dict[str, Any] = {}  # Cache of loaded vLLM engines

    def register(
        self,
        model_id: str,
        tenant_id: str,
        config: ModelCreate,
    ) -> ModelConfig:
        """Register a new model for a tenant"""
        model = ModelConfig(
            id=model_id,
            tenant_id=tenant_id,
            **config.model_dump(),
        )

        # If this is set as default, unset other defaults for tenant
        if model.is_default:
            for m in self._models.values():
                if m.tenant_id == tenant_id and m.is_default:
                    m.is_default = False

        self._models[model_id] = model
        logger.info(f"Registered model {model.name} for tenant {tenant_id}")
        return model

    def get(self, model_id: str, tenant_id: str) -> Optional[ModelConfig]:
        """Get a model by ID"""
        model = self._models.get(model_id)
        if model and model.tenant_id == tenant_id:
            return model
        return None

    def get_default(self, tenant_id: str) -> Optional[ModelConfig]:
        """Get the default model for a tenant"""
        for model in self._models.values():
            if model.tenant_id == tenant_id and model.is_default and model.is_active:
                return model
        return None

    def list(self, tenant_id: str) -> list[ModelConfig]:
        """List all models for a tenant"""
        return [
            m for m in self._models.values()
            if m.tenant_id == tenant_id
        ]

    def update(
        self,
        model_id: str,
        tenant_id: str,
        updates: ModelUpdate,
    ) -> Optional[ModelConfig]:
        """Update a model configuration"""
        model = self.get(model_id, tenant_id)
        if not model:
            return None

        update_data = updates.model_dump(exclude_unset=True)

        # Handle default flag
        if update_data.get("is_default"):
            for m in self._models.values():
                if m.tenant_id == tenant_id and m.is_default:
                    m.is_default = False

        for key, value in update_data.items():
            setattr(model, key, value)

        # Invalidate cached engine if config changed
        if model_id in self._loaded_engines:
            del self._loaded_engines[model_id]

        return model

    def delete(self, model_id: str, tenant_id: str) -> bool:
        """Delete a model"""
        model = self.get(model_id, tenant_id)
        if not model:
            return False

        # Clean up cached engine
        if model_id in self._loaded_engines:
            del self._loaded_engines[model_id]

        del self._models[model_id]
        return True

    def increment_usage(self, model_id: str) -> None:
        """Increment usage counter for a model"""
        if model_id in self._models:
            self._models[model_id].total_requests += 1

    def get_engine(self, model_id: str, tenant_id: str):
        """Get or load a vLLM engine for a model"""
        model = self.get(model_id, tenant_id)
        if not model:
            return None

        # Return cached engine if available
        if model_id in self._loaded_engines:
            return self._loaded_engines[model_id]

        # For external endpoints, return endpoint config
        if model.source == ModelSource.EXTERNAL:
            return {
                "type": "external",
                "endpoint_url": model.endpoint_url,
                "api_key": model.api_key,
            }

        # Load vLLM engine for HuggingFace/local models
        from vllm import LLM

        logger.info(f"Loading model {model.name} ({model.model_id})")

        engine = LLM(
            model=model.model_id,
            gpu_memory_utilization=model.gpu_memory_utilization,
            max_num_seqs=model.max_num_seqs,
            max_model_len=model.max_model_len,
            trust_remote_code=True,
            token=model.hf_token,
        )

        self._loaded_engines[model_id] = engine
        logger.info(f"Model {model.name} loaded successfully")

        return engine


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
