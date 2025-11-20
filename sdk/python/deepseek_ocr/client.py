"""DeepSeek OCR API Client"""
import base64
import time
from pathlib import Path
from typing import Any, Optional, Union

import httpx

from .models import OCRResult, BatchJob, Schema, Model, JobStatus


class DeepSeekOCR:
    """Synchronous client for DeepSeek OCR API"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek-ocr.com",
        timeout: float = 120.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()

    def close(self):
        self._client.close()

    # OCR Methods
    def extract(
        self,
        image: Optional[Union[str, Path, bytes]] = None,
        image_url: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        schema_id: Optional[str] = None,
        model_id: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from an image.

        Args:
            image: Local file path, bytes, or base64 string
            image_url: URL of the image
            schema: JSON schema for structured output
            schema_id: ID of a saved schema
            model_id: ID of a registered model (BYOM)
            prompt: Custom extraction prompt

        Returns:
            OCRResult with extracted data
        """
        payload = {}

        if image_url:
            payload["image_url"] = image_url
        elif image:
            payload["image_base64"] = self._encode_image(image)

        if schema:
            payload["output_schema"] = schema
        if schema_id:
            payload["schema_id"] = schema_id
        if model_id:
            payload["model_id"] = model_id
        if prompt:
            payload["prompt"] = prompt

        response = self._client.post("/ocr/extract", json=payload)
        response.raise_for_status()
        return OCRResult(**response.json())

    def extract_async(
        self,
        image: Optional[Union[str, Path, bytes]] = None,
        image_url: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        schema_id: Optional[str] = None,
        model_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        """
        Start async extraction job.

        Returns:
            job_id for polling
        """
        payload = {}

        if image_url:
            payload["image_url"] = image_url
        elif image:
            payload["image_base64"] = self._encode_image(image)

        if schema:
            payload["output_schema"] = schema
        if schema_id:
            payload["schema_id"] = schema_id
        if model_id:
            payload["model_id"] = model_id

        params = {}
        if webhook_url:
            params["webhook_url"] = webhook_url

        response = self._client.post("/ocr/extract/async", json=payload, params=params)
        response.raise_for_status()
        return response.json()["job_id"]

    def get_job(self, job_id: str) -> dict:
        """Get job status and results"""
        response = self._client.get(f"/ocr/job/{job_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> OCRResult:
        """Wait for async job to complete"""
        start = time.time()
        while True:
            result = self.get_job(job_id)
            status = result.get("status")

            if status == JobStatus.COMPLETED:
                return OCRResult(**result)
            elif status == JobStatus.FAILED:
                raise Exception(f"Job failed: {result.get('error')}")

            if time.time() - start > timeout:
                raise TimeoutError(f"Job {job_id} did not complete in {timeout}s")

            time.sleep(poll_interval)

    def batch(
        self,
        source_bucket: str,
        source_prefix: str,
        output_bucket: str,
        output_prefix: str,
        schema: Optional[dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        """Submit batch processing job"""
        payload = {
            "source_bucket": source_bucket,
            "source_prefix": source_prefix,
            "output_bucket": output_bucket,
            "output_prefix": output_prefix,
        }
        if schema:
            payload["output_schema"] = schema

        params = {}
        if webhook_url:
            params["webhook_url"] = webhook_url

        response = self._client.post("/ocr/batch", json=payload, params=params)
        response.raise_for_status()
        return response.json()["job_id"]

    # Schema Methods
    def create_schema(
        self,
        name: str,
        json_schema: dict[str, Any],
        description: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> Schema:
        """Create a new extraction schema"""
        payload = {
            "name": name,
            "json_schema": json_schema,
        }
        if description:
            payload["description"] = description
        if prompt_template:
            payload["prompt_template"] = prompt_template

        response = self._client.post("/schemas", json=payload)
        response.raise_for_status()
        return Schema(**response.json())

    def list_schemas(self) -> list[Schema]:
        """List all schemas"""
        response = self._client.get("/schemas")
        response.raise_for_status()
        return [Schema(**s) for s in response.json()]

    def get_schema(self, schema_id: str) -> Schema:
        """Get a schema by ID"""
        response = self._client.get(f"/schemas/{schema_id}")
        response.raise_for_status()
        return Schema(**response.json())

    def delete_schema(self, schema_id: str) -> bool:
        """Delete a schema"""
        response = self._client.delete(f"/schemas/{schema_id}")
        response.raise_for_status()
        return True

    # Model Methods (BYOM)
    def register_model(
        self,
        name: str,
        source: str,
        model_id: str,
        hf_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        gpu_memory_utilization: float = 0.85,
        max_model_len: int = 4096,
        is_default: bool = False,
    ) -> Model:
        """Register a custom model"""
        payload = {
            "name": name,
            "source": source,
            "model_id": model_id,
            "gpu_memory_utilization": gpu_memory_utilization,
            "max_model_len": max_model_len,
            "is_default": is_default,
        }
        if hf_token:
            payload["hf_token"] = hf_token
        if endpoint_url:
            payload["endpoint_url"] = endpoint_url
        if api_key:
            payload["api_key"] = api_key

        response = self._client.post("/models", json=payload)
        response.raise_for_status()
        return Model(**response.json())

    def list_models(self) -> list[Model]:
        """List all registered models"""
        response = self._client.get("/models")
        response.raise_for_status()
        return [Model(**m) for m in response.json()]

    def delete_model(self, model_id: str) -> bool:
        """Delete a model"""
        response = self._client.delete(f"/models/{model_id}")
        response.raise_for_status()
        return True

    def load_model(self, model_id: str) -> bool:
        """Pre-load a model into memory"""
        response = self._client.post(f"/models/{model_id}/load")
        response.raise_for_status()
        return True

    # Health
    def health(self) -> dict:
        """Check API health"""
        response = self._client.get("/health")
        response.raise_for_status()
        return response.json()

    # Utilities
    def _encode_image(self, image: Union[str, Path, bytes]) -> str:
        """Encode image to base64"""
        if isinstance(image, bytes):
            return base64.b64encode(image).decode()
        elif isinstance(image, (str, Path)):
            path = Path(image)
            if path.exists():
                return base64.b64encode(path.read_bytes()).decode()
            # Assume it's already base64
            return str(image)
        raise ValueError(f"Invalid image type: {type(image)}")


class AsyncDeepSeekOCR:
    """Async client for DeepSeek OCR API"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek-ocr.com",
        timeout: float = 120.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def close(self):
        await self._client.aclose()

    async def extract(
        self,
        image: Optional[Union[str, Path, bytes]] = None,
        image_url: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        schema_id: Optional[str] = None,
        model_id: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> OCRResult:
        """Extract text from an image"""
        payload = {}

        if image_url:
            payload["image_url"] = image_url
        elif image:
            payload["image_base64"] = self._encode_image(image)

        if schema:
            payload["output_schema"] = schema
        if schema_id:
            payload["schema_id"] = schema_id
        if model_id:
            payload["model_id"] = model_id
        if prompt:
            payload["prompt"] = prompt

        response = await self._client.post("/ocr/extract", json=payload)
        response.raise_for_status()
        return OCRResult(**response.json())

    async def extract_async(
        self,
        image: Optional[Union[str, Path, bytes]] = None,
        image_url: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        """Start async extraction job"""
        payload = {}

        if image_url:
            payload["image_url"] = image_url
        elif image:
            payload["image_base64"] = self._encode_image(image)

        if schema:
            payload["output_schema"] = schema

        params = {}
        if webhook_url:
            params["webhook_url"] = webhook_url

        response = await self._client.post("/ocr/extract/async", json=payload, params=params)
        response.raise_for_status()
        return response.json()["job_id"]

    async def get_job(self, job_id: str) -> dict:
        """Get job status"""
        response = await self._client.get(f"/ocr/job/{job_id}")
        response.raise_for_status()
        return response.json()

    async def health(self) -> dict:
        """Check API health"""
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    def _encode_image(self, image: Union[str, Path, bytes]) -> str:
        """Encode image to base64"""
        if isinstance(image, bytes):
            return base64.b64encode(image).decode()
        elif isinstance(image, (str, Path)):
            path = Path(image)
            if path.exists():
                return base64.b64encode(path.read_bytes()).decode()
            return str(image)
        raise ValueError(f"Invalid image type: {type(image)}")
