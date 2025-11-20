"""DeepSeek OCR Python SDK"""
from .client import DeepSeekOCR, AsyncDeepSeekOCR
from .models import (
    OCRResult,
    BatchJob,
    Schema,
    Model,
    JobStatus,
)

__version__ = "0.1.0"
__all__ = [
    "DeepSeekOCR",
    "AsyncDeepSeekOCR",
    "OCRResult",
    "BatchJob",
    "Schema",
    "Model",
    "JobStatus",
]
