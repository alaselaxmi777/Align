import io
import os
import tempfile
from pathlib import Path
import subprocess
import pytest
from app.services.video_processor import get_ffmpeg_binary, validate_video_magic_bytes, probe_video
from app.services.storage_service import UPLOAD_DIR

def generate_synthetic_mp4(duration_sec: int = 2, width: int = 360, height: int = 640) -> bytes:
    """Generates a real, synthetic H.264/AAC MP4 test video in memory using FFmpeg."""
    ffmpeg = get_ffmpeg_binary()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_name = tmp.name

    try:
        cmd = [
            ffmpeg,
            "-f", "lavfi",
            "-i", f"testsrc=duration={duration_sec}:size={width}x{height}:rate=15",
            "-f", "lavfi",
            "-i", f"sine=frequency=1000:duration={duration_sec}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "64k",
            "-movflags", "+faststart",
            "-y",
            tmp_name,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg synthetic generator failed: {res.stderr.decode()}")
        with open(tmp_name, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_video_magic_bytes_and_probe(tmp_path):
    video_bytes = generate_synthetic_mp4(duration_sec=2, width=360, height=640)
    mime = validate_video_magic_bytes(video_bytes)
    assert mime == "video/mp4"

    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(video_bytes)

    probe = probe_video(test_file)
    assert probe["duration_seconds"] >= 1.5
    assert probe["width"] == 360
    assert probe["height"] == 640
    assert probe["is_vertical"] is True

    # Invalid bytes
    with pytest.raises(ValueError, match="Invalid video format"):
        validate_video_magic_bytes(b"not a video file at all 1234567890")


def test_upload_video_endpoint(client, auth_headers):
    video_bytes = generate_synthetic_mp4(duration_sec=2, width=360, height=640)

    # 1. Reel upload (is_reel=True)
    files = {"file": ("test_reel.mp4", video_bytes, "video/mp4")}
    data = {"is_reel": "true"}
    resp = client.post("/api/v1/uploads/video", files=files, data=data, headers=auth_headers)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["status"] == "success"
    assert "/uploads/reels/" in payload["video_url"]
    assert "/uploads/reels/" in payload["thumbnail_url"]
    assert payload["duration_seconds"] >= 1.5
    assert payload["is_vertical"] is True

    # 2. Feed video upload (is_reel=False)
    files2 = {"file": ("feed_video.mp4", video_bytes, "video/mp4")}
    data2 = {"is_reel": "false"}
    resp2 = client.post("/api/v1/uploads/video", files=files2, data=data2, headers=auth_headers)
    assert resp2.status_code == 201
    payload2 = resp2.json()
    assert "/uploads/videos/" in payload2["video_url"]
    assert "/uploads/videos/" in payload2["thumbnail_url"]


def test_create_and_query_reel(client, auth_headers):
    video_bytes = generate_synthetic_mp4(duration_sec=2)
    files = {"file": ("reel_vid.mp4", video_bytes, "video/mp4")}
    upload_res = client.post("/api/v1/uploads/video", files=files, data={"is_reel": "true"}, headers=auth_headers).json()

    create_payload = {
        "title": "Sahyadri Monsoon Fort Trek Reel",
        "category": "Fort Trekking",
        "video_url": upload_res["video_url"],
        "thumbnail_url": upload_res["thumbnail_url"],
        "duration_seconds": upload_res["duration_seconds"],
        "visibility": "public",
        "caption": "Exploring Rajgad Fort in heavy monsoon fog! #Sahyadri #Trek",
        "tags": ["Sahyadri", "Trek", "Monsoon"],
    }
    create_resp = client.post("/api/v1/reels", json=create_payload, headers=auth_headers)
    assert create_resp.status_code == 201
    reel = create_resp.json()
    assert reel["title"] == "Sahyadri Monsoon Fort Trek Reel"
    assert reel["category"] == "Fort Trekking"
    assert reel["duration_seconds"] == upload_res["duration_seconds"]
    assert reel["visibility"] == "public"
    assert reel["id"] > 0

    # View count increment
    view_resp = client.post(f"/api/v1/reels/{reel['id']}/view")
    assert view_resp.status_code == 200
    assert view_resp.json()["views_count"] >= 1

    # Like reel
    like_resp = client.post(f"/api/v1/reels/{reel['id']}/like", headers=auth_headers)
    assert like_resp.status_code == 200
    assert like_resp.json()["is_liked"] is True

    # Query reels list
    list_resp = client.get("/api/v1/reels?category=Fort Trekking", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    found = next((r for r in items if r["id"] == reel["id"]), None)
    assert found is not None
    assert found["is_liked"] is True
    assert found["likes_count"] == 1


def test_reel_duration_cap(client, auth_headers):
    # Reject reel with duration > 90 seconds
    bad_payload = {
        "title": "Excessive Duration Reel",
        "category": "Travel",
        "video_url": "/uploads/reels/fake.mp4",
        "thumbnail_url": "/uploads/reels/fake.webp",
        "duration_seconds": 95.0,
        "visibility": "public",
    }
    resp = client.post("/api/v1/reels", json=bad_payload, headers=auth_headers)
    assert resp.status_code in (400, 422)


def test_reel_connections_only_privacy(client, auth_headers):
    # User 1 creates connections_only reel
    create_payload = {
        "title": "Private Katta Discussion",
        "category": "General",
        "video_url": "/uploads/reels/private.mp4",
        "thumbnail_url": "/uploads/reels/private.webp",
        "duration_seconds": 15.0,
        "visibility": "connections_only",
    }
    resp = client.post("/api/v1/reels", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    reel_id = resp.json()["id"]

    # Author can see it
    auth_list = client.get("/api/v1/reels", headers=auth_headers).json()
    assert any(r["id"] == reel_id for r in auth_list)

    # Anonymous / unauthenticated user CANNOT see connections_only reel
    anon_list = client.get("/api/v1/reels").json()
    assert not any(r["id"] == reel_id for r in anon_list)
