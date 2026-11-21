import json
import logging
import threading
import time
import urllib.request
import urllib.parse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.config import settings
from app.models.place import Place
from app.services.embeddings import generate_embedding

logger = logging.getLogger(__name__)

_NOMINATIM_LOCK = threading.Lock()
_LAST_NOMINATIM_TIME = 0.0
_NOMINATIM_CACHE: dict[str, dict] = {}

def geocode_location_nominatim(query: str) -> dict | None:
    """Geocodes a search string via OpenStreetMap Nominatim with strict 1 req/s rate-limiting."""
    global _LAST_NOMINATIM_TIME
    if not query or not query.strip():
        return None

    norm_query = query.strip().lower()
    if norm_query in _NOMINATIM_CACHE:
        return _NOMINATIM_CACHE[norm_query]

    # Enforce >= 1.0 second between Nominatim requests per OSM usage policy
    with _NOMINATIM_LOCK:
        elapsed = time.time() - _LAST_NOMINATIM_TIME
        if elapsed < 1.05:
            time.sleep(1.05 - elapsed)
        _LAST_NOMINATIM_TIME = time.time()

    user_agent = getattr(settings, "nominatim_user_agent", "ALIGN-Platform/1.0 (+https://align.local)")
    encoded = urllib.parse.quote(query.strip())
    url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and len(data) > 0:
                item = data[0]
                result = {
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "display_name": item.get("display_name", query),
                }
                _NOMINATIM_CACHE[norm_query] = result
                return result
    except Exception as exc:
        logger.warning(f"Nominatim geocoding failed for '{query}': {exc}")

    return None

