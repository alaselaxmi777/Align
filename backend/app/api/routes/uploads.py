import os
import uuid
import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User, Profile
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = UPLOAD_DIR / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB

def validate_magic_bytes(header: bytes, content_type: str) -> bool:
    if len(header) < 4:
        return False
    if content_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    elif content_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    elif content_type == "image/gif":
        return header.startswith(b"GIF87a") or header.startswith(b"GIF89a")
    elif content_type == "image/webp":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    elif content_type in ("video/mp4", "video/quicktime"):
        return len(header) >= 12 and (b"ftyp" in header[:16] or b"moov" in header[:16])
    elif content_type == "video/webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    return False

def strip_image_exif(file_path: Path):
    """Sanitizes image by stripping all EXIF/GPS geolocation metadata."""
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            format_name = img.format or "JPEG"
            if format_name.upper() == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            data = list(img.getdata())
            clean = Image.new(img.mode, img.size)
            clean.putdata(data)
            clean.save(file_path, format=format_name)
    except Exception as exc:
        logger.warning(f"Could not strip EXIF metadata from {file_path.name}: {exc}")

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower().strip()

    is_image = content_type in ALLOWED_IMAGE_TYPES
    is_video = content_type in ALLOWED_VIDEO_TYPES

    if not (is_image or is_video):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media format '{content_type}'. Allowed: JPEG, PNG, WebP, GIF, MP4, WebM, QuickTime.",
        )

    # Determine extension
    if is_image:
        ext = ALLOWED_IMAGE_TYPES[content_type]
        media_kind = "image"
        subfolder = "posts"
        max_size = MAX_IMAGE_SIZE_BYTES
    else:
        ext = ALLOWED_VIDEO_TYPES[content_type]
        media_kind = "video"
        subfolder = "videos"
        max_size = MAX_VIDEO_SIZE_BYTES

    # Secure unique non-guessable filename with user ID
    unique_name = f"{user.id}_{uuid.uuid4().hex[:12]}{ext}"
    tmp_path = TMP_DIR / f"upload_raw_{unique_name}"

    # Stream read and enforce magic bytes + size limit
    size_read = 0
    first_chunk = True
    try:
        with open(tmp_path, "wb") as buffer:
            while chunk := await file.read(1024 * 64):  # 64 KB chunks
                if first_chunk:
                    if not validate_magic_bytes(chunk, content_type):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Uploaded file signature does not match declared MIME type (file spoofing detected).",
                        )
                    first_chunk = False
                size_read += len(chunk)
                if size_read > max_size:
                    buffer.close()
                    tmp_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {max_size // (1024 * 1024)}MB for {media_kind}s.",
                    )
                buffer.write(chunk)

        if is_image:
            strip_image_exif(tmp_path)

        with open(tmp_path, "rb") as f:
            clean_bytes = f.read()

        public_url, _ = storage_service.save_file(clean_bytes, unique_name, subfolder=subfolder)

        return {
            "status": "success",
            "url": public_url,
            "filename": unique_name,
            "media_type": media_kind,
            "size_bytes": size_read,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to save upload to storage: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file to storage: {str(exc)}",
        )
    finally:
        tmp_path.unlink(missing_ok=True)

