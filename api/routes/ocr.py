import time
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Header

from api.models import (
    OCRRequest,
    OCRResponse,
    JobStatus,
    StructuredOutput,
    BatchJob,
)
from api.models.schemas import BatchRequest
from api.services.ocr_engine import get_engine
from api.services.storage import LocalStorage, S3Storage
from api.routes.schemas import get_schema_by_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["ocr"])

# In-memory job tracking (use Redis/DB in production)
_jobs: dict[str, BatchJob] = {}

# Default storage (configure via environment)
_storage = LocalStorage()


@router.post("/extract", response_model=OCRResponse)
async def extract_text(
    request: OCRRequest,
    x_api_key: str = Header(default="default-tenant:key"),
) -> OCRResponse:
    """
    Synchronous OCR extraction endpoint.

    Extracts structured text from a document image. Supports:
    - Saved schemas via schema_id
    - Inline schemas via output_schema
    - Custom prompts
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Extract tenant_id from API key
    tenant_id = x_api_key.split(":")[0] if ":" in x_api_key else "default-tenant"

    try:
        engine = get_engine()
        if not engine.is_loaded:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded. Service is starting up."
            )

        # Load image
        image = await engine.load_image(
            image_url=request.image_url,
            image_base64=request.image_base64,
        )

        # Resolve schema - prefer schema_id over inline
        output_schema = request.output_schema
        prompt = request.prompt

        if request.schema_id:
            saved_schema = get_schema_by_id(request.schema_id, tenant_id)
            if saved_schema is None:
                raise HTTPException(status_code=404, detail="Schema not found")
            output_schema = saved_schema.json_schema
            if saved_schema.prompt_template:
                prompt = saved_schema.prompt_template

        # Extract data
        result = engine.extract(
            image=image,
            output_schema=output_schema,
            prompt=prompt,
        )

        processing_time = int((time.time() - start_time) * 1000)

        response = OCRResponse(
            request_id=request_id,
            status=JobStatus.COMPLETED,
            result=StructuredOutput(
                data=result["data"],
                raw_text=result.get("raw_text"),
            ),
            processing_time_ms=processing_time,
        )

        # Store result for later retrieval
        await _storage.store_result(request_id, response.model_dump())

        return response

    except ValueError as e:
        return OCRResponse(
            request_id=request_id,
            status=JobStatus.FAILED,
            error=str(e),
        )
    except Exception as e:
        logger.exception(f"OCR extraction failed: {e}")
        return OCRResponse(
            request_id=request_id,
            status=JobStatus.FAILED,
            error=f"Extraction failed: {str(e)}",
        )


@router.post("/extract/async", response_model=dict)
async def extract_text_async(
    request: OCRRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Asynchronous OCR extraction endpoint.

    Returns immediately with a job ID. Poll /ocr/job/{job_id} for results.
    """
    request_id = str(uuid.uuid4())

    # Create job record
    job = BatchJob(
        job_id=request_id,
        status=JobStatus.PENDING,
        total_documents=1,
    )
    _jobs[request_id] = job

    # Queue background processing
    background_tasks.add_task(
        _process_ocr_job,
        request_id,
        request,
    )

    return {
        "job_id": request_id,
        "status": "pending",
        "poll_url": f"/ocr/job/{request_id}",
    }


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an async OCR job"""
    if job_id not in _jobs:
        # Try to retrieve from storage
        result = await _storage.get_result(job_id)
        if result:
            return result
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]

    if job.status == JobStatus.COMPLETED:
        result = await _storage.get_result(job_id)
        return result

    return {
        "job_id": job_id,
        "status": job.status,
        "processed": job.processed_documents,
        "total": job.total_documents,
    }


@router.post("/batch", response_model=dict)
async def submit_batch_job(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Submit a batch processing job.

    Processes all documents in the source bucket/prefix and stores
    results in the output location.
    """
    job_id = str(uuid.uuid4())

    # Create job record
    job = BatchJob(
        job_id=job_id,
        status=JobStatus.PENDING,
        total_documents=0,  # Will be updated when job starts
    )
    _jobs[job_id] = job

    # Queue batch processing
    background_tasks.add_task(
        _process_batch_job,
        job_id,
        request,
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "poll_url": f"/ocr/job/{job_id}",
    }


async def _process_ocr_job(job_id: str, request: OCRRequest):
    """Background task to process single OCR request"""
    job = _jobs[job_id]
    job.status = JobStatus.PROCESSING

    try:
        engine = get_engine()
        image = await engine.load_image(
            image_url=request.image_url,
            image_base64=request.image_base64,
        )

        result = engine.extract(
            image=image,
            output_schema=request.output_schema,
            prompt=request.prompt,
        )

        response = OCRResponse(
            request_id=job_id,
            status=JobStatus.COMPLETED,
            result=StructuredOutput(
                data=result["data"],
                raw_text=result.get("raw_text"),
            ),
        )

        await _storage.store_result(job_id, response.model_dump())
        job.status = JobStatus.COMPLETED
        job.processed_documents = 1

    except Exception as e:
        logger.exception(f"Async OCR job {job_id} failed: {e}")
        job.status = JobStatus.FAILED
        error_response = OCRResponse(
            request_id=job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )
        await _storage.store_result(job_id, error_response.model_dump())


async def _process_batch_job(job_id: str, request: BatchRequest):
    """Background task to process batch of documents from storage"""
    job = _jobs[job_id]
    job.status = JobStatus.PROCESSING

    try:
        # TODO: Implement batch processing
        # 1. List objects in source_bucket/source_prefix
        # 2. Process each document
        # 3. Store results in output_bucket/output_prefix
        # 4. Update job progress

        # Placeholder for batch implementation
        logger.info(f"Batch job {job_id} started for {request.source_bucket}/{request.source_prefix}")

        job.status = JobStatus.COMPLETED

    except Exception as e:
        logger.exception(f"Batch job {job_id} failed: {e}")
        job.status = JobStatus.FAILED
