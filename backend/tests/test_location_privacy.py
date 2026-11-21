"""
Tests for Privacy-Aware Location Services and Cross-User Data Protection.
"""

import pytest
from app.services.location_privacy import (
    snap_to_grid,
    resolve_city_centroid,
    obfuscate_location,
    get_coarse_distance_band,
    sanitize_public_peer_location,
)
from app.models.user import User, Profile

def test_snap_to_grid():
    lat, lon = 18.52043, 73.85674
    # 0.01 degrees snapping
    s_lat, s_lon = snap_to_grid(lat, lon, precision_degrees=0.01)
    assert s_lat == 18.52
    assert s_lon == 73.86

    # 0.045 degrees snapping (~5 km)
    s_lat_5, s_lon_5 = snap_to_grid(lat, lon, precision_degrees=0.045)
    assert round(s_lat_5, 2) == 18.54
    assert round(s_lon_5, 2) == 73.84

def test_resolve_city_centroid():
    pune_coords = resolve_city_centroid("Pune, Maharashtra, India")
    assert pune_coords == (18.5204, 73.8567)

    sf_coords = resolve_city_centroid("San Francisco, CA")
    assert sf_coords == (37.7749, -122.4194)

    unknown = resolve_city_centroid("Random Nowhere Ville 123")
    assert unknown is None

def test_obfuscate_location():
    raw_lat, raw_lon = 18.52043, 73.85674

    # 1. Exact
    e_lat, e_lon, desc = obfuscate_location(raw_lat, raw_lon, "Pune, India", privacy_level="exact")
    assert e_lat == raw_lat
    assert e_lon == raw_lon
    assert "exact" in desc

    # 2. Approximate
    a_lat, a_lon, desc = obfuscate_location(raw_lat, raw_lon, "Pune, India", privacy_level="approximate")
    assert a_lat == 18.52
    assert a_lon == 73.86
    assert "approximate" in desc

    # 3. City
    c_lat, c_lon, desc = obfuscate_location(raw_lat, raw_lon, "Pune, India", privacy_level="city")
    assert c_lat == 18.5204
    assert c_lon == 73.8567
    assert desc == "Pune"

    # 4. Hidden
    h_lat, h_lon, desc = obfuscate_location(raw_lat, raw_lon, "Pune, India", privacy_level="hidden")
    assert h_lat is None
    assert h_lon is None
    assert "distance hidden" in desc

def test_get_coarse_distance_band():
    assert get_coarse_distance_band(None) == "Distance unavailable"
    assert get_coarse_distance_band(2.1) == "< 5 km"
    assert get_coarse_distance_band(8.5) == "5–15 km"
    assert get_coarse_distance_band(22.0) == "15–30 km"
    assert get_coarse_distance_band(65.0) == "30+ km"

def test_sanitize_public_peer_location():
    # Peer user with approximate privacy
    class MockProfile:
        location = "Pune, Maharashtra"
        latitude = 18.5204
        longitude = 73.8567
        location_privacy = "approximate"

    peer = MockProfile()
    viewer_lat, viewer_lon = 18.5300, 73.8500

    sanitized = sanitize_public_peer_location(peer, viewer_lat, viewer_lon)
    # Raw coordinates must NEVER be leaked
    assert sanitized["latitude"] is None
    assert sanitized["longitude"] is None
    assert sanitized["city"] == "Pune"
    assert sanitized["distance_band"] == "< 5 km"

    # Peer user with hidden privacy
    peer.location_privacy = "hidden"
    sanitized_hidden = sanitize_public_peer_location(peer, viewer_lat, viewer_lon)
    assert sanitized_hidden["latitude"] is None
    assert sanitized_hidden["longitude"] is None
    assert sanitized_hidden["distance_band"] == "Distance hidden by user"

def test_api_peer_location_sanitization(client, db):
    """Integration test asserting that GET /users never exposes raw coordinates of another user."""
    # Create two users
    u1 = User(email="viewer@example.com", name="Viewer User", hashed_password="pw", is_active=True, is_verified=True)
    u2 = User(email="peer@example.com", name="Peer User", hashed_password="pw", is_active=True, is_verified=True)
    db.add_all([u1, u2])
    db.commit()

    p1 = Profile(user_id=u1.id, location="Pune", latitude=18.5200, longitude=73.8500, location_privacy="exact")
    p2 = Profile(user_id=u2.id, location="Pune", latitude=18.5300, longitude=73.8600, location_privacy="approximate")
    db.add_all([p1, p2])
    db.commit()

    # List users endpoint
    resp = client.get("/api/v1/users?page=1&limit=10")
    assert resp.status_code == 200
    users_data = resp.json()
    peer_item = next((u for u in users_data if u["id"] == u2.id), None)
    assert peer_item is not None

    # Verify no raw coordinates are returned in public user list
    if peer_item.get("profile"):
        assert peer_item["profile"]["latitude"] is None
        assert peer_item["profile"]["longitude"] is None
    assert peer_item.get("distance_band") in ["< 5 km", "Location flexible", "Distance unavailable", "Online"]

    # Get user by id
    resp_id = client.get(f"/api/v1/users/{u2.id}")
    assert resp_id.status_code == 200
    peer_detail = resp_id.json()
    if peer_detail.get("profile"):
        assert peer_detail["profile"]["latitude"] is None
        assert peer_detail["profile"]["longitude"] is None
    assert peer_detail.get("distance_band") is not None
