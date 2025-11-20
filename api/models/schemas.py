from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRRequest(BaseModel):
    """Request model for OCR extraction"""
    image_url: Optional[str] = Field(None, description="URL of image to process")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image")
    model_id: Optional[str] = Field(
        None,
        description="ID of a registered custom model (BYOM)"
    )
    schema_id: Optional[str] = Field(
        None,
        description="ID of a saved schema to use for extraction"
    )
    output_schema: Optional[dict[str, Any]] = Field(
        None,
        description="Inline JSON schema for structured output extraction"
    )
    prompt: Optional[str] = Field(
        None,
        description="Custom prompt for extraction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://example.com/invoice.png",
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string"},
                        "total": {"type": "number"},
                        "date": {"type": "string"}
                    }
                }
            }
        }


class StructuredOutput(BaseModel):
    """Extracted structured data from document"""
    data: dict[str, Any]
    confidence: Optional[float] = None
    raw_text: Optional[str] = None


class OCRResponse(BaseModel):
    """Response model for OCR extraction"""
    request_id: str
    status: JobStatus
    result: Optional[StructuredOutput] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BatchJob(BaseModel):
    """Batch job for async processing"""
    job_id: str
    status: JobStatus
    total_documents: int
    processed_documents: int = 0
    results_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class BatchRequest(BaseModel):
    """Request for batch processing"""
    source_bucket: str
    source_prefix: str
    output_bucket: str
    output_prefix: str
    output_schema: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    gpu_available: bool
    version: str
