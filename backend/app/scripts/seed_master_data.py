import sys
import os
import logging
from datetime import datetime, timezone
import openpyxl
from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.core.security import hash_password
from app.models.dataset import (
    SkillsHobbiesDataset,
    SkillMaster,
    HobbyMaster,
    GoalsInterestsDataset,
    GoalMaster,
    InterestMaster,
    DatasetMetadata,
)
from app.models.community import Community
from app.models.place import Place
from app.models.user import User, Profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_master_data")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_XLSX = os.path.join(BACKEND_DIR, "skills_and_hobbies_5000_records.xlsx")
GOALS_XLSX = os.path.join(BACKEND_DIR, "goals_and_interests_10000_records.xlsx")


def seed_skills_and_hobbies(db: Session):
    logger.info("Checking Skills & Hobbies dataset from %s...", SKILLS_XLSX)
    if not os.path.exists(SKILLS_XLSX):
        logger.error("File not found: %s", SKILLS_XLSX)
        return

    wb = openpyxl.load_workbook(SKILLS_XLSX, read_only=True)

    # 1. Skill Master
    if "Skill Master" in wb.sheetnames:
        ws = wb["Skill Master"]
        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            cat, stype, desc = str(row[0] or "").strip(), str(row[1] or "").strip(), str(row[2] or "").strip()
            existing = db.scalar(select(SkillMaster).where(SkillMaster.type == stype))
            if not existing:
                db.add(SkillMaster(category=cat, type=stype, description=desc))
                count += 1
        db.commit()
        logger.info("SkillMaster: seeded %d new records (Total: %d)", count, db.scalar(select(func.count(SkillMaster.id))))

    # 2. Hobby Master
    if "Hobby Master" in wb.sheetnames:
        ws = wb["Hobby Master"]
        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            cat, htype, desc = str(row[0] or "").strip(), str(row[1] or "").strip(), str(row[2] or "").strip()
            existing = db.scalar(select(HobbyMaster).where(HobbyMaster.type == htype))
            if not existing:
                db.add(HobbyMaster(category=cat, type=htype, description=desc))
                count += 1
        db.commit()
        logger.info("HobbyMaster: seeded %d new records (Total: %d)", count, db.scalar(select(func.count(HobbyMaster.id))))

    # 3. 5000 Records
    current_count = db.scalar(select(func.count(SkillsHobbiesDataset.id))) or 0
    if current_count >= 5000:
        logger.info("SkillsHobbiesDataset already populated (%d records). Skipping.", current_count)
    else:
        logger.info("Loading 5000 records into SkillsHobbiesDataset...")
        ws = wb["5000 Records"]
        batch = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            item = {
                "record_id": str(row[0]).strip(),
                "record_type": str(row[1] or "Skill").strip(),
                "category": str(row[2] or "").strip(),
                "type": str(row[3] or "").strip(),
                "description": str(row[4] or "").strip(),
                "application_context": str(row[5] or "").strip(),
                "proficiency_engagement_level": str(row[6] or "").strip(),
                "setting": str(row[7] or "").strip(),
                "frequency": str(row[8] or "") if row[8] is not None else None,
                "primary_motivation": str(row[9] or "") if row[9] is not None else None,
                "popularity_score": int(row[10] or 5),
                "expanded_record_description": str(row[11] or "").strip(),
            }
            batch.append(item)
            if len(batch) >= 1000:
                stmt = pg_insert(SkillsHobbiesDataset).values(batch).on_conflict_do_nothing(index_elements=["record_id"])
                db.execute(stmt)
                db.commit()
                batch = []
        if batch:
            stmt = pg_insert(SkillsHobbiesDataset).values(batch).on_conflict_do_nothing(index_elements=["record_id"])
            db.execute(stmt)
            db.commit()
        logger.info("SkillsHobbiesDataset loaded. Total: %d", db.scalar(select(func.count(SkillsHobbiesDataset.id))))


