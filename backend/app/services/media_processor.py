import io
import uuid
import logging
from pathlib import Path
from PIL import Image, ImageOps
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_MIMES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

def validate_image_bytes(data: bytes, declared_mime: str | None = None) -> str:
    """
    Validates magic bytes and real file content.
    Returns canonical mime type or raises ValueError.
    """
    if len(data) < 12:
        raise ValueError("File is too small to be a valid image.")
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image exceeds maximum allowed size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB.")

    # 1. Magic byte checks
    detected_mime = None
    if data.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        detected_mime = "image/webp"

    if not detected_mime:
        raise ValueError("File content does not match allowed image formats (JPEG, PNG, WebP).")

    if declared_mime and declared_mime.lower().strip() != detected_mime:
        logger.warning(f"Declared MIME '{declared_mime}' differs from detected '{detected_mime}'. Using detected.")

    # 2. Structural Pillow verification
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except Exception as e:
        raise ValueError(f"Corrupted or invalid image payload: {e}")

    return detected_mime

def strip_and_normalize_image(data: bytes) -> Image.Image:
    """
    Opens image, converts RGBA/P to RGB (or keeps RGBA if transparent),
    strips all EXIF, GPS, and device metadata.
    """
    with Image.open(io.BytesIO(data)) as raw_img:
        # Handle EXIF orientation before stripping
        try:
            transposed = ImageOps.exif_transpose(raw_img)
            if transposed is not None:
                raw_img = transposed
        except Exception:
            pass

        # Convert palette images to RGBA or RGB
        if raw_img.mode in ("P", "1"):
            raw_img = raw_img.convert("RGBA" if "transparency" in raw_img.info else "RGB")
        elif raw_img.mode not in ("RGB", "RGBA"):
            raw_img = raw_img.convert("RGB")

        # Deep copy data bytes without any EXIF/metadata dictionaries
        clean = Image.frombytes(raw_img.mode, raw_img.size, raw_img.tobytes())
        clean.info = {}
        return clean

def process_image_upload(
    data: bytes,
    user_id: int | str = 0,
    subfolder: str = "posts",
    alt_text: str | None = None,
) -> dict:
    """
    Processes an uploaded image into WebP variants:
    - If subfolder == 'avatars': 512x512 square WebP (quality 85) saved to 'avatars/'.
    - If subfolder == 'posts':
        1. full: resized to max 1080px wide (preserving aspect ratio, quality 85)
        2. feed: 1080x1080 fit crop (quality 85)
        3. thumb: 300x300 fit crop (quality 80)
      saved to 'posts/'.
    Unique, non-guessable naming: {user_id}_{uid}_*.webp.
    All EXIF/GPS metadata is stripped.
    """
    validate_image_bytes(data)
    clean_img = strip_and_normalize_image(data)
    orig_w, orig_h = clean_img.size
    uid = uuid.uuid4().hex[:12]
    clean_uid = f"{user_id}_{uid}"

    if subfolder == "avatars":
        # Avatars: square cropped/fitted to max 512x512
        avatar_size = min(max(orig_w, orig_h), 512)
        avatar_img = ImageOps.fit(clean_img, (avatar_size, avatar_size), method=Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        avatar_img.save(buf, format="WEBP", quality=85, method=6)
        avatar_filename = f"{clean_uid}_avatar.webp"
        avatar_url, _ = storage_service.save_file(buf.getvalue(), avatar_filename, subfolder="avatars")

        return {
            "original_url": avatar_url,
            "feed_url": avatar_url,
            "thumbnail_url": avatar_url,
            "avatar_url": avatar_url,
            "width": avatar_size,
            "height": avatar_size,
            "alt_text": alt_text.strip() if alt_text else "User avatar",
            "media_type": "image",
        }

    # Posts:
    # 1. Full variant (max 1080px wide to save Supabase free tier storage)
    full_img = clean_img.copy()
    if full_img.width > 1080:
        new_h = int(full_img.height * (1080 / full_img.width))
        full_img = full_img.resize((1080, new_h), Image.Resampling.LANCZOS)
    elif max(full_img.size) > 1080:
        full_img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)

    full_buf = io.BytesIO()
    full_img.save(full_buf, format="WEBP", quality=85, method=6)
    full_url, _ = storage_service.save_file(full_buf.getvalue(), f"{clean_uid}_full.webp", subfolder="posts")

    # 2. Feed variant (1080x1080 fit/crop)
    feed_img = ImageOps.fit(clean_img, (1080, 1080), method=Image.Resampling.LANCZOS)
    feed_buf = io.BytesIO()
    feed_img.save(feed_buf, format="WEBP", quality=85, method=6)
    feed_url, _ = storage_service.save_file(feed_buf.getvalue(), f"{clean_uid}_feed.webp", subfolder="posts")

    # 3. Thumbnail variant (300x300 fit/crop)
    thumb_img = ImageOps.fit(clean_img, (300, 300), method=Image.Resampling.LANCZOS)
    thumb_buf = io.BytesIO()
    thumb_img.save(thumb_buf, format="WEBP", quality=80, method=6)
    thumb_url, _ = storage_service.save_file(thumb_buf.getvalue(), f"{clean_uid}_thumb.webp", subfolder="posts")

    return {
        "original_url": full_url,
        "feed_url": feed_url,
        "thumbnail_url": thumb_url,
        "width": full_img.width,
        "height": full_img.height,
        "alt_text": alt_text.strip() if alt_text else None,
        "media_type": "image",
    }
