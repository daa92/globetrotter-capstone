"""
app/media.py

Uploads user-submitted place photos/videos to Cloudinary (free tier:
25GB storage, 25GB bandwidth/month — comfortably covers a capstone-scale
app). Uses Cloudinary's raw signed-upload REST API directly over httpx
rather than their Python SDK, to avoid adding a whole extra dependency
for what's a handful of HTTP calls.

Why not store files in TiDB directly? A single approved place could
have several images plus a video, each up to the combined 10MB cap —
storing that as base64 in JSON rows would bloat every read of the
`store` table's places/destinations collections (even queries that don't
care about media), and TiDB Serverless free tier has a storage cap that
10MB-per-place blobs would burn through fast. A dedicated media host is
the right tool here, same reasoning as using Brevo for email instead of
hand-rolling SMTP.
"""
import hashlib
import logging
import time
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("gt.media")


class MediaUploadError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET)


def _signature(params: dict[str, str]) -> str:
    """Cloudinary's signed-upload scheme: sort params, join as
    key=value pairs, append the API secret, SHA-1 the result. Documented
    at cloudinary.com/documentation/authentication_signatures."""
    to_sign = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + settings.CLOUDINARY_API_SECRET
    return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()


def upload_file(content: bytes, filename: str, content_type: str, folder: str = "gt-places") -> dict:
    """Returns {"url": ..., "resource_type": "image"|"video", "bytes": int}. Raises MediaUploadError on failure."""
    if not is_configured():
        raise MediaUploadError("Media uploads aren't configured on this server yet")

    resource_type = "video" if content_type.startswith("video/") else "image"
    timestamp = str(int(time.time()))
    params_to_sign = {"timestamp": timestamp, "folder": folder}
    signature = _signature(params_to_sign)

    url = f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/{resource_type}/upload"
    try:
        response = httpx.post(
            url,
            data={
                "timestamp": timestamp,
                "folder": folder,
                "api_key": settings.CLOUDINARY_API_KEY,
                "signature": signature,
            },
            files={"file": (filename, content, content_type)},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Cloudinary upload failed for %s: %s", filename, exc)
        raise MediaUploadError("Upload to media host failed") from exc

    data = response.json()
    return {"url": data["secure_url"], "resource_type": resource_type, "bytes": data.get("bytes", len(content))}


def delete_file(public_id: str, resource_type: str = "image") -> None:
    """Best-effort cleanup when a place is deleted/edited — a failure
    here shouldn't block the place deletion itself, just leaves an
    orphaned file in Cloudinary (harmless, well within free-tier quota
    for a capstone's traffic)."""
    if not is_configured():
        return
    timestamp = str(int(time.time()))
    params_to_sign = {"timestamp": timestamp, "public_id": public_id}
    signature = _signature(params_to_sign)
    url = f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/{resource_type}/destroy"
    try:
        httpx.post(
            url,
            data={
                "timestamp": timestamp,
                "public_id": public_id,
                "api_key": settings.CLOUDINARY_API_KEY,
                "signature": signature,
            },
            timeout=15.0,
        )
    except httpx.HTTPError:
        logger.warning("Cloudinary delete failed for %s (non-fatal)", public_id)
