"""Artifact storage abstraction layer.

Supports:
- Cloudflare R2 (S3-compatible)
- Supabase Storage (legacy)
- Local disk (development)
"""

import os
from typing import Protocol, runtime_checkable
import boto3
from botocore.config import Config


@runtime_checkable
class StorageClient(Protocol):
    """Storage client interface."""

    async def upload_file(self, key: str, content: bytes, content_type: str) -> str:
        """Upload file and return storage key.

        Args:
            key: Object key (path) for the file
            content: File content as bytes
            content_type: MIME type (e.g., 'application/pdf')

        Returns:
            Storage key for later retrieval
        """
        ...

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Get presigned URL for download.

        Args:
            key: Object key
            expires_in: URL expiration in seconds (default 1 hour)

        Returns:
            Presigned download URL
        """
        ...

    async def delete_file(self, key: str) -> None:
        """Delete file from storage.

        Args:
            key: Object key
        """
        ...


class CloudflareR2Client:
    """Cloudflare R2 storage client (S3-compatible).

    R2 is Cloudflare's object storage offering that's fully compatible
    with the S3 API. It offers 10GB free storage with no egress fees.

    Usage:
        client = CloudflareR2Client(
            account_id="abc123",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name="my-bucket"
        )

        # Upload
        key = await client.upload_file(
            "reports/2024-11-21.pdf",
            pdf_bytes,
            "application/pdf"
        )

        # Get download URL
        url = await client.get_presigned_url(key, expires_in=3600)
    """

    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
    ):
        """Initialize R2 client.

        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
        """
        self.bucket_name = bucket_name

        # R2 endpoint format
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        # Create S3 client (R2 is S3-compatible)
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    async def upload_file(self, key: str, content: bytes, content_type: str) -> str:
        """Upload file to R2.

        Args:
            key: Object key (path)
            content: File content
            content_type: MIME type

        Returns:
            Object key (use get_presigned_url for download URL)
        """
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        # Return key (use presigned URL for downloads)
        return key

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned download URL.

        Args:
            key: Object key
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL valid for `expires_in` seconds
        """
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete_file(self, key: str) -> None:
        """Delete file from R2.

        Args:
            key: Object key to delete
        """
        self.s3.delete_object(Bucket=self.bucket_name, Key=key)


def get_storage_client() -> StorageClient:
    """Get storage client based on environment configuration.

    Reads ARTIFACT_STORAGE_TYPE from environment:
    - 'r2': Cloudflare R2 (default, recommended)
    - 'supabase': Supabase Storage (legacy)
    - 'disk': Local filesystem (development only)

    Returns:
        StorageClient instance configured for current environment

    Raises:
        ValueError: If storage type is unsupported or credentials missing
    """
    storage_type = os.getenv("ARTIFACT_STORAGE_TYPE", "r2")

    if storage_type == "r2":
        # Cloudflare R2
        account_id = os.getenv("R2_ACCOUNT_ID")
        access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        bucket_name = os.getenv("R2_BUCKET_NAME", "chad-core-artifacts")

        if not all([account_id, access_key_id, secret_access_key]):
            raise ValueError(
                "R2 storage requires: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY environment variables"
            )

        return CloudflareR2Client(
            account_id=account_id,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            bucket_name=bucket_name,
        )

    elif storage_type == "supabase":
        # TODO: Implement SupabaseStorageClient
        raise NotImplementedError("Supabase storage not yet implemented")

    elif storage_type == "disk":
        # TODO: Implement LocalDiskStorageClient
        raise NotImplementedError("Local disk storage not yet implemented")

    else:
        raise ValueError(
            f"Unsupported storage type: {storage_type}. "
            f"Valid options: r2, supabase, disk"
        )


__all__ = [
    "StorageClient",
    "CloudflareR2Client",
    "get_storage_client",
]
