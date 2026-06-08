"""
MinIO async client helpers for AURA services.

Wraps ``miniopy-async`` to provide initialisation, bucket bootstrapping,
binary upload and presigned URL generation as simple module-level calls
shared across all services.
"""
import hashlib
import io
from datetime import timedelta

import miniopy_async as minio_lib

_client = None
_bucket_map: dict[str, str] = {}
_access_key = None
_secret_key = None


def init_minio(
    endpoint: str,
    access_key: str,
    secret_key: str,
    secure: bool,
    buckets: dict[str, str],
) -> None:
    """Initialise the global MinIO client and register logical bucket names.

    Must be called once during application startup before any other
    function in this module is used.

    Args:
        endpoint:   MinIO host and port, e.g. ``"minio:9000"``.
        access_key: MinIO root / access key.
        secret_key: MinIO root / secret key.
        secure:     Whether to use TLS (``False`` for local development).
        buckets:    Mapping from logical bucket key (used in code) to the
                    actual bucket name, e.g.
                    ``{"models": "models", "compiled": "compiled"}``.
    """
    global _client, _bucket_map, _access_key, _secret_key
    _access_key = access_key
    _secret_key = secret_key
    _client = minio_lib.Minio(
        endpoint, access_key=access_key, secret_key=secret_key, secure=secure
    )
    _bucket_map = buckets


def get_minio():
    """Return the initialised MinIO client.

    Raises:
        RuntimeError: If :func:`init_minio` has not been called yet.
    """
    if _client is None:
        raise RuntimeError("MinIO not initialized. Call init_minio() first.")
    return _client


async def ensure_buckets() -> None:
    """Create all registered buckets if they do not already exist.

    Should be called once during application startup after
    :func:`init_minio`.
    """
    for bucket in _bucket_map.values():
        if not await _client.bucket_exists(bucket):
            await _client.make_bucket(bucket)


async def upload_bytes(bucket_key: str, object_key: str, data: bytes) -> str:
    """Upload raw bytes to MinIO and return the SHA-256 hex digest.

    Args:
        bucket_key: Logical bucket key as registered in :func:`init_minio`.
        object_key: Object path inside the bucket, e.g.
                    ``"{model_id}/source.pt"``.
        data:       Raw bytes to upload.

    Returns:
        Hex-encoded SHA-256 digest of ``data``.
    """
    bucket = _bucket_map[bucket_key]
    sha = hashlib.sha256(data).hexdigest()
    await _client.put_object(bucket, object_key, io.BytesIO(data), len(data))
    return sha


async def presigned_url(
    bucket_key: str,
    object_key: str,
    expiry_seconds: int = 3600,
) -> str:
    """Generate a presigned GET URL for a MinIO object.

    Args:
        bucket_key:     Logical bucket key.
        object_key:     Object path inside the bucket.
        expiry_seconds: URL validity in seconds. Defaults to 3600 (1 hour).

    Returns:
        A presigned HTTPS/HTTP URL string valid for ``expiry_seconds``.
    """
    import os
    from urllib.parse import urlparse, urlunparse
    bucket = _bucket_map[bucket_key]
    public_url = os.getenv("MINIO_PUBLIC_URL")
    if public_url:
        parsed_public = urlparse(public_url)
        host = parsed_public.netloc
        scheme = parsed_public.scheme
        
        tmp_client = minio_lib.Minio(
            host, 
            access_key=_access_key, 
            secret_key=_secret_key, 
            secure=(scheme == "https"),
            region="us-east-1"
        )
        url = await tmp_client.presigned_get_object(
            bucket, object_key, expires=timedelta(seconds=expiry_seconds)
        )
    else:
        url = await _client.presigned_get_object(
            bucket, object_key, expires=timedelta(seconds=expiry_seconds)
        )
        
    return url
