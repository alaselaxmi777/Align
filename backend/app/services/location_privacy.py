"""
Privacy-Aware Location Services for ALIGN.

Provides:
1. Grid snapping (approximate ~1 km grid snapping via 0.01 degree precision).
2. City centroid resolution (for city-level privacy).
3. Distance hiding and privacy tier management ('exact', 'approximate', 'city', 'hidden').
4. Coarse distance band categorization (<5 km, 5–15 km, 15–30 km, 30+ km).
5. Cross-user coordinate sanitization (guarantees raw coordinates of other users are never returned).
"""

import math
from typing import Any

# Representative centroid coordinates for major discovery hubs
CITY_CENTROIDS: dict[str, tuple[float, float]] = {
    "pune": (18.5204, 73.8567),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "delhi": (28.7041, 77.1025),
    "new delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "san francisco": (37.7749, -122.4194),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "berlin": (52.5200, 13.4050),
    "singapore": (1.3521, 103.8198),
}

def snap_to_grid(lat: float, lon: float, precision_degrees: float = 0.01) -> tuple[float, float]:
    """
    Snaps raw coordinates to a geographic grid.
    0.01 degrees corresponds to ~1.11 km at the equator.
    """
    snapped_lat = round(round(lat / precision_degrees) * precision_degrees, 4)
    snapped_lon = round(round(lon / precision_degrees) * precision_degrees, 4)
    return snapped_lat, snapped_lon

def resolve_city_centroid(city_or_location: str) -> tuple[float, float] | None:
    """Finds centroid coordinates for a given city/location string."""
    if not city_or_location:
        return None
    loc_clean = city_or_location.lower().strip()
    for city, coords in CITY_CENTROIDS.items():
        if city in loc_clean:
            return coords
    return None

def obfuscate_location(
    lat: float | None,
    lon: float | None,
    city_name: str | None,
    privacy_level: str = "approximate",
) -> tuple[float | None, float | None, str]:
    """
    Applies user-selected privacy level to geographical coordinates.
    Returns: (obfuscated_lat, obfuscated_lon, display_description)
    """
    level = (privacy_level or "approximate").lower().strip()

    if level in {"hidden", "off", "none"}:
        city = (city_name or "Location").split(",")[0].strip()
        return None, None, f"{city} (distance hidden by user)"

    if lat is None or lon is None:
        if city_name:
            centroid = resolve_city_centroid(city_name)
            if centroid:
                return centroid[0], centroid[1], city_name.split(",")[0].strip()
        return None, None, "Location flexible"

    if level == "exact":
        city = (city_name or "Area").split(",")[0].strip()
        return lat, lon, f"{city} (exact)"

    if level == "city":
        city = (city_name or "City").split(",")[0].strip()
        centroid = resolve_city_centroid(city_name or "")
        if centroid:
            return centroid[0], centroid[1], city
        return round(lat, 1), round(lon, 1), city

    # Default: "approximate" (~1 km grid snapping)
    s_lat, s_lon = snap_to_grid(lat, lon, precision_degrees=0.01)
    city = (city_name or "Area").split(",")[0].strip()
    return s_lat, s_lon, f"{city} (~1 km approximate)"

def get_coarse_distance_band(dist_km: float | None) -> str:
    """
    Categorizes precise distances into coarse privacy bands:
    - '< 5 km'
    - '5–15 km'
    - '15–30 km'
    - '30+ km'
    """
    if dist_km is None:
        return "Distance unavailable"
    if dist_km < 5.0:
        return "< 5 km"
    if dist_km <= 15.0:
        return "5–15 km"
    if dist_km <= 30.0:
        return "15–30 km"
    return "30+ km"

def sanitize_public_peer_location(
    peer_profile: Any,
    viewer_lat: float | None,
    viewer_lon: float | None,
) -> dict[str, Any]:
    """
    Strips raw coordinates of another user and returns only coarse distance band and city name.
    Strictly prevents coordinate triangulation and stalking.
    """
    if not peer_profile:
        return {"city": "Online", "distance_band": "Online", "latitude": None, "longitude": None}

    loc_str = getattr(peer_profile, "location", "") or "Online"
    city = loc_str.split(",")[0].strip()
    privacy = getattr(peer_profile, "location_privacy", "approximate") or "approximate"

    if privacy in {"hidden", "off"}:
        return {
            "city": city,
            "distance_band": "Distance hidden by user",
            "latitude": None,
            "longitude": None,
        }

    raw_lat = getattr(peer_profile, "latitude", None)
    raw_lon = getattr(peer_profile, "longitude", None)

    dist_band = "Location flexible"
    if viewer_lat is not None and viewer_lon is not None and raw_lat is not None and raw_lon is not None:
        from app.services.discovery import haversine_distance
        obf_lat, obf_lon, _ = obfuscate_location(raw_lat, raw_lon, loc_str, privacy)
        if obf_lat is not None and obf_lon is not None:
            km = haversine_distance(viewer_lat, viewer_lon, obf_lat, obf_lon)
            dist_band = get_coarse_distance_band(km)

    return {
        "city": city,
        "distance_band": dist_band,
        "latitude": None,  # NEVER exposed to other users
        "longitude": None, # NEVER exposed to other users
    }
