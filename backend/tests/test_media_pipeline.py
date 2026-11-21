import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.post import Post, PostMedia
from app.models.connection import UserConnection
from app.services.media_processor import process_image_upload, validate_image_bytes

def create_sample_jpeg_bytes(width: int = 400, height: int = 400, color: tuple = (255, 0, 0)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def create_sample_jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (200, 200), color=(0, 255, 0))
    buf = io.BytesIO()
    # Create raw EXIF data with Camera Make / Model / GPS metadata tags
    exif = img.getexif()
    exif[0x010f] = "AlignCameraTest"
    exif[0x0110] = "ModelX-GPS-Enabled"
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()

def test_media_processor_variant_generation():
    raw_bytes = create_sample_jpeg_bytes(1600, 1200)
    result = process_image_upload(raw_bytes, alt_text="Sahyadri trek scenic vista")

    assert result["media_type"] == "image"
    assert result["alt_text"] == "Sahyadri trek scenic vista"
    assert result["original_url"].endswith("_full.webp")
    assert result["feed_url"].endswith("_feed.webp")
    assert result["thumbnail_url"].endswith("_thumb.webp")
    assert result["width"] == 1600
    assert result["height"] == 1200

def test_media_processor_strips_exif_completely():
    raw_with_exif = create_sample_jpeg_with_exif()
    # Confirm the input indeed had EXIF
    with Image.open(io.BytesIO(raw_with_exif)) as raw_check:
        assert raw_check.getexif() is not None
        assert raw_check.getexif().get(0x010f) == "AlignCameraTest"

    # Process and save
    result = process_image_upload(raw_with_exif)

    # Read back the saved full variant
    from app.services.storage_service import storage_service
    full_rel = result["original_url"].removeprefix("/uploads/").lstrip("/")
    saved_path = storage_service.base_dir / full_rel
    assert saved_path.exists()

    with Image.open(saved_path) as saved_img:
        assert saved_img.format == "WEBP"
        # In Pillow, WebP with no EXIF returns an empty dict or None for getexif
        exif_data = saved_img.getexif()
        assert not exif_data or len(exif_data) == 0

def test_media_processor_rejects_spoofed_content():
    fake_png = b"Not a PNG at all, just plain text payload claiming to be image"
    with pytest.raises(ValueError, match="does not match allowed image formats"):
        validate_image_bytes(fake_png, "image/png")

def test_media_processor_rejects_oversize_image():
    # 11 MB dummy buffer
    oversize = b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        validate_image_bytes(oversize)

def test_upload_image_api_endpoint(client: TestClient, db: Session):
    # Register/login user
    client.post("/api/v1/auth/register", json={
        "name": "Photographer User",
        "email": "photographer@align.local",
        "password": "Password123!",
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "photographer@align.local",
        "password": "Password123!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sample_bytes = create_sample_jpeg_bytes(800, 600)
    files = {"file": ("test_pic.jpg", sample_bytes, "image/jpeg")}
    data = {"alt_text": "Fort view in Pune"}

    res = client.post("/api/v1/uploads/image", files=files, data=data, headers=headers)
    assert res.status_code == 201
    resp_data = res.json()
    assert resp_data["status"] == "success"
    assert "feed_url" in resp_data
    assert "thumbnail_url" in resp_data
    assert resp_data["alt_text"] == "Fort view in Pune"

def test_carousel_post_creation_and_connections_privacy(client: TestClient, db: Session):
    # 1. User A (creator)
    res_a = client.post("/api/v1/auth/register", json={
        "name": "User Alpha",
        "email": "alpha_creator@align.local",
        "password": "Password123!",
    })
    user_a_id = res_a.json()["id"]
    login_a = client.post("/api/v1/auth/login", json={
        "email": "alpha_creator@align.local",
        "password": "Password123!",
    })
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. User B (unconnected viewer)
    res_b = client.post("/api/v1/auth/register", json={
        "name": "User Beta",
        "email": "beta_viewer@align.local",
        "password": "Password123!",
    })
    user_b_id = res_b.json()["id"]
    login_b = client.post("/api/v1/auth/login", json={
        "email": "beta_viewer@align.local",
        "password": "Password123!",
    })
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a carousel post with 2 images, visibility: connections_only
    carousel_payload = {
        "content": "Sunset at Sinhagad Fort with friends! #trek #pune",
        "visibility": "connections_only",
        "location_area": "Sinhagad, Pune",
        "media_items": [
            {
                "position": 0,
                "media_type": "image",
                "original_url": "/uploads/posts/img_1_full.webp",
                "feed_url": "/uploads/posts/img_1_feed.webp",
                "thumbnail_url": "/uploads/posts/img_1_thumb.webp",
                "width": 1080,
                "height": 1080,
                "alt_text": "Sinhagad fort gate",
            },
            {
                "position": 1,
                "media_type": "image",
                "original_url": "/uploads/posts/img_2_full.webp",
                "feed_url": "/uploads/posts/img_2_feed.webp",
                "thumbnail_url": "/uploads/posts/img_2_thumb.webp",
                "width": 1080,
                "height": 1080,
                "alt_text": "Valley sunset view",
            },
        ],
    }

    create_res = client.post("/api/v1/feed", json=carousel_payload, headers=headers_a)
    assert create_res.status_code == 201
    post_data = create_res.json()
    post_id = post_data["id"]
    assert len(post_data["media"]) == 2
    assert post_data["visibility"] == "connections_only"
    assert post_data["location_area"] == "Sinhagad, Pune"

    # User B attempts to view User A's connections_only post detail -> 403 Forbidden
    detail_res_b = client.get(f"/api/v1/feed/{post_id}", headers=headers_b)
    assert detail_res_b.status_code == 403
    assert "visible to connections only" in detail_res_b.json()["detail"]

    # Anonymous user attempts to view -> 403 Forbidden
    anon_res = client.get(f"/api/v1/feed/{post_id}")
    assert anon_res.status_code == 403

    # Now create an accepted connection between User A and User B
    conn = UserConnection(sender_id=user_a_id, receiver_id=user_b_id, status="accepted")
    db.add(conn)
    db.commit()

    # User B can now view the post!
    detail_res_b_connected = client.get(f"/api/v1/feed/{post_id}", headers=headers_b)
    assert detail_res_b_connected.status_code == 200
    assert detail_res_b_connected.json()["id"] == post_id
    assert len(detail_res_b_connected.json()["media"]) == 2
