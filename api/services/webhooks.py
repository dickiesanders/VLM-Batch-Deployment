"""Webhook callbacks for async job notifications"""
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


async def send_webhook(
    url: str,
    payload: dict[str, Any],
    headers: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
    retries: int = 3,
) -> bool:
    """
    Send webhook notification with retry logic.

    Returns True if successful, False otherwise.
    """
    default_headers = {
        "Content-Type": "application/json",
        "User-Agent": "DeepSeek-OCR-API/1.0",
    }
    if headers:
        default_headers.update(headers)

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=default_headers,
                    timeout=timeout,
                )
                response.raise_for_status()
                logger.info(f"Webhook sent successfully to {url}")
                return True

        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Webhook failed (attempt {attempt + 1}/{retries}): "
                f"{e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.warning(
                f"Webhook request failed (attempt {attempt + 1}/{retries}): {e}"
            )

        # Exponential backoff
        if attempt < retries - 1:
            import asyncio
            await asyncio.sleep(2 ** attempt)

    logger.error(f"Webhook failed after {retries} attempts: {url}")
    return False


async def notify_job_complete(
    webhook_url: str,
    job_id: str,
    status: str,
    result_url: Optional[str] = None,
    error: Optional[str] = None,
) -> bool:
    """Send job completion notification"""
    payload = {
        "event": "job.completed",
        "job_id": job_id,
        "status": status,
        "result_url": result_url,
        "error": error,
    }
    return await send_webhook(webhook_url, payload)


async def notify_batch_progress(
    webhook_url: str,
    job_id: str,
    processed: int,
    total: int,
) -> bool:
    """Send batch progress notification"""
    payload = {
        "event": "batch.progress",
        "job_id": job_id,
        "processed": processed,
        "total": total,
        "percent": round(processed / total * 100, 1) if total > 0 else 0,
    }
    return await send_webhook(webhook_url, payload)