@router.post("/image", status_code=status.HTTP_201_CREATED)
async def upload_image_variants(
    file: UploadFile = File(...),
    subfolder: str = Form("posts"),
    alt_text: str | None = Form(None),
    user: User = Depends(get_current_user),
):
    """
    Uploads an image, validates real content, enforces 10MB limit and allowed formats,
    strips EXIF/GPS, resizes variants (posts: max 1080px wide; avatars: 512px), and saves
    to the Supabase Storage 'align-media' bucket.
    """
    content_type = (file.content_type or "").lower().strip()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{content_type}'. Allowed formats: JPEG (.jpg, .jpeg), PNG (.png), and WebP (.webp).",
        )

    # Stream read with 10MB size enforcement
    chunks = []
    total_size = 0
    while chunk := await file.read(1024 * 64):
        total_size += len(chunk)
        if total_size > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Image exceeds maximum allowed size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB.",
            )
        chunks.append(chunk)

    data = b"".join(chunks)

    # Auto-route avatars if declared
    target_subfolder = "avatars" if (subfolder == "avatars" or alt_text == "User avatar") else "posts"

    try:
        from app.services.media_processor import process_image_upload
        result = process_image_upload(data, user_id=user.id, subfolder=target_subfolder, alt_text=alt_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Image variant generation failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process image variants.")

    return {
        "status": "success",
        **result
    }

@router.post("/avatar", status_code=status.HTTP_201_CREATED)
async def upload_user_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dedicated avatar upload endpoint:
    - Validates image and strips EXIF/GPS
    - Resizes to max 512x512 WebP (to conserve Supabase free tier storage)
    - Saves directly to 'align-media/avatars/{user_id}_{uuid}_avatar.webp'
    - Updates user profile in Neon PostgreSQL with the public URL
    """
    content_type = (file.content_type or "").lower().strip()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{content_type}'. Allowed formats: JPEG (.jpg, .jpeg), PNG (.png), and WebP (.webp).",
        )

    chunks = []
    total_size = 0
    while chunk := await file.read(1024 * 64):
        total_size += len(chunk)
        if total_size > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Avatar image exceeds maximum allowed size of 10MB.",
            )
        chunks.append(chunk)

    data = b"".join(chunks)
    try:
        from app.services.media_processor import process_image_upload
        result = process_image_upload(data, user_id=user.id, subfolder="avatars", alt_text=f"Avatar of {user.name}")
        public_avatar_url = result["avatar_url"]

        # Persist public URL directly in Neon PostgreSQL and delete old avatar
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if profile:
            old_avatar = profile.avatar_url
            if old_avatar and ("align-media" in old_avatar or "/uploads/" in old_avatar):
                storage_service.delete_file(old_avatar)
            profile.avatar_url = public_avatar_url
            db.commit()
            db.refresh(profile)

        return {
            "status": "success",
            "avatar_url": public_avatar_url,
            **result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error(f"Avatar upload failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload avatar.")

@router.post("/video", status_code=status.HTTP_201_CREATED)
async def upload_video_transcode(
    file: UploadFile = File(...),
    is_reel: bool = Form(False),
    user: User = Depends(get_current_user),
):
    """
    Uploads a video, enforces 50MB limit via chunked stream, validates magic bytes,
    checks duration (<=90s for reels, <=300s for feed), transcodes to 720p H.264/AAC MP4 with +faststart,
    extracts WebP poster frame, and saves to Supabase Storage 'align-media' bucket.
    """
    from app.services.video_processor import (
        process_video_upload,
        FFmpegNotFoundError,
        InvalidVideoFormatError,
        VideoDurationExceededError,
        VideoSizeExceededError,
        VideoProcessingError,
        MAX_VIDEO_SIZE_BYTES,
        TMP_DIR,
    )

    uid = uuid.uuid4().hex[:12]
    tmp_upload_path = TMP_DIR / f"upload_chunk_{user.id}_{uid}.tmp"
    total_bytes = 0
    chunk_size = 64 * 1024  # 64 KB

    try:
        with open(tmp_upload_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_VIDEO_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Video file exceeds maximum allowed size of {MAX_VIDEO_SIZE_BYTES // (1024 * 1024)} MB.",
                    )
                f.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded video file is empty.",
            )

        result = await process_video_upload(tmp_upload_path, user_id=user.id, is_reel=is_reel)
        return {
            "status": "success",
            **result,
        }
    except HTTPException:
        raise
    except FFmpegNotFoundError as exc:
        logger.error(f"FFmpeg not installed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video transcoding service is currently unavailable (FFmpeg is missing). Please contact support.",
        )
    except (InvalidVideoFormatError, VideoDurationExceededError) as exc:
        logger.warning(f"Video validation failed: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except VideoSizeExceededError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))
    except VideoProcessingError as exc:
        logger.error(f"Video processing failed: {exc}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected video upload error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcode and process video: {str(exc)}",
        )
    finally:
        tmp_upload_path.unlink(missing_ok=True)