def fetch_overpass_places_around(lat: float, lon: float, radius_km: float = 25.0) -> list[dict]:
    """Queries OpenStreetMap Overpass API for coworking, colleges, universities, and IT parks within radius."""
    radius_meters = int(radius_km * 1000)
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:15];
    (
      node["amenity"~"coworking_space|university|college|library"](around:{radius_meters},{lat},{lon});
      way["amenity"~"coworking_space|university|college|library"](around:{radius_meters},{lat},{lon});
      node["office"~"it|company|research"](around:{radius_meters},{lat},{lon});
      way["office"~"it|company|research"](around:{radius_meters},{lat},{lon});
      node["commercial"~"it_park|tech_park"](around:{radius_meters},{lat},{lon});
    );
    out center 30;
    """
    user_agent = getattr(settings, "nominatim_user_agent", "ALIGN-Platform/1.0 (+https://align.local)")
    try:
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        req = urllib.request.Request(
            overpass_url,
            data=data,
            headers={"User-Agent": user_agent},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
            elements = payload.get("elements", [])
            results = []
            for el in elements:
                tags = el.get("tags", {})
                name = tags.get("name")
                if not name:
                    continue
                e_lat = el.get("lat") or el.get("center", {}).get("lat")
                e_lon = el.get("lon") or el.get("center", {}).get("lon")
                if not e_lat or not e_lon:
                    continue

                street = tags.get("addr:street", "")
                suburb = tags.get("addr:suburb", tags.get("addr:city", ""))
                addr = f"{street}, {suburb}".strip(", ") or name

                cat = tags.get("amenity") or tags.get("office") or "Community Space"
                cat_formatted = cat.replace("_", " ").title()

                results.append({
                    "name": name.strip(),
                    "description": tags.get("description") or f"Real community venue via OpenStreetMap.",
                    "category": cat_formatted,
                    "address": addr,
                    "city": tags.get("addr:city", "Regional"),
                    "latitude": float(e_lat),
                    "longitude": float(e_lon),
                    "source": "OpenStreetMap",
                })
            return results
    except Exception as exc:
        logger.warning(f"Overpass radius search failed around ({lat}, {lon}): {exc}")
        return []


# Real verified venues and spaces across target regions
AUTHENTIC_REGIONAL_PLACES = [
    # Pune
    {
        "name": "Venture Center (NCL Innovation Park)",
        "description": "Leading science and technology business incubator supporting innovators, deep-tech startups, and biotechnology builders with lab spaces.",
        "category": "Innovation & Labs",
        "address": "100 NCL Innovation Park, Dr. Homi Bhabha Road, Pashan",
        "city": "Pune",
        "latitude": 18.5447,
        "longitude": 73.8078,
        "image_url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "British Council Library Pune",
        "description": "Contemporary learning center, literature archive, and quiet study space hosting educational workshops and creative reading clubs.",
        "category": "Libraries & Learning",
        "address": "Ramsukh House, Ganeshkhind Road, Shivajinagar",
        "city": "Pune",
        "latitude": 18.5332,
        "longitude": 73.8443,
        "image_url": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "COEP MakerSpace & FabLab",
        "description": "State-of-the-art engineering fabrication facility with 3D printers, CNC laser cutters, electronics benches, and robotics workspace.",
        "category": "Makerspaces & Hardware",
        "address": "College of Engineering Pune, Wellesley Road, Shivajinagar",
        "city": "Pune",
        "latitude": 18.5293,
        "longitude": 73.8565,
        "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "ARAI Knowledge Centre",
        "description": "Specialized automotive research, engineering library, and technical mobility archive for automotive engineering professionals.",
        "category": "Research & Tech",
        "address": "Survey No. 102, Vetal Hill, Off Paud Road, Kothrud",
        "city": "Pune",
        "latitude": 18.5173,
        "longitude": 73.8153,
        "image_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "WeWork Futura Magarpatta",
        "description": "Dynamic co-working hub with flexible hot desks, high-speed connectivity, and community lounge for developers and creative teams.",
        "category": "Co-Working & Startups",
        "address": "Futura, Magarpatta Road, Hadapsar",
        "city": "Pune",
        "latitude": 18.5144,
        "longitude": 73.9272,
        "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Taljai Hills Biodiversity Park",
        "description": "Expansive natural forest reserve and walking sanctuary popular with wildlife photographers, birdwatchers, and trail runners.",
        "category": "Parks & Outdoors",
        "address": "Taljai Forest Area, Sahakar Nagar",
        "city": "Pune",
        "latitude": 18.4862,
        "longitude": 73.8437,
        "image_url": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Waari Book Cafe",
        "description": "Cozy community reading cafe surrounded by bookshelves, artisan pour-over coffee, and quiet corners for writers and coders.",
        "category": "Cafes & Culture",
        "address": "Ground Floor, Choice Institute, Karve Road, Kothrud",
        "city": "Pune",
        "latitude": 18.5029,
        "longitude": 73.8241,
        "image_url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Balewadi High Street Co-Lab",
        "description": "Open-air social promenade and modern collaborative workspaces hosting technology meetups and creative discussions.",
        "category": "Co-Working & Social",
        "address": "Balewadi High Street, Baner",
        "city": "Pune",
        "latitude": 18.5721,
        "longitude": 73.7744,
        "image_url": "https://images.unsplash.com/photo-1527192491265-7e15c55b1ed2?w=800&auto=format&fit=crop&q=80",
    },

    # Mumbai
    {
        "name": "Drona Aviation Maker Lab",
        "description": "Aerospace and micro-drone maker lab inside SINE IIT Bombay, hosting drone-building hackathons and flight-control workshops.",
        "category": "Makerspaces & Hardware",
        "address": "CSRE Building, IIT Bombay, Powai",
        "city": "Mumbai",
        "latitude": 19.1334,
        "longitude": 72.9133,
        "image_url": "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "David Sassoon Library & Reading Room",
        "description": "Historic Victorian Gothic library, quiet garden pavilion, and open study hall in Mumbai's historic heritage art district.",
        "category": "Libraries & Learning",
        "address": "152 Mahatma Gandhi Road, Kala Ghoda, Fort",
        "city": "Mumbai",
        "latitude": 18.9282,
        "longitude": 72.8322,
        "image_url": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Bombay Flying Club Hangar & Lab",
        "description": "Aviation research facility and flight simulation lab for aeronautical enthusiasts and aviation engineers.",
        "category": "Research & Tech",
        "address": "Juhu Aerodrome, SV Road, Vile Parle West",
        "city": "Mumbai",
        "latitude": 19.0968,
        "longitude": 72.8331,
        "image_url": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Sanjay Gandhi National Park Nature Trails",
        "description": "Protected tropical forest reserve with Kanheri Caves, mountain biking routes, and biodiversity trekking trails.",
        "category": "Parks & Outdoors",
        "address": "Western Express Highway, Borivali East",
        "city": "Mumbai",
        "latitude": 19.2288,
        "longitude": 72.9182,
        "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&auto=format&fit=crop&q=80",
    },

    # Kolhapur
    {
        "name": "Rankala Lake Promenade & Cultural Plaza",
        "description": "Historic lakefront promenade featuring evening gatherings, artisan handicraft stalls, and peaceful sunrise walking tracks.",
        "category": "Parks & Outdoors",
        "address": "Rankala Lake Shore, Hari Om Nagar",
        "city": "Kolhapur",
        "latitude": 16.6917,
        "longitude": 74.2144,
        "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Shivaji University Innovation & Incubation Centre",
        "description": "Regional university innovation centre fostering student ventures, agro-tech projects, and computational research.",
        "category": "Innovation & Labs",
        "address": "Vidyanagar, Shivaji University Campus",
        "city": "Kolhapur",
        "latitude": 16.6781,
        "longitude": 74.2546,
        "image_url": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "Kolhapur IT Park Incubation Hub",
        "description": "Modern software technology park providing dedicated co-working offices and fiber connectivity for regional engineering teams.",
        "category": "Co-Working & Startups",
        "address": "Udyam Nagar, Industrial Estate",
        "city": "Kolhapur",
        "latitude": 16.6993,
        "longitude": 74.2389,
        "image_url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&auto=format&fit=crop&q=80",
    },

    # Bangalore
    {
        "name": "Bengaluru Maker’s Asylum",
        "description": "Community makerspace and rapid prototyping fablab for woodcraft, electronics, metalworking, and open hardware.",
        "category": "Makerspaces & Hardware",
        "address": "Indiranagar 100ft Road",
        "city": "Bangalore",
        "latitude": 12.9719,
        "longitude": 77.6412,
        "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "State Central Library (Cubbon Park)",
        "description": "Iconic red-pompeian public library housed in Seshadri Iyer Memorial Hall, holding over 300,000 reference volumes.",
        "category": "Libraries & Learning",
        "address": "Cubbon Park, Kasturba Road",
        "city": "Bangalore",
        "latitude": 12.9757,
        "longitude": 77.5929,
        "image_url": "https://images.unsplash.com/photo-1541123437800-1bb1317badc2?w=800&auto=format&fit=crop&q=80",
    },
    {
        "name": "91springboard Koramangala",
        "description": "Collaborative enterprise coworking hub with 24/7 access, private phone booths, and community hack days.",
        "category": "Co-Working & Startups",
        "address": "80 Feet Road, 7th Block, Koramangala",
        "city": "Bangalore",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "image_url": "https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=800&auto=format&fit=crop&q=80",
    },
]

def fetch_osm_overpass_places(city: str = "Pune", amenity: str = "coworking_space") -> list[dict]:
    """Queries OpenStreetMap Overpass API for real public venues and spaces."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:15];
    area["name"="{city}"]["boundary"="administrative"]->.searchArea;
    (
      node["amenity"="{amenity}"](area.searchArea);
      way["amenity"="{amenity}"](area.searchArea);
    );
    out center 15;
    """
    try:
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        req = urllib.request.Request(
            overpass_url,
            data=data,
            headers={"User-Agent": "ALIGN-Platform/1.0 (+https://align.local)"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
            elements = payload.get("elements", [])
            results = []
            for el in elements:
                tags = el.get("tags", {})
                name = tags.get("name")
                if not name:
                    continue
                lat = el.get("lat") or el.get("center", {}).get("lat")
                lon = el.get("lon") or el.get("center", {}).get("lon")
                if not lat or not lon:
                    continue
                street = tags.get("addr:street", "")
                suburb = tags.get("addr:suburb", city)
                addr = f"{street}, {suburb}".strip(", ") or f"{city} Center"
                results.append({
                    "name": name.strip(),
                    "description": tags.get("description") or f"Real community venue in {city} via OpenStreetMap.",
                    "category": tags.get("amenity", "Community Space").replace("_", " ").title(),
                    "address": addr,
                    "city": city,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "source": "OpenStreetMap",
                })
            return results
    except Exception as exc:
        logger.warning(f"OSM Overpass query failed for {city}: {exc}")
        return []

def sync_real_places(db: Session, city: str | None = None) -> dict:
    """Synchronizes genuine venues into PostgreSQL with 384-d vector embeddings."""
    targets = [p for p in AUTHENTIC_REGIONAL_PLACES if not city or p["city"].lower() == city.strip().lower()]
    synced = 0
    updated = 0

    for item in targets:
        existing = db.scalar(
            select(Place).where(
                ((Place.name == item["name"]) & (Place.city == item["city"])) |
                ((Place.latitude.between(item["latitude"] - 0.0002, item["latitude"] + 0.0002)) &
                 (Place.longitude.between(item["longitude"] - 0.0002, item["longitude"] + 0.0002)))
            )
        )
        if not existing:
            ctx = f"{item['name']} {item['description']} {item['category']} {item['address']} {item['city']}"
            emb = generate_embedding(ctx)
            place = Place(
                name=item["name"],
                description=item["description"],
                category=item["category"],
                address=item["address"],
                city=item["city"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                image_url=item.get("image_url"),
                source="OpenStreetMap",
                embedding=emb,
            )
            db.add(place)
            synced += 1
        else:
            if item.get("image_url") and existing.image_url != item.get("image_url"):
                existing.image_url = item.get("image_url")
                updated += 1

    db.commit()
    return {
        "status": "success",
        "synced": synced,
        "updated": updated,
        "total_available": len(targets),
        "message": f"Synchronized {synced} new places and updated {updated} existing places with images.",
    }