def seed_goals_and_interests(db: Session):
    logger.info("Checking Goals & Interests dataset from %s...", GOALS_XLSX)
    if not os.path.exists(GOALS_XLSX):
        logger.error("File not found: %s", GOALS_XLSX)
        return

    wb = openpyxl.load_workbook(GOALS_XLSX, read_only=True)

    # 1. Goal Master
    if "Goal Master" in wb.sheetnames:
        ws = wb["Goal Master"]
        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            cat, gtype, desc = str(row[0] or "").strip(), str(row[1] or "").strip(), str(row[2] or "").strip()
            existing = db.scalar(select(GoalMaster).where(GoalMaster.type == gtype))
            if not existing:
                db.add(GoalMaster(category=cat, type=gtype, description=desc))
                count += 1
        db.commit()
        logger.info("GoalMaster: seeded %d new records (Total: %d)", count, db.scalar(select(func.count(GoalMaster.id))))

    # 2. Interest Master
    if "Interest Master" in wb.sheetnames:
        ws = wb["Interest Master"]
        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[1]:
                continue
            cat, itype, desc = str(row[0] or "").strip(), str(row[1] or "").strip(), str(row[2] or "").strip()
            existing = db.scalar(select(InterestMaster).where(InterestMaster.type == itype))
            if not existing:
                db.add(InterestMaster(category=cat, type=itype, description=desc))
                count += 1
        db.commit()
        logger.info("InterestMaster: seeded %d new records (Total: %d)", count, db.scalar(select(func.count(InterestMaster.id))))

    # 3. 10000 Records
    current_count = db.scalar(select(func.count(GoalsInterestsDataset.id))) or 0
    if current_count >= 10000:
        logger.info("GoalsInterestsDataset already populated (%d records). Skipping.", current_count)
    else:
        logger.info("Loading 10000 records into GoalsInterestsDataset...")
        ws = wb["10000 Records"]
        batch = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            item = {
                "record_id": str(row[0]).strip(),
                "record_type": str(row[1] or "Goal").strip(),
                "category": str(row[2] or "").strip(),
                "type": str(row[3] or "").strip(),
                "description": str(row[4] or "").strip(),
                "life_context": str(row[5] or "") if row[5] is not None else None,
                "timeline_engagement_level": str(row[6] or "") if row[6] is not None else None,
                "priority_setting": str(row[7] or "") if row[7] is not None else None,
                "status_frequency": str(row[8] or "") if row[8] is not None else None,
                "primary_motivation": str(row[9] or "") if row[9] is not None else None,
                "popularity_score": int(row[10] or 5),
                "expanded_record_description": str(row[11] or "").strip(),
            }
            batch.append(item)
            if len(batch) >= 1000:
                stmt = pg_insert(GoalsInterestsDataset).values(batch).on_conflict_do_nothing(index_elements=["record_id"])
                db.execute(stmt)
                db.commit()
                batch = []
        if batch:
            stmt = pg_insert(GoalsInterestsDataset).values(batch).on_conflict_do_nothing(index_elements=["record_id"])
            db.execute(stmt)
            db.commit()
        logger.info("GoalsInterestsDataset loaded. Total: %d", db.scalar(select(func.count(GoalsInterestsDataset.id))))


def seed_metadata(db: Session):
    meta_records = [
        {
            "dataset_name": "Goals & Interests Dataset",
            "version": "v1.0",
            "source_filename": "goals_and_interests_10000_records.xlsx",
            "total_records": 10000,
            "record_types": "Goal, Interest",
            "status": "ready",
            "notes": "10,000 empirical goal and interest taxonomy records across 20 distinct life categories.",
        },
        {
            "dataset_name": "Skills & Hobbies Dataset",
            "version": "v1.0",
            "source_filename": "skills_and_hobbies_5000_records.xlsx",
            "total_records": 5000,
            "record_types": "Skill, Hobby",
            "status": "ready",
            "notes": "5,000 structured skill and hobby profile taxonomy records with proficiency scores.",
        },
    ]
    for m in meta_records:
        existing = db.scalar(select(DatasetMetadata).where(DatasetMetadata.dataset_name == m["dataset_name"]))
        if not existing:
            db.add(DatasetMetadata(**m))
    db.commit()
    logger.info("DatasetMetadata verified.")


