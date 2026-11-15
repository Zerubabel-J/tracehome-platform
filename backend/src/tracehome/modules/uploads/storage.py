"""Presigned uploads. The browser uploads straight to the private incoming bucket, so the API
never handles the file itself (decision 51).

We use a presigned POST, not a PUT: a POST policy lets S3 itself refuse files that are too big
or of the wrong type. A presigned PUT can't limit the size.
"""

import boto3
from botocore.config import Config

from tracehome.config import get_settings


def _signing_client():
    settings = get_settings()
    if settings.s3_public_endpoint_url:
        # Local only: sign for the address the browser can reach (LocalStack on localhost).
        return boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.s3_public_endpoint_url,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    return boto3.client(
        "s3", region_name=settings.aws_region, config=Config(signature_version="s3v4")
    )


def presign_photo_upload(object_key: str, content_type: str) -> dict:
    settings = get_settings()
    # Signing happens on this machine; no network call. On ECS the signature uses the task
    # role's temporary credentials, so the link also dies when those credentials expire.
    return _signing_client().generate_presigned_post(
        Bucket=settings.incoming_bucket,
        Key=object_key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, settings.max_photo_bytes],
        ],
        ExpiresIn=settings.upload_url_ttl_seconds,
    )


def held_key(object_key: str) -> str:
    """Where the upload checks park a flagged photo: uploads/<listing>/<file> -> held/... (decision 75)."""
    return "held/" + object_key.removeprefix("uploads/")


def presign_held_photo_view(object_key: str) -> str:
    """A 5-minute link so a moderator's browser can show one flagged photo. The bucket stays
    private; the API checks the moderator's permission before signing (ARCHITECTURE.md)."""
    settings = get_settings()
    return _signing_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.incoming_bucket, "Key": held_key(object_key)},
        ExpiresIn=300,
    )


def publish_held_photo(object_key: str, public_key: str) -> None:
    """A moderator approved a flagged photo: copy it from held/ to the public photos bucket.
    Copying the same file twice gives the same result, so a retry is safe."""
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.copy_object(
        Bucket=settings.photos_bucket,
        Key=public_key,
        CopySource={"Bucket": settings.incoming_bucket, "Key": held_key(object_key)},
    )
