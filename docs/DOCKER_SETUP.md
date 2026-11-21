# Docker Setup & Deployment Guide

## 1. Services Architecture

The ALIGN container stack coordinates three core services:

| Service | Image / Build | Port Mapping | Description |
| :--- | :--- | :--- | :--- |
| `db` | `pgvector/pgvector:pg16` | `5433:5432` | PostgreSQL with pgvector extension enabled |
| `backend` | `./backend` | `8000:8000` | FastAPI application with SentenceTransformers engine |
| `frontend` | `./frontend` | `5173:5173` | React + Vite client |

---

## 2. Quick Start Commands

### Start All Services:
```powershell
docker compose up -d
```

### View Logs:
```powershell
docker compose logs -f
```

### Check Running Containers:
```powershell
docker compose ps
```

### Stop Services (Preserving Database Volume):
```powershell
docker compose down
```

### Rebuild Containers:
```powershell
docker compose up -d --build
```

---

## 3. Database Persistence

Database records and vector embeddings are persisted across restarts in the Docker named volume:
`align_postgres_data`

To inspect the volume:
```powershell
docker volume inspect align_align_postgres_data
```

---

## 4. Local Windows Host Access

To prevent port collision with any native PostgreSQL instance running on Windows port 5432, Docker maps the container port to host port `5433`:

- **Inside Docker Containers**: `postgresql+psycopg://align_user:align_dev_password@db:5432/align_db`
- **From Windows Host**: `postgresql+psycopg://align_user:align_dev_password@localhost:5433/align_db`