COMMUNITIES_SEED = [
    {
        "name": "AI & Generative Systems Hub",
        "description": "Engineers, researchers, and builders collaborating on LLMs, agentic workflows, PyTorch, and generative architectures.",
        "category": "Technology",
        "tags": "AI, LLMs, Machine Learning, Python, PyTorch, Generative AI",
        "location": "Bengaluru",
        "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Weekend Trail & Mountain Trekkers",
        "description": "Trail runners, peak hikers, landscape photographers, and outdoor nature enthusiasts discovering pristine summits.",
        "category": "Outdoors",
        "tags": "Hiking, Trekking, Photography, Nature, Fitness, Outdoors",
        "location": "Pune",
        "image_url": "https://images.unsplash.com/photo-1551632811-561732d1e306?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Product Design & Design Systems Lab",
        "description": "UI/UX architects, design theorists, and Figma creators critiquing micro-interactions, typography, and UX research.",
        "category": "Design",
        "tags": "UI/UX, Figma, Design Systems, Prototyping, User Research",
        "location": "Mumbai",
        "image_url": "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Indie Hackers & Solo Founders Guild",
        "description": "Founders bootstrapping SaaS, developer tools, and micro-apps from zero to ramen profitability and beyond.",
        "category": "Business",
        "tags": "SaaS, Startups, Indie Hacker, Product, Growth, Marketing",
        "location": "Bengaluru",
        "image_url": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Specialty Coffee & Espresso Craft",
        "description": "Baristas, home roasters, and bean geeks calibrating pour-overs, water chemistry, and lever machines.",
        "category": "Culinary",
        "tags": "Coffee, Espresso, Roasting, Aeropress, Latte Art",
        "location": "Mumbai",
        "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Bouldering & High-Angle Climbing",
        "description": "Indoor gym boulderers and outdoor crag senders working dynamic heel hooks, slab balance, and finger power.",
        "category": "Fitness",
        "tags": "Bouldering, Climbing, Fitness, Movement, Calisthenics",
        "location": "Pune",
        "image_url": "https://images.unsplash.com/photo-1522163182402-834f871fd851?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Analog Synthesizers & Modular Audio",
        "description": "Sound designers, Eurorack modular patchers, and ambient composers crafting hardware electronic tracks.",
        "category": "Music",
        "tags": "Synthesizers, Modular, Eurorack, Sound Design, Production",
        "location": "Delhi",
        "image_url": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=1200&auto=format&fit=crop&q=80",
    },
    {
        "name": "Open Source Systems & Rustacean Collective",
        "description": "Systems programmers writing memory-safe kernels, distributed databases, high-throughput engines in Rust and Go.",
        "category": "Technology",
        "tags": "Rust, Systems Programming, Go, WebAssembly, Performance",
        "location": "Hyderabad",
        "image_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80",
    },
]

PLACES_SEED = [
    {
        "name": "The Highline Co-working & Roastworks",
        "description": "A premier quiet workspace featuring artisanal filter coffee, ergonomic standing desks, and private phone booths.",
        "category": "Co-working",
        "address": "12th Main Road, Indiranagar",
        "city": "Bengaluru",
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "name": "Koregaon Boulder & Movement Studio",
        "description": "Specialty climbing gym with 600 sqm of textured wall surfaces, campus rungs, and calisthenics rigs.",
        "category": "Sports",
        "address": "Lane 5, Koregaon Park",
        "city": "Pune",
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "name": "Bandra Artisan Bakery & Bookshop",
        "description": "Cozy independent bookstore offering heritage espresso, sourdough croissants, and quiet reading alcoves.",
        "category": "Cafe",
        "address": "Perry Cross Road, Bandra West",
        "city": "Mumbai",
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "name": "Cyber Towers Open Innovation Lab",
        "description": "Collaborative prototyping studio with fast fiber internet, 3D printers, and whiteboards.",
        "category": "Co-working",
        "address": "Hitec City",
        "city": "Hyderabad",
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "name": "Hauz Khas Creative Common",
        "description": "Sunlit cafe and communal workshop hosting film screenings, poetry readings, and design circles.",
        "category": "Arts",
        "address": "Hauz Khas Village",
        "city": "Delhi",
        "latitude": 0.0,
        "longitude": 0.0,
    },
]


def seed_communities_and_places(db: Session):
    for c in COMMUNITIES_SEED:
        existing = db.scalar(select(Community).where(Community.name == c["name"]))
        if not existing:
            db.add(Community(**c))
    for p in PLACES_SEED:
        existing = db.scalar(select(Place).where(Place.name == p["name"]))
        if not existing:
            db.add(Place(**p))
    db.commit()
    logger.info("Communities & Places verified. Total communities: %d, Total places: %d",
                db.scalar(select(func.count(Community.id))),
                db.scalar(select(func.count(Place.id))))


