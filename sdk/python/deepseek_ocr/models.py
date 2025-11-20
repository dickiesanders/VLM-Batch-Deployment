"""Data models for the SDK"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StructuredOutput(BaseModel):
    """Extracted data from document"""
    data: dict[str, Any]
    confidence: Optional[float] = None
    raw_text: Optional[str] = None


class OCRResult(BaseModel):
    """Result from OCR extraction"""
    request_id: str
    status: JobStatus
    result: Optional[StructuredOutput] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None


class BatchJob(BaseModel):
    """Batch processing job"""
    job_id: str
    status: JobStatus
    total_documents: int
    processed_documents: int = 0
    results_url: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Schema(BaseModel):
    """Extraction schema"""
    id: str
    name: str
    description: Optional[str] = None
    json_schema: dict[str, Any]
    prompt_template: Optional[str] = None
    created_at: Optional[datetime] = None


class Model(BaseModel):
    """Registered model"""
    id: str
    name: str
    source: str
    model_id: str
    description: Optional[str] = None
    gpu_memory_utilization: float = 0.85
    max_model_len: int = 4096
    is_active: bool = True
    is_default: bool = False
    total_requests: int = 0
    created_at: Optional[datetime] = None


class ABTestResult(BaseModel):
    """A/B test results"""
    test_id: str
    description: str
    total_requests: int
    variants: dict[str, dict[str, Any]]
