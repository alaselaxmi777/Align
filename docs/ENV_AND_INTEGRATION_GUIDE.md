# ALIGN Environment & Third-Party Integration Guide

This guide details configuration, environment variables, credentials handling, and third-party API integration for ALIGN.

---

## 1. Environment Variables Reference

### 1.1 Backend Configuration (`backend/.env`)

| Variable | Required | Default / Example | Purpose |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://align_user:align_password@db:5432/align_db` | PostgreSQL connection string |
| `SECRET_KEY` | **Yes** | `align-super-secure-jwt-key-...` | Secret key for signing HS256 JWT access tokens |
| `ALGORITHM` | No | `HS256` | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Lifespan of access tokens in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` | Lifespan of persistent refresh tokens in days |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Allowed origins for cross-origin requests |
| `NEO4J_URI` | No | `bolt://neo4j:7687` | Neo4j Bolt connection URI |
| `NEO4J_USER` | No | `neo4j` | Neo4j database user |
| `NEO4J_PASSWORD` | No | `align_graph_password` | Neo4j database password |
| `EVENTBRITE_API_KEY` | No | *(Private API Token)* | Eventbrite v3 API token for real events sync |
| `GOOGLE_CLIENT_ID` | No | `...apps.googleusercontent.com` | Google OAuth2 Web Client ID |
| `GOOGLE_CLIENT_SECRET` | No | `...` | Google OAuth2 Web Client Secret |
| `GOOGLE_MAPS_API_KEY` | No | `AIzaSy...` | Google Places & Geocoding API key |
| `GITHUB_TOKEN` | No | `ghp_...` | GitHub Personal Access Token for profile sync |
| `GEMINI_API_KEY` | No | `AIzaSy...` | Gemini API key for Assistant V2 LLM tool calling |
| `HF_HUB_OFFLINE` | No | `0` (or `1` for air-gapped test) | HuggingFace offline mode toggle |
| `ENVIRONMENT` | No | `development` / `production` | Environment profile switch |

### 1.2 Frontend Configuration (`frontend/.env`)

| Variable | Required | Default / Example | Purpose |
|---|---|---|---|
| `VITE_API_URL` | **Yes** | `http://localhost:8000/api/v1` | Backend API base URL |
| `VITE_GOOGLE_CLIENT_ID` | No | `...apps.googleusercontent.com` | Google Identity Services client ID |
| `VITE_ENABLE_ASSISTANT_STREAMING` | No | `true` | Toggle for Assistant V2 SSE streaming |

---

## 2. Third-Party Integration Setup

### 2.1 Eventbrite API (Live Event Discovery)
- **Service**: Ingests real tech summits, developer workshops, and conferences.
- **Setup**:
  1. Register an application in the [Eventbrite Developer Portal](https://www.eventbrite.com/platform/api).
  2. Generate a Personal OAuth Token.
  3. Add to `backend/.env`:
     ```env
     EVENTBRITE_API_KEY=YOUR_EVENTBRITE_TOKEN
     ```
- **Fallback Behavior**: If the key is absent or rates are exceeded, ALIGN gracefully serves all database-registered events without crashing.

### 2.2 Google Identity OAuth2 (One-Click Sign-In)
- **Service**: Passwordless login using Google Identity Services.
- **Setup**:
  1. In the [Google Cloud Console](https://console.cloud.google.com/), navigate to **APIs & Services $\rightarrow$ Credentials**.
  2. Create an **OAuth 2.0 Client ID** (Web application).
  3. Add Authorized JavaScript origins: `http://localhost:5173` and production domain.
  4. Add Authorized redirect URIs: `http://localhost:5173/auth` and production domain.
  5. Add Client ID to both `backend/.env` and `frontend/.env`:
     ```env
     GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
     ```
- **Verification**: Backend verifies token signature, issuer (`accounts.google.com`), and audience using the Google Auth library.

### 2.3 Google Places & OpenStreetMap Overpass (Verified Venues)
- **Service**: Resolves authentic venue names, exact coordinates, ratings, and photography.
- **Setup**:
  1. Enable **Places API (New)** and **Geocoding API** in Google Cloud Console.
  2. Restrict API key by HTTP referrers.
  3. Add to `backend/.env`:
     ```env
     GOOGLE_MAPS_API_KEY=YOUR_API_KEY
     ```
- **Fallback**: The platform includes OpenStreetMap Overpass sync scripts as an open-source zero-cost fallback for local venue ingestion.

### 2.4 Neo4j Graph Database
- **Service**: Community topology, graph clustering, and collaborative filtering.
- **Setup**:
  - Automatically configured and spun up via `docker-compose.yml` (`neo4j:5.20-community`).
  - APOC plugin is mounted and enabled for graph algorithms and batch processing.
  - Verification: Open browser at `http://localhost:7474` and login with `neo4j` / `align_graph_password`.

### 2.5 SentenceTransformers & Local Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors).
- **Offline / Air-Gapped Mode**:
  - The model weights are automatically downloaded and cached in `~/.cache/huggingface/hub`.
  - If network access to Hugging Face is unavailable, ALIGN includes an integrated deterministic vector fallback ensuring all vector operations, tests, and database seeding succeed offline.

---

## 3. Security & Secret Protection Protocol

1. **Zero Secret Commits**:
   - `.env`, `.env.local`, `*.pem`, and `credentials.json` are strictly ignored by `.gitignore`.
   - Never commit raw API keys to Git history.
2. **Secret Rotation Protocol**:
   - If a test token or credential is ever exposed, immediately revoke it in the respective provider dashboard (Eventbrite, Google Cloud, GitHub).
   - Generate a replacement secret and update local `.env` securely.
