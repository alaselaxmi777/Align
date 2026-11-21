import os
import json
import random
from dataclasses import dataclass, field
import openpyxl
from sklearn.model_selection import train_test_split
from app.services.embeddings import generate_embedding

BENCHMARK_CACHE_FILE = os.path.join(os.path.dirname(__file__), "benchmark_cache.json")

@dataclass
class BenchmarkItem:
    id: int
    title: str
    category: str
    description: str
    tags: str
    location: str
    latitude: float
    longitude: float
    popularity: float
    embedding: list[float] = field(default_factory=list)

@dataclass
class BenchmarkQuery:
    id: int
    query: str
    relevant_ids: set[int]
    is_hard: bool
    category: str
    user_lat: float | None = None
    user_lon: float | None = None
    target_category: str | None = None

# Realistic geographic centroids for community clusters
CITIES = [
    ("San Francisco, CA", 37.7749, -122.4194),
    ("Oakland, CA", 37.8044, -122.2712),
    ("Berkeley, CA", 37.8715, -122.2730),
    ("Palo Alto, CA", 37.4419, -122.1430),
    ("San Jose, CA", 37.3382, -121.8863),
]

def load_or_create_benchmark_items(num_items: int = 400, seed: int = 42) -> list[BenchmarkItem]:
    """Loads 400 benchmark items sampled deterministically from Excel master datasets."""
    random.seed(seed)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # If general 400 cache exists, slice from it to avoid re-computing embeddings
    cache_400 = os.path.join(os.path.dirname(__file__), "items_cache_400.json")
    if os.path.exists(cache_400):
        try:
            with open(cache_400, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = [BenchmarkItem(**d) for d in data]
                if len(items) >= num_items:
                    return items[:num_items]
        except Exception:
            pass

    cache_path = os.path.join(os.path.dirname(__file__), f"items_cache_{num_items}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [BenchmarkItem(**d) for d in data]
        except Exception:
            pass

    items: list[BenchmarkItem] = []
    curr_id = 1

    # 1. Load from goals_and_interests_10000_records.xlsx
    goals_path = os.path.join(base_dir, "goals_and_interests_10000_records.xlsx")
    if not os.path.exists(goals_path):
        goals_path = os.path.join(base_dir, "backend", "goals_and_interests_10000_records.xlsx")

    if os.path.exists(goals_path):
        wb = openpyxl.load_workbook(goals_path, read_only=True)
        ws = wb["10000 Records"]
        rows = list(ws.iter_rows(values_only=True))[1:]  # skip header
        target_goals = min(int(num_items * 0.625), len(rows))
        sampled_rows = random.sample(rows, max(0, min(target_goals, len(rows))))
        for r in sampled_rows:
            rec_id, r_type, cat, sub_type, desc, life_ctx, timeline, priority, status, motivation, pop, expanded = r[:12]
            city, lat, lon = random.choice(CITIES)
            # Create descriptive item title & tags
            title = f"{sub_type or r_type} Collective"
            clean_desc = expanded or desc or f"Community circle focused on {sub_type}."
            tags_list = [str(x).lower() for x in [cat, sub_type, r_type, motivation] if x]
            tags = ", ".join(tags_list)
            pop_score = float(pop or 5.0)

            items.append(BenchmarkItem(
                id=curr_id,
                title=title,
                category=str(cat or "Personal Growth"),
                description=str(clean_desc),
                tags=tags,
                location=city,
                latitude=lat,
                longitude=lon,
                popularity=pop_score,
                embedding=[],
            ))
            curr_id += 1

    # 2. Load from skills_and_hobbies_5000_records.xlsx
    skills_path = os.path.join(base_dir, "skills_and_hobbies_5000_records.xlsx")
    if not os.path.exists(skills_path):
        skills_path = os.path.join(base_dir, "backend", "skills_and_hobbies_5000_records.xlsx")

    if os.path.exists(skills_path):
        wb = openpyxl.load_workbook(skills_path, read_only=True)
        ws = wb["5000 Records"]
        rows = list(ws.iter_rows(values_only=True))[1:]
        needed = max(0, num_items - len(items))
        if needed > 0 and len(rows) > 0:
            sampled_rows = random.sample(rows, min(needed, len(rows)))
            for r in sampled_rows:
                rec_id, r_type, cat, sub_type, desc, app_ctx, prof, setting, freq, motivation, pop, expanded = r[:12]
                city, lat, lon = random.choice(CITIES)
                title = f"{sub_type or r_type} Guild"
                clean_desc = expanded or desc or f"Hands-on workshop and community for {sub_type}."
                tags_list = [str(x).lower() for x in [cat, sub_type, r_type, setting] if x]
                tags = ", ".join(tags_list)
                pop_score = float(pop or 5.0)

                items.append(BenchmarkItem(
                    id=curr_id,
                    title=title,
                    category=str(cat or "Skills & Hobbies"),
                    description=str(clean_desc),
                    tags=tags,
                location=city,
                latitude=lat,
                longitude=lon,
                popularity=pop_score,
                embedding=[],
            ))
            curr_id += 1

    # Pre-generate embeddings
    for item in items:
        text = f"{item.title} {item.description} {item.category} {item.tags}"
        item.embedding = generate_embedding(text)

    # Save cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump([item.__dict__ for item in items], f)
    except Exception:
        pass

    return items

def build_benchmark_queries(items: list[BenchmarkItem], seed: int = 42) -> list[BenchmarkQuery]:
    """
    Constructs 120 diverse intent queries spanning standard and hard vocabulary-mismatch scenarios.
    Ground-truth labels are established through multi-attribute semantic assignment.
    """
    random.seed(seed)
    queries: list[BenchmarkQuery] = []

    # Helper to find items matching criteria
    def find_ids(keywords: list[str], max_count: int = 5) -> set[int]:
        matched = set()
        for it in items:
            text = (it.title + " " + it.description + " " + it.tags + " " + it.category).lower()
            if any(k.lower() in text for k in keywords):
                matched.add(it.id)
                if len(matched) >= max_count:
                    break
        return matched

    # 1. Standard Queries (Lexical keywords present in description/tags)
    standard_templates = [
        ("I want to learn deep learning and neural network architectures with python", ["deep learning", "neural network", "python", "machine learning"], "Technology"),
        ("Looking for weekend watercolor painting and botanical sketching groups", ["painting", "watercolor", "drawing", "sketching", "art"], "Arts"),
        ("Frontend web development with TypeScript React and CSS performance", ["react", "typescript", "frontend", "web development", "coding"], "Technology"),
        ("Hardware hacking robotics PCB soldering and embedded microcontrollers", ["robotics", "hardware", "arduino", "electronics"], "Engineering"),
        ("Early stage founders venture capital strategy and B2B SaaS sales", ["startup", "venture capital", "entrepreneurship", "business"], "Business"),
        ("Trail running marathon training and long distance endurance intervals", ["running", "marathon", "fitness", "trail"], "Fitness"),
        ("Design systems Figma auto-layout and accessible UI UX patterns", ["figma", "ui/ux", "design", "graphic design"], "Design"),
        ("Philosophy discussions exploring Stoicism ethics and classic literature", ["philosophy", "books", "reading", "literature", "humanities"], "Humanities"),
        ("Large language models prompt engineering RAG pipelines and vector databases", ["llm", "ai", "artificial intelligence", "nlp", "data science"], "Technology"),
        ("Urban cycling group rides bike maintenance and road safety advocacy", ["cycling", "bike", "fitness", "outdoor"], "Fitness"),
        ("Acoustic guitar fingerstyle and music production home studio recording", ["music", "guitar", "audio", "production"], "Arts"),
        ("Ceramics pottery wheel throwing and clay glazing workshops", ["pottery", "ceramics", "sculpture", "craft"], "Arts"),
        ("Creative writing fiction workshops character development and novel drafting", ["writing", "fiction", "novel", "literature"], "Humanities"),
        ("Astrophysics astronomy stargazing and amateur telescope observation", ["astronomy", "science", "physics", "telescope"], "Science"),
        ("Mobile app development using React Native Flutter and iOS Swift", ["mobile", "app development", "flutter", "swift", "coding"], "Technology"),
        ("Culinary sourdough bread baking and fermentation science classes", ["baking", "cooking", "culinary", "food"], "Lifestyle"),
        ("Public speaking communication storytelling and leadership toastmasters", ["public speaking", "communication", "leadership", "speaking"], "Career"),
        ("Mindfulness breathwork vipassana meditation and sound healing circle", ["meditation", "mindfulness", "wellness", "breathwork"], "Wellness"),
        ("Specialty coffee pour-over extraction espresso calibration and latte art", ["coffee", "culinary", "brewing", "beverage"], "Lifestyle"),
        ("Competitive chess strategy tactical puzzles and blitz tournaments", ["chess", "strategy", "board games", "games"], "Mind Games"),
        ("Woodworking joinery hand planes and custom timber furniture building", ["woodworking", "carpentry", "furniture", "craft"], "Crafts"),
        ("Yoga vinyasa flow flexibility posture alignment and breathwork", ["yoga", "pilates", "flexibility", "wellness"], "Fitness"),
        ("Cybersecurity penetration testing ethical hacking and network security", ["cybersecurity", "security", "networking", "linux"], "Technology"),
        ("Organic gardening permaculture composting and urban balcony agriculture", ["gardening", "agriculture", "plants", "sustainability"], "Environment"),
        ("Board game strategy nights engine building and cooperative table games", ["board games", "tabletop", "games", "gaming"], "Social"),
        ("Hiking mountain peaks wilderness survival and lightweight backpacking", ["hiking", "backpacking", "outdoor", "camping"], "Outdoors"),
        ("DevOps continuous integration Kubernetes container clusters and Terraform", ["devops", "cloud", "docker", "kubernetes"], "Technology"),
        ("Digital photography street portrait composition and Adobe Lightroom editing", ["photography", "camera", "photo", "lightroom"], "Arts"),
        ("Rock climbing bouldering technique grip strength and belaying certification", ["climbing", "bouldering", "fitness", "sports"], "Sports"),
        ("Personal finance index fund investing budgeting and retirement planning", ["finance", "investing", "money", "wealth"], "Finance"),
    ]

    qid = 1
    for text, keys, cat in standard_templates:
        rel = find_ids(keys, max_count=4)
        if not rel:
            rel = {items[qid % len(items)].id}
        queries.append(BenchmarkQuery(
            id=qid,
            query=text,
            relevant_ids=rel,
            is_hard=False,
            category=cat,
            user_lat=37.7749,
            user_lon=-122.4194,
            target_category=cat,
        ))
        qid += 1

    # 2. Replicate across variations to generate diverse intents
    variations = [
        "Looking for a supportive community to practice {q_term}",
        "Are there any active meetups or workshops for {q_term} in the bay area",
        "I need peers who are passionate about {q_term} to collaborate with",
    ]
    for text, keys, cat in standard_templates:
        q_term = keys[0]
        for v_template in variations[:2]:
            v_text = v_template.format(q_term=q_term)
            rel = find_ids(keys, max_count=4)
            queries.append(BenchmarkQuery(
                id=qid,
                query=v_text,
                relevant_ids=rel,
                is_hard=False,
                category=cat,
                user_lat=37.7749,
                user_lon=-122.4194,
                target_category=cat,
            ))
            qid += 1

    # 3. Hard Queries (Semantic intent with minimal/zero lexical overlap)
    # Pure keyword search fails here because target items do not use these exact words.
    hard_templates = [
        ("I want to feel less stressed and spend time outdoors", ["hiking", "outdoor", "nature", "meditation"], "Wellness"),
        ("Seeking a calm mind and better physical balance through gentle body movement", ["yoga", "pilates", "meditation", "flexibility"], "Wellness"),
        ("Creative visual expression without screen fatigue or digital blue light", ["watercolor", "painting", "drawing", "pottery", "ceramics"], "Arts"),
        ("Struggling with nervousness when presenting in front of an audience", ["public speaking", "communication", "leadership"], "Career"),
        ("Looking to meet analytical problem solvers on weekend logic challenges", ["chess", "board games", "strategy", "mathematics"], "Mind Games"),
        ("Need to recover from burnout by working with tactile natural materials", ["woodworking", "ceramics", "gardening", "craft"], "Crafts"),
        ("Want to build endurance and breathe fresh morning air before work", ["running", "marathon", "cycling", "fitness"], "Fitness"),
        ("Connect with curious thinkers discussing the meaning of existence and virtue", ["philosophy", "books", "reading", "ethics"], "Humanities"),
        ("Looking for hands-on culinary fermentation and artisanal kitchen skills", ["baking", "cooking", "culinary", "food"], "Lifestyle"),
        ("Want to automate cloud deployment pipelines and prevent site downtime", ["devops", "cloud", "docker", "kubernetes", "linux"], "Technology"),
        ("Need to gain confidence managing personal wealth and achieving independence", ["finance", "investing", "budgeting", "money"], "Finance"),
        ("Fascinated by the night sky cosmic phenomena and distant celestial bodies", ["astronomy", "telescope", "science"], "Science"),
        ("Looking to craft acoustic melodies with strings in a quiet creative space", ["guitar", "music", "audio"], "Arts"),
        ("Want to learn defensive computer techniques to protect data systems", ["cybersecurity", "security", "networking"], "Technology"),
        ("Seeking physical adrenaline and vertical wall challenges with team safety", ["climbing", "bouldering", "sports"], "Sports"),
        ("Overwhelmed by unstructured days and need disciplined time tracking systems", ["productivity", "goal", "habits", "leadership"], "Personal Growth"),
        ("Want to build interactive web experiences that feel fast and delightful", ["frontend", "react", "typescript", "design"], "Technology"),
        ("Looking for friendly tabletop social nights that don't involve bars or alcohol", ["board games", "tabletop", "chess"], "Social"),
        ("Desire to write stories that captivate imagination and explore human nature", ["writing", "fiction", "literature", "novel"], "Humanities"),
        ("Seeking restorative somatic practices to release shoulder and neck tension", ["yoga", "wellness", "pilates", "meditation"], "Wellness"),
        ("Want to construct physical electronics that move autonomously in the real world", ["robotics", "hardware", "arduino", "electronics"], "Engineering"),
        ("Looking to capture fleeting urban moments through a viewfinder lens", ["photography", "camera", "photo", "art"], "Arts"),
        ("Need to structure a high-growth tech venture from product validation to seed funding", ["startup", "entrepreneurship", "business", "founders"], "Business"),
        ("Want to explore sustainable living and grow edible plants at home", ["gardening", "sustainability", "agriculture"], "Environment"),
        ("Seeking a supportive circle for non-native speakers to hone natural conversation", ["languages", "communication", "speaking"], "Social"),
        ("Looking for long weekend scenic two-wheeled journeys through hill climbs", ["cycling", "bike", "outdoors", "fitness"], "Fitness"),
        ("Want to express deep emotions through three-dimensional tactile sculpting", ["ceramics", "sculpture", "clay", "pottery"], "Arts"),
        ("Looking to explore machine reasoning and neural representations of text", ["nlp", "llm", "ai", "deep learning"], "Technology"),
        ("Seeking a reflective book discussion group exploring timeless moral questions", ["philosophy", "books", "reading", "literature"], "Humanities"),
        ("Want to develop muscular stamina without lifting heavy metal barbells", ["climbing", "running", "yoga", "swimming"], "Fitness"),
        ("Looking to escape corporate bureaucracy by launching an independent venture", ["startup", "founders", "entrepreneurship"], "Business"),
        ("Need a quiet morning community for espresso craft and bean origins", ["coffee", "culinary", "brewing"], "Lifestyle"),
        ("Looking for hands-on timber joinery to build heirloom household pieces", ["woodworking", "carpentry", "craft"], "Crafts"),
        ("Seeking to transition my career from manual operations to automated cloud code", ["devops", "cloud", "python", "coding"], "Career"),
        ("Want to explore wild mountain ridges and navigate with compass and topographic maps", ["hiking", "backpacking", "outdoor"], "Outdoors"),
    ]

    for text, keys, cat in hard_templates:
        rel = find_ids(keys, max_count=4)
        if not rel:
            rel = {items[qid % len(items)].id}
        queries.append(BenchmarkQuery(
            id=qid,
            query=text,
            relevant_ids=rel,
            is_hard=True,
            category=cat,
            user_lat=37.7749,
            user_lon=-122.4194,
            target_category=cat,
        ))
        qid += 1

    return queries

def get_benchmark_splits(
    items: list[BenchmarkItem],
    queries: list[BenchmarkQuery],
    seed: int = 42,
) -> tuple[list[BenchmarkQuery], list[BenchmarkQuery], list[BenchmarkQuery]]:
    """Splits queries into Train (60%), Validation (20%), and Test (20%)."""
    q_train, q_temp = train_test_split(queries, test_size=0.40, random_state=seed, stratify=[q.is_hard for q in queries])
    q_val, q_test = train_test_split(q_temp, test_size=0.50, random_state=seed, stratify=[q.is_hard for q in q_temp])
    return q_train, q_val, q_test
