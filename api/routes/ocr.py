import time
import uuid
import json
import logging
from io import BytesIO
from datetime import datetime
from typing import Optional

import boto3
from PIL import Image
from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Depends

from api.models import (
    OCRRequest,
    OCRResponse,
    JobStatus,
    StructuredOutput,
    BatchJob,
)
from api.models.schemas import BatchRequest
from api.services.ocr_engine import get_engine
from api.services.storage import LocalStorage, S3Storage, GCSStorage
from api.services.job_tracker import get_job_tracker
from api.services.webhooks import notify_job_complete, notify_batch_progress
from api.services.rate_limiter import get_rate_limiter
from api.routes.schemas import get_schema_by_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["ocr"])

# Default storage (configure via environment)
_storage = LocalStorage()


async def check_rate_limit(x_api_key: str = Header(default="default-tenant:key")):
    """Dependency to check rate limits"""
    tenant_id = x_api_key.split(":")[0] if ":" in x_api_key else "default-tenant"
    limiter = get_rate_limiter()
    allowed, info = await limiter.check_rate_limit(tenant_id)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=info.get("error", "Rate limit exceeded"),
            headers={
                "X-RateLimit-Remaining": str(info.get("requests_remaining_minute", 0)),
                "Retry-After": "60",
            },
        )
    return tenant_id


@router.post("/extract", response_model=OCRResponse)
async def extract_text(
    request: OCRRequest,
    tenant_id: str = Depends(check_rate_limit),
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
    webhook_url: Optional[str] = None,
    tenant_id: str = Depends(check_rate_limit),
) -> dict:
    """
    Asynchronous OCR extraction endpoint.

    Returns immediately with a job ID. Poll /ocr/job/{job_id} for results.
    Optionally provide webhook_url to receive completion notification.
    """
    request_id = str(uuid.uuid4())
    tracker = get_job_tracker()

    # Create job record
    job = BatchJob(
        job_id=request_id,
        status=JobStatus.PENDING,
        total_documents=1,
    )
    await tracker.create_job(job)

    # Queue background processing
    background_tasks.add_task(
        _process_ocr_job,
        request_id,
        request,
        webhook_url,
    )

    return {
        "job_id": request_id,
        "status": "pending",
        "poll_url": f"/ocr/job/{request_id}",
    }


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an async OCR job"""
    tracker = get_job_tracker()
    job = await tracker.get_job(job_id)

    if not job:
        # Try to retrieve from storage
        result = await _storage.get_result(job_id)
        if result:
            return result
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.COMPLETED:
        result = await _storage.get_result(job_id)
        if result:
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
    webhook_url: Optional[str] = None,
    tenant_id: str = Depends(check_rate_limit),
) -> dict:
    """
    Submit a batch processing job.

    Processes all documents in the source bucket/prefix and stores
    results in the output location.
    """
    job_id = str(uuid.uuid4())
    tracker = get_job_tracker()

    # Create job record
    job = BatchJob(
        job_id=job_id,
        status=JobStatus.PENDING,
        total_documents=0,  # Will be updated when job starts
    )
    await tracker.create_job(job)

    # Queue batch processing
    background_tasks.add_task(
        _process_batch_job,
        job_id,
        request,
        webhook_url,
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "poll_url": f"/ocr/job/{job_id}",
    }


async def _process_ocr_job(
    job_id: str,
    request: OCRRequest,
    webhook_url: Optional[str] = None,
):
    """Background task to process single OCR request"""
    tracker = get_job_tracker()
    job = await tracker.get_job(job_id)
    job.status = JobStatus.PROCESSING
    await tracker.update_job(job)

    result_url = None

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

        result_url = await _storage.store_result(job_id, response.model_dump())
        job.status = JobStatus.COMPLETED
        job.processed_documents = 1
        job.results_url = result_url
        await tracker.update_job(job)

        # Send webhook notification
        if webhook_url:
            await notify_job_complete(
                webhook_url, job_id, "completed", result_url
            )

    except Exception as e:
        logger.exception(f"Async OCR job {job_id} failed: {e}")
        job.status = JobStatus.FAILED
        await tracker.update_job(job)

        error_response = OCRResponse(
            request_id=job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )
        await _storage.store_result(job_id, error_response.model_dump())

        if webhook_url:
            await notify_job_complete(
                webhook_url, job_id, "failed", error=str(e)
            )


async def _process_batch_job(
    job_id: str,
    request: BatchRequest,
    webhook_url: Optional[str] = None,
):
    """Background task to process batch of documents from storage"""
    tracker = get_job_tracker()
    job = await tracker.get_job(job_id)
    job.status = JobStatus.PROCESSING
    await tracker.update_job(job)

    try:
        engine = get_engine()
        if not engine.is_loaded:
            raise RuntimeError("Model not loaded")

        # List objects from source bucket
        s3 = boto3.client("s3")
        response = s3.list_objects_v2(
            Bucket=request.source_bucket,
            Prefix=request.source_prefix,
        )

        if "Contents" not in response:
            logger.warning(f"No objects found in {request.source_bucket}/{request.source_prefix}")
            job.status = JobStatus.COMPLETED
            job.total_documents = 0
            await tracker.update_job(job)
            return

        # Filter for image files
        image_keys = [
            obj["Key"] for obj in response["Contents"]
            if any(obj["Key"].lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"])
        ]

        job.total_documents = len(image_keys)
        await tracker.update_job(job)

        logger.info(f"Batch job {job_id}: Processing {len(image_keys)} images")

        results = []

        for i, key in enumerate(image_keys):
            try:
                # Load image from S3
                obj = s3.get_object(Bucket=request.source_bucket, Key=key)
                image_data = obj["Body"].read()
                image = Image.open(BytesIO(image_data))

                # Extract data
                result = engine.extract(
                    image=image,
                    output_schema=request.output_schema,
                )

                results.append({
                    "source_key": key,
                    "status": "success",
                    "data": result["data"],
                })

            except Exception as e:
                logger.error(f"Failed to process {key}: {e}")
                results.append({
                    "source_key": key,
                    "status": "failed",
                    "error": str(e),
                })

            # Update progress
            job.processed_documents = i + 1
            await tracker.update_job(job)

            # Send progress webhook every 10 documents
            if webhook_url and (i + 1) % 10 == 0:
                await notify_batch_progress(
                    webhook_url, job_id, i + 1, len(image_keys)
                )

        # Store results
        output_key = f"{request.output_prefix}/{job_id}.json"
        s3.put_object(
            Bucket=request.output_bucket,
            Key=output_key,
            Body=json.dumps(results, default=str),
            ContentType="application/json",
        )

        result_url = f"s3://{request.output_bucket}/{output_key}"
        job.status = JobStatus.COMPLETED
        job.results_url = result_url
        job.completed_at = datetime.utcnow()
        await tracker.update_job(job)

        logger.info(f"Batch job {job_id} completed: {len(results)} results")

        if webhook_url:
            await notify_job_complete(
                webhook_url, job_id, "completed", result_url
            )

    except Exception as e:
        logger.exception(f"Batch job {job_id} failed: {e}")
        job.status = JobStatus.FAILED
        await tracker.update_job(job)

        if webhook_url:
            await notify_job_complete(
                webhook_url, job_id, "failed", error=str(e)
            )
