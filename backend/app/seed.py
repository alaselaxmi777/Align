from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.community import Community, CommunityMembership
from app.models.event import Event, EventRegistration
from app.models.place import Place
from app.models.user import User, Profile
from app.core.security import hash_password
from app.services.embeddings import generate_embedding
from app.services.eventbrite import sync_eventbrite_events

COMMUNITIES = [
    {
        "name": "AI Explorers Circle",
        "description": "A welcoming community for students and curious builders learning machine learning, generative AI, LLMs, and practical AI projects together.",
        "category": "Technology",
        "tags": "AI, machine learning, Python, PyTorch, generative AI, students, projects",
        "location": "Online",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Weekend Trail & Outdoor Club",
        "description": "Meet people who enjoy beginner-friendly hikes, outdoor photography, nature walks, trail runs, and weekend adventures.",
        "category": "Outdoors",
        "tags": "hiking, photography, nature, weekends, fitness, outdoors",
        "location": "Pune",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "image_url": "https://images.unsplash.com/photo-1551632811-561732d1e306?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Product Design & UX Studio",
        "description": "A peer group for UI/UX designers, students, and beginners to share case studies, critique design thinking, and master Figma.",
        "category": "Design",
        "tags": "UX, UI, product design, Figma, portfolio, prototyping",
        "location": "Online",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "image_url": "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Women in Tech Connect",
        "description": "A supportive network for women in software engineering and data science to share career advice, collaborate on code, and find mentors.",
        "category": "Career",
        "tags": "women in tech, mentorship, coding, career, networking, data science",
        "location": "Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "image_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Creative Indie Makers Collective",
        "description": "A circle for creative people who love illustration, mechanical keyboards, generative art, and building indie apps.",
        "category": "Arts",
        "tags": "art, illustration, crafts, creativity, side projects, design",
        "location": "Bangalore",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "image_url": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=1200&auto=format&fit=crop&q=80",
    },
]

# Note: Real-time events are pulled dynamically from Eventbrite API (no hardcoded fake events).

PLACES = [
    {
        "name": "Viman Nagar Tech Hub & Co-working",
        "description": "Collaborative space with high-speed internet, conference pods, and frequent tech meetups.",
        "category": "Co-working",
        "address": "Phoenix Marketcity Road, Viman Nagar",
        "city": "Pune",
        "latitude": 18.5679,
        "longitude": 73.9143,
    },
    {
        "name": "ARAI Hills Nature Trailhead",
        "description": "Popular urban nature trail for morning walks, bird photography, and relaxed outdoor meetups.",
        "category": "Outdoors",
        "address": "Paud Road, Kothrud",
        "city": "Pune",
        "latitude": 18.5158,
        "longitude": 73.8173,
    },
    {
        "name": "Bandra Design & Art Café",
        "description": "Cozy café with community art exhibitions, indie design meetups, and quiet work tables.",
        "category": "Café",
        "address": "Pali Hill, Bandra West",
        "city": "Mumbai",
        "latitude": 19.0607,
        "longitude": 72.8258,
    },
]

import sys
import os
from app.core.config import settings

def main():
    if os.getenv("ENVIRONMENT", "").lower() == "production" or getattr(settings, "environment", "").lower() == "production":
        raise RuntimeError("ABORTED: Seeding synthetic or dev data is strictly forbidden in production environments.")

    if "--dev-seed" not in sys.argv and os.getenv("DEV_SEED", "").lower() != "true":
        print(
            "SAFETY NOTICE: ALIGN operates as a real, data-driven platform. "
            "Demo seeding is disabled by default to prevent contaminating genuine databases. "
            "To explicitly seed developmental test records, run with: python -m app.seed --dev-seed"
        )
        return

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Create Dev Test User if not exists (clearly tagged is_test=True)
        demo_email = "dev_seed@align.local"
        user = db.scalar(select(User).where(User.email == demo_email))
        if not user:
            user = User(
                name="Dev Seed User",
                email=demo_email,
                password_hash=hash_password("AlignDev2026!"),
                is_active=True,
                is_verified=True,
                is_test=True,
            )
            db.add(user)
            db.flush()
            profile = Profile(
                user_id=user.id,
                bio="Developmental test user profile for local verification.",
                location="Pune",
                latitude=18.5204,
                longitude=73.8567,
                interests="Artificial Intelligence, Machine Learning, Hiking, Photography",
                skills="Python, FastAPI, PyTorch, React",
                goals="Build production AI systems, connect with machine learning study groups",
                preferred_activities="Workshops, weekend hikes, hackathons",
                preferred_community_types="Technology, Outdoors, Design",
                onboarding_completed=True,
            )
            ctx = f"{profile.bio} {profile.interests} {profile.skills} {profile.goals}"
            profile.embedding = generate_embedding(ctx)
            db.add(profile)
            db.flush()

        # Seed Communities (tagged is_test=True)
        for payload in COMMUNITIES:
            existing = db.scalar(select(Community).where(Community.name == payload["name"]))
            if not existing:
                ctx = f"{payload['name']} {payload['description']} {payload['category']} {payload['tags']} {payload['location']}"
                item = Community(
                    **payload,
                    created_by_id=user.id,
                    is_test=True,
                    embedding=generate_embedding(ctx),
                )
                db.add(item)
                db.flush()
                # Creator membership
                db.add(CommunityMembership(user_id=user.id, community_id=item.id, role="admin", status="active"))

        # Seed Real-Time Events from Eventbrite (purges any old dummy events)
        sync_res = sync_eventbrite_events(db, query="all", location="", purge_dummy=True)
        print(f"Eventbrite Sync: {sync_res.get('message')}")

        # Seed Places
        for payload in PLACES:
            existing = db.scalar(select(Place).where(Place.name == payload["name"]))
            if not existing:
                ctx = f"{payload['name']} {payload['description']} {payload['category']} {payload['city']}"
                place = Place(
                    **payload,
                    embedding=generate_embedding(ctx),
                )
                db.add(place)

        db.commit()
    print("ALIGN database seeded with demo user, communities, events, places, and vector embeddings.")

if __name__ == "__main__":
    main()
