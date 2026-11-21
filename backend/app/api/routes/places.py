from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.place import Place
from app.models.user import User
from app.schemas.catalog import PlaceResponse
from app.services.discovery import haversine_distance
from app.services.places_service import (
    geocode_location_nominatim,
    fetch_overpass_places_around,
    sync_real_places,
)
from app.services.embeddings import generate_embedding

router = APIRouter(prefix="/places", tags=["places"])

@router.get("", response_model=list[PlaceResponse])
def list_places(
    q: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
    user_lat: float | None = Query(default=None),
    user_lon: float | None = Query(default=None),
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # Auto-seed authentic regional places if table is empty
    count = db.scalar(select(func.count(Place.id))) or 0
    if count == 0:
        sync_real_places(db)

    stmt = select(Place)
    if city:
        stmt = stmt.where(Place.city.ilike(f"%{city.strip()}%"))
    if category:
        stmt = stmt.where(Place.category.ilike(f"%{category.strip()}%"))
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Place.name.ilike(term),
                Place.description.ilike(term),
                Place.category.ilike(term),
                Place.address.ilike(term),
                Place.city.ilike(term),
            )
        )
    stmt = stmt.limit(limit)
    places = list(db.scalars(stmt))

    results = []
    for p in places:
        dist = None
        if user_lat is not None and user_lon is not None:
            dist = haversine_distance(user_lat, user_lon, p.latitude, p.longitude)
        res = PlaceResponse.model_validate(p)
        res.distance_km = round(dist, 2) if dist is not None else None
        results.append(res)

    if user_lat is not None and user_lon is not None:
        results.sort(key=lambda r: r.distance_km if r.distance_km is not None else 999999)

    return results

@router.post("/sync")
def trigger_places_sync(
    city: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can trigger places sync.")
    return sync_real_places(db, city=city)

@router.get("/map/markers")
def get_map_markers(
    user_lat: float | None = Query(default=None),
    user_lon: float | None = Query(default=None),
    radius_km: float = Query(default=35.0, ge=1.0, le=500.0),
    query: str | None = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
):
    from app.models.event import Event

    # If search query provided, geocode via Nominatim with 1 req/s rate-limiting
    if query and query.strip():
        geocoded = geocode_location_nominatim(query.strip())
        if geocoded:
            user_lat = geocoded["lat"]
            user_lon = geocoded["lon"]

    # Auto-seed authentic regional places if table is empty
    count = db.scalar(select(func.count(Place.id))) or 0
    if count == 0:
        sync_real_places(db)

    # If coordinates are known, check if we have local places nearby
    if user_lat is not None and user_lon is not None:
        local_db_count = 0
        all_db_places = list(db.scalars(select(Place)))
        for p in all_db_places:
            if haversine_distance(user_lat, user_lon, p.latitude, p.longitude) <= radius_km:
                local_db_count += 1

        # If no DB places within radius, dynamically query OSM Overpass around searched coordinates
        if local_db_count == 0:
            osm_places = fetch_overpass_places_around(user_lat, user_lon, radius_km=min(radius_km, 30.0))
            for item in osm_places:
                # Deduplicate before saving
                existing_p = db.scalar(
                    select(Place.id).where(
                        (Place.name == item["name"]) &
                        (Place.latitude.between(item["latitude"] - 0.001, item["latitude"] + 0.001))
                    )
                )
                if not existing_p:
                    emb = generate_embedding(f"{item['name']} {item['category']} {item['address']}")
                    new_place = Place(
                        name=item["name"],
                        description=item["description"],
                        category=item["category"],
                        address=item["address"],
                        city=item["city"],
                        latitude=item["latitude"],
                        longitude=item["longitude"],
                        source="OpenStreetMap",
                        embedding=emb,
                    )
                    db.add(new_place)
            if osm_places:
                db.commit()

    markers = []

    # 1. Real Places strictly filtered by radius_km from searched coordinates
    places = list(db.scalars(select(Place)))
    for p in places:
        dist = None
        if user_lat is not None and user_lon is not None:
            dist = haversine_distance(user_lat, user_lon, p.latitude, p.longitude)
            if dist > radius_km:
                # Exclude venues beyond search radius (prevents Pune showing for Kolhapur)
                continue
        markers.append({
            "id": f"place_{p.id}",
            "type": "place",
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "address": p.address,
            "city": p.city,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "image_url": p.image_url,
            "distance_km": round(dist, 1) if dist is not None else None,
            "link": "/places",
        })

    # 2. Events strictly filtered by radius_km
    evts = list(
        db.scalars(
            select(Event).where(
                (Event.is_cancelled == False) & (Event.latitude.is_not(None)) & (Event.longitude.is_not(None))
            )
        )
    )
    for e in evts:
        dist = None
        if user_lat is not None and user_lon is not None and e.latitude and e.longitude:
            dist = haversine_distance(user_lat, user_lon, e.latitude, e.longitude)
            if dist > radius_km:
                continue
        markers.append({
            "id": f"event_{e.id}",
            "type": "event",
            "name": e.title,
            "category": e.category,
            "description": e.description[:120],
            "address": e.location,
            "city": e.location.split(",")[-1].strip(),
            "latitude": e.latitude,
            "longitude": e.longitude,
            "distance_km": round(dist, 1) if dist is not None else None,
            "link": "/events",
        })

    # Sort markers by distance ascending
    if user_lat is not None and user_lon is not None:
        markers.sort(key=lambda m: m["distance_km"] if m["distance_km"] is not None else 999999)

    return markers
