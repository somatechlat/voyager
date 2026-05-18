"""Storage service for S3/MinIO object storage operations.

Handles file upload, download, deletion, and presigned URL generation
using boto3 with S3-compatible backends (AWS S3, MinIO, Ceph).
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported file type detection
# ---------------------------------------------------------------------------

SUPPORTED_TYPES: dict[str, list[str]] = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".tiff", ".psd", ".ai"],
    "video": [".mp4", ".mov", ".avi", ".webm", ".mkv"],
    "document": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv"],
    "font": [".ttf", ".otf", ".woff", ".woff2"],
    "archive": [".zip", ".rar", ".7z"],
    "audio": [".mp3", ".wav", ".ogg", ".flac"],
}

MAX_SIZES: dict[str, int] = {
    "image": 100 * 1024 * 1024,  # 100 MB
    "video": 2 * 1024 * 1024 * 1024,  # 2 GB
    "document": 50 * 1024 * 1024,  # 50 MB
    "font": 10 * 1024 * 1024,  # 10 MB
    "archive": 500 * 1024 * 1024,  # 500 MB
    "audio": 200 * 1024 * 1024,  # 200 MB
}


def _detect_file_type(filename: str) -> str:
    """Detect the broad file type category from extension.

    Args:
        filename: The file name including extension.

    Returns:
        One of the SUPPORTED_TYPES keys or 'unknown'.
    """
    ext = Path(filename).suffix.lower()
    for file_type, extensions in SUPPORTED_TYPES.items():
        if ext in extensions:
            return file_type
    return "unknown"


def _detect_mime_type(filename: str) -> str:
    """Guess the MIME type from the filename extension.

    Args:
        filename: The file name including extension.

    Returns:
        MIME type string or 'application/octet-stream'.
    """
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _get_s3_client() -> boto3.client:
    """Create and return an S3-compatible client.

    Reads endpoint, access key, and secret key from Django settings
    with sensible defaults for MinIO development environments.

    Returns:
        Configured boto3 S3 client.
    """
    endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000")
    access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "minioadmin")
    secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "minioadmin")
    region = getattr(settings, "AWS_S3_REGION_NAME", "us-east-1")
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _get_bucket_name() -> str:
    """Return the configured S3 bucket name.

    Defaults to 'voyager-assets' for development.
    """
    return getattr(settings, "AWS_STORAGE_BUCKET_NAME", "voyager-assets")


class StorageService:
    """Service for S3/MinIO storage operations.

    Provides upload, download, deletion, and presigned URL generation
    for digital assets stored in S3-compatible object storage.
    """

    @staticmethod
    def validate_file(filename: str, file_size: int) -> dict[str, Any]:
        """Validate a file before upload.

        Checks file type support and size limits.

        Args:
            filename: The original file name.
            file_size: File size in bytes.

        Returns:
            Dict with ``valid`` (bool), ``file_type``, ``mime_type``,
            ``max_size``, and optional ``error`` message.
        """
        file_type = _detect_file_type(filename)
        if file_type == "unknown":
            return {
                "valid": False,
                "file_type": "unknown",
                "mime_type": "",
                "error": f"Unsupported file extension for '{filename}'",
            }
        max_size = MAX_SIZES.get(file_type, 0)
        if file_size > max_size:
            return {
                "valid": False,
                "file_type": file_type,
                "mime_type": _detect_mime_type(filename),
                "max_size": max_size,
                "error": (
                    f"File size {file_size} exceeds " f"{max_size} byte limit for {file_type}"
                ),
            }
        return {
            "valid": True,
            "file_type": file_type,
            "mime_type": _detect_mime_type(filename),
            "max_size": max_size,
        }

    @staticmethod
    def generate_file_key(
        tenant_id: str,
        asset_id: str,
        filename: str,
        version: int | None = None,
    ) -> str:
        """Generate a deterministic S3 object key for an asset.

        Args:
            tenant_id: Tenant scope identifier.
            asset_id: UUID of the asset record.
            filename: Original file name.
            version: Optional version number for versioned keys.

        Returns:
            S3 object key string.
        """
        safe_name = Path(filename).name
        if version:
            return f"{tenant_id}/{asset_id}/v{version}/{safe_name}"
        return f"{tenant_id}/{asset_id}/{safe_name}"

    @staticmethod
    def generate_thumbnail_key(
        tenant_id: str,
        asset_id: str,
        size: int,
    ) -> str:
        """Generate an S3 object key for a thumbnail.

        Args:
            tenant_id: Tenant scope identifier.
            asset_id: UUID of the asset record.
            size: Thumbnail dimension in pixels.

        Returns:
            S3 object key string.
        """
        return f"{tenant_id}/{asset_id}/thumbs/{size}.jpg"

    @staticmethod
    def upload_file(
        file_data: bytes,
        file_key: str,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Upload file bytes to S3/MinIO.

        Args:
            file_data: Raw file bytes.
            file_key: Destination S3 object key.
            content_type: MIME type for the object.

        Returns:
            Dict with ``success`` (bool), ``file_key``, ``etag``,
            and optional ``error``.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        try:
            s3.put_object(
                Bucket=bucket,
                Key=file_key,
                Body=file_data,
                ContentType=content_type,
            )
            response = s3.head_object(Bucket=bucket, Key=file_key)
            etag = response.get("ETag", "").strip('"')
            return {"success": True, "file_key": file_key, "etag": etag}
        except ClientError as exc:
            logger.error("S3 upload failed for %s: %s", file_key, exc)
            return {"success": False, "file_key": file_key, "error": str(exc)}

    @staticmethod
    def delete_file(file_key: str) -> dict[str, Any]:
        """Delete an object from S3/MinIO.

        Args:
            file_key: S3 object key to delete.

        Returns:
            Dict with ``success`` (bool) and optional ``error``.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        try:
            s3.delete_object(Bucket=bucket, Key=file_key)
            return {"success": True, "file_key": file_key}
        except ClientError as exc:
            logger.error("S3 delete failed for %s: %s", file_key, exc)
            return {"success": False, "file_key": file_key, "error": str(exc)}

    @staticmethod
    def generate_presigned_url(
        file_key: str,
        operation: str = "get_object",
        expiration: int = 3600,
    ) -> str | None:
        """Generate a presigned URL for temporary access.

        Args:
            file_key: S3 object key.
            operation: S3 operation ('get_object' or 'put_object').
            expiration: URL lifetime in seconds (max 7 days).

        Returns:
            Presigned URL string or ``None`` on failure.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        try:
            url = s3.generate_presigned_url(
                ClientMethod=operation,
                Params={"Bucket": bucket, "Key": file_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as exc:
            logger.error("Failed to generate presigned URL for %s: %s", file_key, exc)
            return None

    @staticmethod
    def generate_presigned_post(
        file_key: str,
        content_type: str = "application/octet-stream",
        expiration: int = 3600,
        max_size: int | None = None,
    ) -> dict[str, Any] | None:
        """Generate a presigned POST policy for browser uploads.

        Args:
            file_key: S3 object key.
            content_type: Expected MIME type.
            expiration: Policy lifetime in seconds.
            max_size: Maximum file size in bytes.

        Returns:
            Dict with ``url`` and ``fields`` or ``None`` on failure.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        conditions: list[Any] = [["eq", "$Content-Type", content_type]]
        if max_size:
            conditions.append(["content-length-range", 1, max_size])
        try:
            post = s3.generate_presigned_post(
                Bucket=bucket,
                Key=file_key,
                Fields={"Content-Type": content_type},
                Conditions=conditions,
                ExpiresIn=expiration,
            )
            return post
        except ClientError as exc:
            logger.error("Failed to generate presigned POST for %s: %s", file_key, exc)
            return None

    @staticmethod
    def get_file_metadata(file_key: str) -> dict[str, Any]:
        """Retrieve S3 object metadata without downloading the body.

        Args:
            file_key: S3 object key.

        Returns:
            Dict with ``size``, ``content_type``, ``last_modified``,
            ``etag``, and ``exists`` flag.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        try:
            response = s3.head_object(Bucket=bucket, Key=file_key)
            return {
                "exists": True,
                "size": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", ""),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag", "").strip('"'),
            }
        except ClientError:
            return {"exists": False}

    @staticmethod
    def copy_file(source_key: str, dest_key: str) -> dict[str, Any]:
        """Copy an S3 object to a new key within the same bucket.

        Args:
            source_key: Source S3 object key.
            dest_key: Destination S3 object key.

        Returns:
            Dict with ``success`` (bool) and optional ``error``.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        copy_source = {"Bucket": bucket, "Key": source_key}
        try:
            s3.copy_object(
                CopySource=copy_source,
                Bucket=bucket,
                Key=dest_key,
            )
            return {"success": True, "source_key": source_key, "dest_key": dest_key}
        except ClientError as exc:
            logger.error("S3 copy failed %s -> %s: %s", source_key, dest_key, exc)
            return {"success": False, "error": str(exc)}

    @staticmethod
    def ensure_bucket() -> dict[str, Any]:
        """Ensure the configured S3 bucket exists, creating it if needed.

        Returns:
            Dict with ``success``, ``bucket``, and ``created`` flag.
        """
        s3 = _get_s3_client()
        bucket = _get_bucket_name()
        try:
            s3.head_bucket(Bucket=bucket)
            return {"success": True, "bucket": bucket, "created": False}
        except ClientError:
            try:
                s3.create_bucket(Bucket=bucket)
                return {"success": True, "bucket": bucket, "created": True}
            except ClientError as exc:
                logger.error("Failed to create bucket %s: %s", bucket, exc)
                return {"success": False, "bucket": bucket, "error": str(exc)}
