from __future__ import annotations

import logging
from typing import Any

import boto3
from config import get_settings

logger = logging.getLogger(__name__)


class S3ResultStore:
    """Uploads large tool results to S3 and generates pre-signed download URLs."""

    def __init__(self) -> None:
        settings = get_settings()
        kwargs: dict[str, Any] = {"region_name": settings.aws_region}
        self._client = boto3.client("s3", **kwargs)
        self._bucket = settings.s3_results_bucket

    @staticmethod
    def make_key(session_id: str, result_id: str) -> str:
        return f"results/{session_id}/{result_id}.txt"

    @staticmethod
    def make_summary_key(session_id: str) -> str:
        return f"summaries/{session_id}/latest.txt"

    @staticmethod
    def make_user_facts_key(user_id: str) -> str:
        return f"users/{user_id}/facts.json"

    def upload_result(self, key: str, content: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        logger.info("Uploaded tool result to s3://%s/%s", self._bucket, key)

    def download_result(self, key: str) -> str:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        content: str = resp["Body"].read().decode("utf-8")
        logger.info("Downloaded tool result from s3://%s/%s", self._bucket, key)
        return content

    def generate_presigned_url(self, key: str, expiry: int | None = None) -> str:
        if expiry is None:
            expiry = get_settings().s3_presigned_url_expiry
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry,
        )
        return url