DEMO_USERS = [
    ("Aarav Sharma", "aarav_ai", "aarav.ai@demo.align.local", "Bengaluru", "AI researcher building autonomous agent frameworks.", "Python, Machine Learning, PyTorch, Deep Learning", "Chess Strategy, Digital Photography", "Autonomous AI Agents, Open Source LLMs", "Transition into AI/ML, Build Open Source Projects"),
    ("Priya Nair", "priya_design", "priya.design@demo.align.local", "Mumbai", "Senior UI/UX architect crafting accessible design systems.", "UI/UX Design, Figma, User Research, Design Systems", "Specialty Coffee Brewing, Ceramic & Pottery", "Minimalist UI/UX, Typography & Lettering", "Scale Freelance Business, Launch an Indie App or Product"),
    ("Rohan Kulkarni", "rohan_runs", "rohan.runs@demo.align.local", "Pune", "Marathon enthusiast and backend systems engineer.", "Go, Distributed Systems, Docker, Kubernetes", "Trail Hiking, Distance Running, Sourdough Bread Baking", "Calisthenics & Bodyweight Training, Space Exploration & Astrophysics", "Train for a Half Marathon, Master Distributed Systems"),
    ("Ananya Sen", "ananya_dev", "ananya.dev@demo.align.local", "Delhi", "Full stack developer interested in web accessibility and rust.", "TypeScript, React, Rust, Next.js", "Film Photography, Tabletop Role-Playing Games", "Developer Ergonomics & Tooling, Sci-Fi Literature", "Land First Software Role, Read 24 Books a Year"),
    ("Vikram Deshmukh", "vikram_builds", "vikram.builds@demo.align.local", "Pune", "Indie hacker bootstrapping developer productivity utilities.", "Python, FastAPI, React, PostgreSQL", "Bouldering & Rock Climbing, Retro Arcade Gaming", "Civic Hacking & Open Data, Open Source LLMs", "Launch an Indie App or Product, Find a Tech Co-Founder"),
    ("Sneha Patel", "sneha_data", "sneha.data@demo.align.local", "Bengaluru", "Data engineer building real-time event streaming pipelines.", "Apache Spark, SQL & Relational Databases, Pandas & NumPy", "Specialty Coffee Brewing, Indoor Plant Care", "Cognitive Science & Neuroscience, Biotechnology & Longevity", "Acquire Cloud Architecture Certification, Practice Daily Mindfulness Meditation"),
    ("Kabir Joshi", "kabir_audio", "kabir.audio@demo.align.local", "Mumbai", "Modular synthesizer sound artist and music producer.", "Creative Storytelling, Technical Writing", "Music Production, Acoustic Guitar, Vinyl Records", "Electronic Synthesizers & Modular Audio, Film Scores & Orchestral Music", "Record an EP or Music Album, Build a Local Meetup Community"),
    ("Meera Reddy", "meera_climbs", "meera.climbs@demo.align.local", "Hyderabad", "Bouldering enthusiast and cybersecurity consultant.", "Network Security, Penetration Testing, Application Security", "Bouldering & Rock Climbing, Yoga & Mindfulness", "Brazilian Jiu-Jitsu & Martial Arts, Wilderness Conservation", "Establish Consistent Workout Habit, Public Speaking & Thought Leadership"),
    ("Aditya Varma", "aditya_cloud", "aditya.cloud@demo.align.local", "Bengaluru", "Cloud solutions architect optimizing multi-region kubernetes clusters.", "Amazon Web Services (AWS), Terraform, Kubernetes, DevOps", "Road Cycling, Specialty Coffee Brewing", "Renewable Energy & Climate Tech, High-Performance Cycling", "Acquire Cloud Architecture Certification, Prepare for System Design Interviews"),
    ("Kavya Iyer", "kavya_story", "kavya.story@demo.align.local", "Chennai", "Product marketing specialist and fiction author.", "Content Strategy, Digital Marketing, Copywriting", "Creative Writing, Podcasting, Tea Brewing & Appreciation", "Cinematography & Lighting, Independent Cinema & Arthouse", "Publish a Weekly Newsletter, Read 24 Books a Year"),
    ("Ishaan Mehta", "ishaan_robot", "ishaan.robot@demo.align.local", "Pune", "Robotics engineer exploring embedded microcontrollers and ROS.", "Robotics, Embedded Systems, C++, Linux System Administration", "3D Printing & CAD, Amateur Astronomy", "Edge Computing & IoT, Space Exploration & Astrophysics", "Build Open Source Projects, Master Distributed Systems"),
    ("Tanvi Saxena", "tanvi_art", "tanvi.art@demo.align.local", "Delhi", "Visual designer and creative coder experimenting with WebGL.", "Figma, UI/UX Design, Rapid Prototyping", "Digital Art & Illustration, Painting", "Generative Art & Shaders, Minimalist UI/UX", "Launch an Indie App or Product, Scale Freelance Business"),
    ("Nikhil Bhat", "nikhil_code", "nikhil.code@demo.align.local", "Bengaluru", "Backend developer interested in database query optimization.", "SQL & Relational Databases, Java, REST API Design", "Speedcubing, Chess Strategy", "Developer Ergonomics & Tooling, Autonomous AI Agents", "Prepare for System Design Interviews, Land First Software Role"),
    ("Divya Menon", "divya_yoga", "divya.yoga@demo.align.local", "Kochi", "Wellness coach and frontend engineer practicing mindful living.", "React, TypeScript, CSS & Responsive Design", "Yoga & Mindfulness, Tea Brewing & Appreciation", "Functional Mobility & Movement, Mental Health Advocacy", "Practice Daily Mindfulness Meditation, Improve Sleep Consistency"),
    ("Arjun Kapoor", "arjun_venture", "arjun.venture@demo.align.local", "Mumbai", "Fintech product manager analyzing early-stage consumer models.", "Financial Modeling, Startup Fundraising, Product Management", "Mixology & Craft Mocktails, Road Cycling", "Web3 & Decentralized Protocols, Urban Sustainability", "Find a Tech Co-Founder, Public Speaking & Thought Leadership"),
    ("Pooja Hegde", "pooja_ml", "pooja.ml@demo.align.local", "Hyderabad", "NLP practitioner fine-tuning transformer models for multilingual tasks.", "Natural Language Processing, PyTorch, LLM Fine-Tuning", "Film Photography, Podcasting", "Open Source LLMs, Tech Education for Underrepresented Groups", "Transition into AI/ML, Publish a Weekly Newsletter"),
    ("Siddharth Rao", "sid_hikes", "sid.hikes@demo.align.local", "Pune", "DevOps engineer who spends weekends in the Western Ghats.", "CI/CD Pipelines, Docker, Linux System Administration", "Trail Hiking, Digital Photography", "Wilderness Conservation, High-Performance Cycling", "Train for a Half Marathon, Establish Consistent Workout Habit"),
    ("Neha Gupta", "neha_growth", "neha.growth@demo.align.local", "Delhi", "Performance growth marketer scaling organic acquisition channels.", "Performance Marketing, Search Engine Optimization (SEO), Data Analysis", "Urban Skateboarding, Specialty Coffee Brewing", "Ethical AI & Algorithmic Fairness, Civic Hacking & Open Data", "Scale Freelance Business, Cook Healthy Whole-Food Meals"),
    ("Gaurav Singhal", "gaurav_sec", "gaurav.sec@demo.align.local", "Bengaluru", "Application security researcher hunting zero-day logic flaws.", "Application Security, Penetration Testing, Cryptography", "Competitive Esports, Tabletop Role-Playing Games", "Developer Ergonomics & Tooling, Web3 & Decentralized Protocols", "Master Distributed Systems, Public Speaking & Thought Leadership"),
    ("Tara Chawla", "tara_film", "tara.film@demo.align.local", "Mumbai", "Documentary filmmaker and editor capturing urban culture.", "Videography & Video Editing, Creative Storytelling", "Film Photography, Mixology & Craft Mocktails", "Cinematography & Lighting, Independent Cinema & Arthouse", "Record an EP or Music Album, Publish a Weekly Newsletter"),
    ("Rahul Nambiar", "rahul_oss", "rahul.oss@demo.align.local", "Chennai", "Open-source contributor working on modern terminal tools.", "Rust, Go, Linux System Administration", "Mechanical Keyboards, Amateur Astronomy", "Developer Ergonomics & Tooling, Autonomous AI Agents", "Build Open Source Projects, Land First Software Role"),
    ("Shreya Bannerjee", "shreya_bio", "shreya.bio@demo.align.local", "Kolkata", "Computational biology researcher studying genomic sequencing.", "Python, Data Analysis, Pandas & NumPy", "Acoustic Guitar, Painting", "Biotechnology & Longevity, Cognitive Science & Neuroscience", "Read 24 Books a Year, Practice Daily Mindfulness Meditation"),
    ("Varun Pillai", "varun_mobile", "varun.mobile@demo.align.local", "Bengaluru", "Cross-platform mobile developer building smooth offline-first apps.", "Flutter, React Native, Mobile Development", "Trail Hiking, Bouldering & Rock Climbing", "Minimalist UI/UX, Edge Computing & IoT", "Launch an Indie App or Product, Establish Consistent Workout Habit"),
    ("Ananya Roy", "ananya_product", "ananya.product@demo.align.local", "Pune", "Technical product manager aligning user research with roadmap execution.", "Product Management, Agile & Scrum, User Research", "Ceramic & Pottery, Sourdough Bread Baking", "Urban Sustainability & Community Gardens, Mental Health Advocacy", "Find a Tech Co-Founder, Cook Healthy Whole-Food Meals"),
    ("Karan Malhotra", "karan_data", "karan.data@demo.align.local", "Mumbai", "Business intelligence analyst converting raw streams into actionable metrics.", "Business Intelligence, Data Visualization, SQL & Relational Databases", "Distance Running, Board Game Design", "Civic Hacking & Open Data, High-Performance Cycling", "Train for a Half Marathon, Prepare for System Design Interviews"),
    ("Rhea Dsouza", "rhea_brand", "rhea.brand@demo.align.local", "Goa", "Brand strategist crafting memorable identities for sustainable brands.", "Design Systems, Copywriting, Creative Storytelling", "Specialty Coffee Brewing, Surfing", "Architecture & Spatial Design, Typography & Lettering", "Scale Freelance Business, Build a Local Meetup Community"),
    ("Manish Tiwari", "manish_devops", "manish.devops@demo.align.local", "Noida", "Site reliability engineer keeping distributed microservices resilient.", "Terraform, Kubernetes, Amazon Web Services (AWS), DevOps", "Home Automation & Homelab, Speedcubing", "Edge Computing & IoT, Space Exploration & Astrophysics", "Acquire Cloud Architecture Certification, Improve Sleep Consistency"),
    ("Simran Gill", "simran_write", "simran.write@demo.align.local", "Chandigarh", "Technical writer documenting developer SDKs and REST APIs.", "Technical Writing, REST API Design, Copywriting", "Creative Writing, Podcasting", "Developer Ergonomics & Tooling, Tech Education for Underrepresented Groups", "Publish a Weekly Newsletter, Read 24 Books a Year"),
    ("Dhruv Sen", "dhruv_frontend", "dhruv.frontend@demo.align.local", "Hyderabad", "Frontend performance specialist obsessed with 60fps animations.", "TypeScript, React, Next.js, UI/UX Design", "Digital Photography, Retro Arcade Gaming", "Minimalist UI/UX, Generative Art & Shaders", "Launch an Indie App or Product, Land First Software Role"),
    ("Alisha Merchant", "alisha_fin", "alisha.fin@demo.align.local", "Mumbai", "Quantitative researcher modeling market dynamics and risk profiles.", "Financial Modeling, Data Analysis, Python", "Chess Strategy, Yoga & Mindfulness", "Cognitive Science & Neuroscience, Ethical AI & Algorithmic Fairness", "Find a Tech Co-Founder, Master Distributed Systems"),
]


