"""Model registry for BYOM (Bring Your Own Model) support"""
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# GCS model cache directory
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/tmp/model-cache")


class ModelSource(str, Enum):
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    EXTERNAL = "external"
    GCS = "gcs"  # Google Cloud Storage


class ModelLoader:
    """Utility class for loading models from various sources"""

    @staticmethod
    def download_from_gcs(gcs_path: str, local_path: str) -> str:
        """Download model from GCS to local cache

        Args:
            gcs_path: GCS path like gs://bucket/path/to/model
            local_path: Local directory to download to

        Returns:
            Local path to downloaded model
        """
        from google.cloud import storage

        # Parse GCS path
        if not gcs_path.startswith("gs://"):
            raise ValueError(f"Invalid GCS path: {gcs_path}")

        path_parts = gcs_path[5:].split("/", 1)
        bucket_name = path_parts[0]
        prefix = path_parts[1] if len(path_parts) > 1 else ""

        # Create local directory
        local_dir = Path(local_path)
        local_dir.mkdir(parents=True, exist_ok=True)

        # Download from GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        downloaded_files = 0
        for blob in blobs:
            # Get relative path from prefix
            rel_path = blob.name[len(prefix):].lstrip("/")
            if not rel_path:
                continue

            local_file = local_dir / rel_path
            local_file.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading {blob.name} to {local_file}")
            blob.download_to_filename(str(local_file))
            downloaded_files += 1

        logger.info(f"Downloaded {downloaded_files} files from {gcs_path}")
        return str(local_dir)

    @staticmethod
    def download_from_huggingface(model_id: str, token: Optional[str] = None) -> str:
        """Download model from HuggingFace Hub

        Args:
            model_id: HuggingFace model ID
            token: HF token for gated models

        Returns:
            Local path to downloaded model
        """
        from huggingface_hub import snapshot_download

        logger.info(f"Downloading model {model_id} from HuggingFace")

        local_dir = snapshot_download(
            repo_id=model_id,
            token=token,
            cache_dir=MODEL_CACHE_DIR,
        )

        logger.info(f"Model downloaded to {local_dir}")
        return local_dir

    @staticmethod
    def is_model_cached(model_id: str, source: "ModelSource") -> bool:
        """Check if model is already cached locally"""
        if source == ModelSource.GCS:
            cache_path = Path(MODEL_CACHE_DIR) / model_id.replace("gs://", "").replace("/", "_")
            return cache_path.exists()
        elif source == ModelSource.HUGGINGFACE:
            # HuggingFace uses its own cache management
            cache_path = Path(MODEL_CACHE_DIR) / f"models--{model_id.replace('/', '--')}"
            return cache_path.exists()
        return False


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

        # Determine model path based on source
        model_path = model.model_id

        if model.source == ModelSource.GCS:
            # Download from GCS if not cached
            cache_name = model.model_id.replace("gs://", "").replace("/", "_")
            local_path = str(Path(MODEL_CACHE_DIR) / cache_name)

            if not Path(local_path).exists():
                logger.info(f"Downloading model from GCS: {model.model_id}")
                model_path = ModelLoader.download_from_gcs(model.model_id, local_path)
            else:
                logger.info(f"Using cached model from {local_path}")
                model_path = local_path

        elif model.source == ModelSource.HUGGINGFACE:
            # HuggingFace models are downloaded automatically by vLLM
            # but we can pre-download for better control
            if not ModelLoader.is_model_cached(model.model_id, ModelSource.HUGGINGFACE):
                logger.info(f"Pre-downloading model from HuggingFace: {model.model_id}")
                model_path = ModelLoader.download_from_huggingface(
                    model.model_id,
                    model.hf_token
                )
            else:
                model_path = model.model_id

        # Load vLLM engine
        from vllm import LLM

        logger.info(f"Loading model {model.name} from {model_path}")

        engine = LLM(
            model=model_path,
            gpu_memory_utilization=model.gpu_memory_utilization,
            max_num_seqs=model.max_num_seqs,
            max_model_len=model.max_model_len,
            trust_remote_code=True,
            token=model.hf_token if model.source == ModelSource.HUGGINGFACE else None,
        )

        self._loaded_engines[model_id] = engine
        logger.info(f"Model {model.name} loaded successfully")

        return engine

    def preload_model(self, model_id: str, tenant_id: str) -> bool:
        """Pre-download model to cache without loading into GPU memory

        Useful for warming up models before they're needed.
        """
        model = self.get(model_id, tenant_id)
        if not model:
            return False

        if model.source == ModelSource.GCS:
            cache_name = model.model_id.replace("gs://", "").replace("/", "_")
            local_path = str(Path(MODEL_CACHE_DIR) / cache_name)
            if not Path(local_path).exists():
                ModelLoader.download_from_gcs(model.model_id, local_path)
            return True

        elif model.source == ModelSource.HUGGINGFACE:
            if not ModelLoader.is_model_cached(model.model_id, ModelSource.HUGGINGFACE):
                ModelLoader.download_from_huggingface(model.model_id, model.hf_token)
            return True

        return True


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
