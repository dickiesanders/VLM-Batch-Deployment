import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class StorageBackend:
    """Abstract storage backend for results"""

    async def store_result(
        self,
        job_id: str,
        result: dict[str, Any],
    ) -> str:
        """Store result and return URL/path"""
        raise NotImplementedError

    async def get_result(self, job_id: str) -> Optional[dict[str, Any]]:
        """Retrieve stored result"""
        raise NotImplementedError


class S3Storage(StorageBackend):
    """S3-based storage backend"""

    def __init__(
        self,
        bucket: str,
        prefix: str = "ocr-results",
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self._client = boto3.client("s3", region_name=region)

    async def store_result(
        self,
        job_id: str,
        result: dict[str, Any],
    ) -> str:
        """Store result in S3 and return S3 URI"""
        key = f"{self.prefix}/{job_id}.json"

        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(result, default=str),
                ContentType="application/json",
            )
            return f"s3://{self.bucket}/{key}"
        except ClientError as e:
            logger.error(f"Failed to store result in S3: {e}")
            raise

    async def get_result(self, job_id: str) -> Optional[dict[str, Any]]:
        """Retrieve result from S3"""
        key = f"{self.prefix}/{job_id}.json"

        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise


class GCSStorage(StorageBackend):
    """Google Cloud Storage backend"""

    def __init__(
        self,
        bucket: str,
        prefix: str = "ocr-results",
    ):
        from google.cloud import storage
        self.bucket_name = bucket
        self.prefix = prefix
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket)

    async def store_result(
        self,
        job_id: str,
        result: dict[str, Any],
    ) -> str:
        """Store result in GCS and return gs:// URI"""
        blob_name = f"{self.prefix}/{job_id}.json"
        blob = self._bucket.blob(blob_name)

        blob.upload_from_string(
            json.dumps(result, default=str),
            content_type="application/json",
        )
        return f"gs://{self.bucket_name}/{blob_name}"

    async def get_result(self, job_id: str) -> Optional[dict[str, Any]]:
        """Retrieve result from GCS"""
        blob_name = f"{self.prefix}/{job_id}.json"
        blob = self._bucket.blob(blob_name)

        if not blob.exists():
            return None

        return json.loads(blob.download_as_string().decode("utf-8"))


class LocalStorage(StorageBackend):
    """Local filesystem storage (for development)"""

    def __init__(self, base_path: str = "/tmp/ocr-results"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def store_result(
        self,
        job_id: str,
        result: dict[str, Any],
    ) -> str:
        """Store result locally and return file path"""
        file_path = self.base_path / f"{job_id}.json"

        with open(file_path, "w") as f:
            json.dump(result, f, default=str)

        return str(file_path)

    async def get_result(self, job_id: str) -> Optional[dict[str, Any]]:
        """Retrieve result from local storage"""
        file_path = self.base_path / f"{job_id}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            return json.load(f)
