import os
import re
import uuid
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Union
from PIL import Image
from app.services.storage_service import storage_service, UPLOAD_DIR

logger = logging.getLogger(__name__)

# Video Limits
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB
MAX_VIDEO_DURATION_SECONDS = 300.0        # 5 minutes
MAX_REEL_DURATION_SECONDS = 90.0          # 90 seconds
FFMPEG_TIMEOUT_SECONDS = 120.0

ALLOWED_VIDEO_MIMES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

TMP_DIR = UPLOAD_DIR / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

class VideoProcessingError(Exception):
    """Base exception for video processing errors."""
    pass

class FFmpegNotFoundError(VideoProcessingError):
    """Raised when FFmpeg binary is missing from system and environment."""
    pass

class InvalidVideoFormatError(VideoProcessingError):
    """Raised when file magic bytes do not correspond to an allowed video format."""
    pass

class VideoDurationExceededError(VideoProcessingError):
    """Raised when video duration exceeds allowed thresholds (90s for reels, 300s for feed)."""
    pass

class VideoSizeExceededError(VideoProcessingError):
    """Raised when video file exceeds the maximum allowed size (50MB)."""
    pass

def get_ffmpeg_binary() -> str:
    """Resolves verified FFmpeg executable."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe) and os.access(exe, os.X_OK):
            return exe
    except Exception:
        pass
    p = shutil.which("ffmpeg")
    if p:
        return p
    for candidate in ["/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FFmpegNotFoundError(
        "FFmpeg executable not found. Video transcoding is unavailable on this server."
    )

def validate_video_magic_bytes(header_or_data: bytes) -> str:
    """Validates video signature."""
    if len(header_or_data) < 16:
        raise InvalidVideoFormatError("Video file is too small to be valid.")

    if b"ftyp" in header_or_data[:32] or b"moov" in header_or_data[:32]:
        return "video/mp4"
    elif header_or_data.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    elif len(header_or_data) >= 8 and (header_or_data[4:8] == b"wide" or header_or_data[4:8] == b"mdat"):
        return "video/quicktime"

    raise InvalidVideoFormatError("Invalid video format. Allowed formats: MP4, WebM, MOV.")

def _probe_video_sync(file_path: Path) -> dict:
    """Probes video duration and dimensions using FFmpeg banner output."""
    ffmpeg = get_ffmpeg_binary()
    try:
        res = subprocess.run(
            [ffmpeg, "-i", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoProcessingError("Video probe timed out after 30 seconds.") from exc

    stderr = res.stderr or ""
    duration = 0.0
    m_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if m_dur:
        h, m, s = m_dur.groups()
        duration = float(h) * 3600 + float(m) * 60 + float(s)
    else:
        if "Invalid data found when processing input" in stderr:
            raise InvalidVideoFormatError("The uploaded file is not a valid or readable video stream.")

    width, height = 720, 1280
    m_res = re.search(r"Stream #0:\d+.*Video:.*,\s*(\d+)x(\d+)", stderr)
    if m_res:
        width = int(m_res.group(1))
        height = int(m_res.group(2))

    return {
        "duration_seconds": round(duration, 2),
        "width": width,
        "height": height,
        "is_vertical": height > width,
    }

def _transcode_video_to_mp4_sync(input_path: Path, output_path: Path, timeout_sec: float = FFMPEG_TIMEOUT_SECONDS) -> None:
    """
    Transcodes input video to standard H.264/AAC MP4 with +faststart for instant streaming.
    Constrains maximum width to 720p (-vf scale='min(720,iw)':-2) to optimize file size and Supabase storage.
    """
    ffmpeg = get_ffmpeg_binary()
    cmd = [
        ffmpeg,
        "-i", str(input_path),
        "-vf", "scale='min(720,iw)':-2",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "25",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise VideoProcessingError(f"Video transcoding timed out after {timeout_sec} seconds.") from exc

    if res.returncode != 0:
        output_path.unlink(missing_ok=True)
        logger.error(f"FFmpeg transcode failed (exit {res.returncode}): {res.stderr}")
        err_msg = res.stderr[-500:].strip() if res.stderr else f"FFmpeg failed with exit code {res.returncode}"
        raise VideoProcessingError(f"Video transcoding failed: {err_msg}")

def _extract_poster_frame_sync(video_path: Path, poster_path: Path, timestamp_sec: float = 1.0, timeout_sec: float = 30.0) -> None:
    """Extracts a poster frame and saves it as a clean WebP thumbnail."""
    ffmpeg = get_ffmpeg_binary()
    tmp_jpg = poster_path.with_suffix(".tmp.jpg")
    try:
        cmd = [
            ffmpeg,
            "-ss", str(timestamp_sec),
            "-i", str(video_path),
            "-vframes", "1",
            "-f", "image2",
            "-y",
            str(tmp_jpg),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        if res.returncode != 0 or not tmp_jpg.exists():
            # Fallback to 0.0s if timestamp was beyond duration
            cmd[2] = "0.0"
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)

        if tmp_jpg.exists():
            with Image.open(tmp_jpg) as img:
                clean = Image.frombytes(img.mode, img.size, img.tobytes())
                clean.save(poster_path, format="WEBP", quality=85)
        else:
            raise VideoProcessingError("Failed to extract video poster frame.")
    finally:
        tmp_jpg.unlink(missing_ok=True)

# Synchronous public helpers for backwards compatibility
def probe_video(file_path: Path) -> dict:
    return _probe_video_sync(file_path)

def transcode_video_to_mp4(input_path: Path, output_path: Path) -> None:
    _transcode_video_to_mp4_sync(input_path, output_path)

def extract_poster_frame(video_path: Path, poster_path: Path, timestamp_sec: float = 1.0) -> None:
    _extract_poster_frame_sync(video_path, poster_path, timestamp_sec=timestamp_sec)

async def process_video_upload(
    data_or_path: Union[bytes, Path],
    user_id: int | str = 0,
    is_reel: bool = False,
) -> dict:
    """
    Validates, probes, transcodes to 720p H.264/AAC MP4 with +faststart, extracts poster frame,
    and uploads through storage_service (Supabase Storage 'align-media' bucket).
    - Reel MP4s are saved under 'reels/{user_id}_{uid}.mp4'
    - Poster images are saved under 'posters/{user_id}_{uid}_poster.webp'
    Runs CPU-bound operations in a worker thread to keep the asyncio loop unblocked.
    """
    uid = uuid.uuid4().hex[:12]
    clean_uid = f"{user_id}_{uid}"
    tmp_input: Path
    owns_input = False

    if isinstance(data_or_path, (bytes, bytearray)):
        if len(data_or_path) > MAX_VIDEO_SIZE_BYTES:
            raise VideoSizeExceededError(f"Video file exceeds maximum allowed size of {MAX_VIDEO_SIZE_BYTES // (1024 * 1024)} MB.")
        validate_video_magic_bytes(data_or_path[:64])
        tmp_input = TMP_DIR / f"raw_{clean_uid}.tmp"
        with open(tmp_input, "wb") as f:
            f.write(data_or_path)
        owns_input = True
    else:
        tmp_input = Path(data_or_path)
        with open(tmp_input, "rb") as f:
            header = f.read(64)
        validate_video_magic_bytes(header)

    tmp_transcoded = TMP_DIR / f"transcoded_{clean_uid}.mp4"
    tmp_poster = TMP_DIR / f"poster_{clean_uid}.webp"

    try:
        # Probe video metadata in thread
        info = await asyncio.to_thread(_probe_video_sync, tmp_input)
        duration = info["duration_seconds"]

        # Enforce duration constraints (90s for reels, 300s for feed)
        if is_reel and duration > MAX_REEL_DURATION_SECONDS:
            raise VideoDurationExceededError(
                f"Reel duration exceeds maximum allowed limit of {int(MAX_REEL_DURATION_SECONDS)} seconds (detected: {duration}s)."
            )
        if not is_reel and duration > MAX_VIDEO_DURATION_SECONDS:
            raise VideoDurationExceededError(
                f"Video duration exceeds maximum allowed limit of {int(MAX_VIDEO_DURATION_SECONDS)} seconds (detected: {duration}s)."
            )

        # Transcode in thread
        await asyncio.to_thread(_transcode_video_to_mp4_sync, tmp_input, tmp_transcoded)

        # Extract poster frame in thread
        extract_time = min(1.0, max(0.0, duration / 2.0)) if duration < 1.0 else 1.0
        await asyncio.to_thread(_extract_poster_frame_sync, tmp_transcoded, tmp_poster, extract_time)

        # Read transcoded files for storage service
        with open(tmp_transcoded, "rb") as vf:
            transcoded_bytes = vf.read()
        with open(tmp_poster, "rb") as pf:
            poster_bytes = pf.read()

        video_subfolder = "reels" if is_reel else "videos"
        dest_video_name = f"{clean_uid}.mp4"
        dest_poster_name = f"{clean_uid}_poster.webp"

        # Upload MP4 to reels/ (or videos/) and poster frame to posters/
        video_url, _ = storage_service.save_file(transcoded_bytes, dest_video_name, subfolder=video_subfolder)
        thumbnail_url, _ = storage_service.save_file(poster_bytes, dest_poster_name, subfolder="posters")

        return {
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "duration_seconds": duration,
            "width": info["width"],
            "height": info["height"],
            "is_vertical": info["is_vertical"],
        }
    finally:
        if owns_input:
            tmp_input.unlink(missing_ok=True)
        tmp_transcoded.unlink(missing_ok=True)
        tmp_poster.unlink(missing_ok=True)