def seed_demo_users(db: Session):
    logger.info("Checking demo users...")
    demo_pw = hash_password("DemoPassword123!")
    count = 0
    for name, uname, email, city, bio, skills, hobbies, interests, goals in DEMO_USERS:
        existing = db.scalar(select(User).where(User.email == email))
        if not existing:
            user = User(
                name=name,
                username=uname,
                email=email,
                password_hash=demo_pw,
                is_active=True,
                is_verified=True,
                is_test=False,
                role="user",
            )
            db.add(user)
            db.flush()
            profile = Profile(
                user_id=user.id,
                bio=bio,
                location=city,
                latitude=None,      # Coarse city level only: no raw coordinates
                longitude=None,
                privacy_level="public",
                location_privacy="approximate",
                skills=skills,
                hobbies=hobbies,
                interests=interests,
                goals=goals,
                onboarding_completed=True,
                onboarding_step=3,
            )
            db.add(profile)
            count += 1
    db.commit()
    logger.info("Demo users seeded: %d new accounts (Total users: %d)", count, db.scalar(select(func.count(User.id))))


def main():
    logger.info("=== Starting Master Idempotent Data Ingestion to Neon neondb ===")
    with SessionLocal() as db:
        seed_skills_and_hobbies(db)
        seed_goals_and_interests(db)
        seed_metadata(db)
        seed_communities_and_places(db)
        seed_demo_users(db)
    logger.info("=== Master Seeding Finished Successfully ===")


if __name__ == "__main__":
    main()
