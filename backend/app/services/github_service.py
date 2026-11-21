import os
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from app.core.config import settings

logger = logging.getLogger(__name__)

def http_get_json_with_retry(url: str, headers: dict, timeout: float = 6.0, max_retries: int = 2) -> dict | None:
    """Performs HTTP GET with timeouts and exponential backoff retries."""
    req = urllib.request.Request(url, headers=headers)
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(0.4 * (2 ** attempt))
    logger.debug(f"HTTP GET failed after {max_retries} retries for {url}: {last_err}")
    return None

def get_headers() -> dict:
    headers = {
        "User-Agent": "Align-App",
        "Accept": "application/vnd.github+json"
    }
    token = settings.github_token or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

COMMON_TECH_SKILLS = {
    "python", "javascript", "typescript", "react", "nextjs", "vue", "angular",
    "pytorch", "tensorflow", "fastapi", "django", "flask", "docker", "kubernetes",
    "golang", "rust", "c++", "c#", "java", "kotlin", "swift", "flutter",
    "aws", "gcp", "azure", "postgresql", "mongodb", "graphql", "sql", "git",
    "llm", "rag", "langchain", "deep learning", "machine learning", "nlp", "ai"
}

def extract_skills_from_text(text: str) -> set[str]:
    if not text:
        return set()
    found = set()
    lower = text.lower()
    for skill in COMMON_TECH_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", lower):
            found.add(skill.capitalize() if len(skill) > 2 else skill.upper())
    return found

def fetch_github_people(query: str = "tech", location: str = "", limit: int = 6) -> list[dict]:
    """
    Searches GitHub users by skills, keywords, and optional location.
    Enriches with user bio, location, top skills, and avatar.
    """
    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    words = [w for w in clean_q.split() if len(w) > 1 and w.lower() not in {"find", "people", "developer", "developers", "looking", "for", "in", "near"}]
    search_keyword = "+".join(words[:4]) if words else "developer"

    q_parts = [search_keyword]
    if location and len(location.strip()) > 2:
        q_parts.append(f"location:{location.strip()}")
    
    full_q = "+".join(q_parts)
    url = f"https://api.github.com/search/users?q={full_q}&per_page={limit}"

    data = http_get_json_with_retry(url, headers=get_headers(), timeout=8.0, max_retries=2)
    if not data:
        logger.warning(f"GitHub search users failed or timed out for '{full_q}'")
        return []

    items = data.get("items", [])

    people = []
    for item in items[:limit]:
        user_url = item.get("url")
        if not user_url:
            continue
        try:
            u_detail = http_get_json_with_retry(user_url, headers=get_headers(), timeout=6.0, max_retries=1)
            if not u_detail:
                continue
                
            name = u_detail.get("name") or u_detail.get("login") or "Developer"
            login = u_detail.get("login")
            bio = u_detail.get("bio") or "Passionate software builder and open source contributor."
            user_loc = u_detail.get("location") or location or "Global"
            avatar = u_detail.get("avatar_url")
            html_url = u_detail.get("html_url")
            company = u_detail.get("company") or ""
            public_repos = u_detail.get("public_repos") or 0

            # Extract skills from bio + company
            detected_skills = extract_skills_from_text(f"{bio} {company} {query}")
            skills_list = sorted(list(detected_skills))
            if not skills_list:
                skills_list = [w.capitalize() for w in words[:3]] if words else ["Code", "OpenSource"]

            people.append({
                "id": u_detail.get("id"),
                "login": login,
                "name": name,
                "bio": bio,
                "location": user_loc,
                "avatar_url": avatar,
                "html_url": html_url,
                "skills": skills_list,
                "skills_str": ", ".join(skills_list),
                "public_repos": public_repos,
            })
        except Exception as exc:
            logger.debug(f"Could not fetch user details for {item.get('login')}: {exc}")
            continue

    return people

def fetch_user_github_skills(username: str) -> dict:
    """
    Fetches a specific GitHub user's profile and top repo languages to build a verified skill stack.
    """
    clean_user = username.strip().replace("@", "")
    profile_url = f"https://api.github.com/users/{clean_user}"
    repos_url = f"https://api.github.com/users/{clean_user}/repos?sort=updated&per_page=12"

    profile_data = http_get_json_with_retry(profile_url, headers=get_headers(), timeout=8.0, max_retries=2)
    if not profile_data:
        return {
            "username": clean_user,
            "name": clean_user,
            "bio": "GitHub user profile unavailable.",
            "location": "",
            "avatar_url": None,
            "skills": [],
            "skills_string": "",
            "verified_repos_count": 0,
        }

    skills = set()
    bio_skills = extract_skills_from_text(profile_data.get("bio") or "")
    skills.update(bio_skills)

    try:
        repos_data = http_get_json_with_retry(repos_url, headers=get_headers(), timeout=8.0, max_retries=1)
        if repos_data and isinstance(repos_data, list):
            for repo in repos_data:
                lang = repo.get("language")
                if lang:
                    skills.add(lang)
                for topic in repo.get("topics", []):
                    if topic and len(topic) <= 20:
                        skills.add(topic.capitalize())
    except Exception as exc:
        logger.warning(f"Could not fetch repos for {clean_user}: {exc}")

    skill_list = sorted(list(skills))
    return {
        "username": clean_user,
        "name": profile_data.get("name") or clean_user,
        "bio": profile_data.get("bio") or "Builder & developer on GitHub.",
        "location": profile_data.get("location") or "",
        "avatar_url": profile_data.get("avatar_url"),
        "skills": skill_list,
        "skills_string": ", ".join(skill_list),
        "html_url": profile_data.get("html_url"),
        "public_repos": profile_data.get("public_repos", 0),
    }

def fetch_github_good_first_issues(query: str = "python", limit: int = 8) -> list[dict]:
    """Fetches real 'good first issue' open tickets from active GitHub repositories."""
    clean_term = re.sub(r"[^\w\s-]", " ", query).strip()
    words = [w for w in clean_term.split() if len(w) > 1]
    search_q = "+".join(words[:2]) if words else "python"
    
    url = f"https://api.github.com/search/issues?q=label:%22good+first+issue%22+is:open+is:issue+{search_q}&sort=updated&order=desc&per_page={limit}"
    data = http_get_json_with_retry(url, headers=get_headers(), timeout=8.0, max_retries=2)
    if not data:
        logger.warning(f"GitHub search issues failed for query '{search_q}'")
        return []

    items = data.get("items", [])
    results = []
    for it in items[:limit]:
        repo_url = it.get("repository_url", "")
        repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else "Open Source Project"
        labels = [l.get("name") for l in it.get("labels", []) if l.get("name")]
        
        results.append({
            "id": it.get("id"),
            "title": it.get("title", "Open Source Issue"),
            "html_url": it.get("html_url", ""),
            "repository": repo_name,
            "comments_count": it.get("comments", 0),
            "labels": labels[:4],
            "created_at": it.get("created_at"),
            "state": it.get("state", "open"),
        })

    return results
