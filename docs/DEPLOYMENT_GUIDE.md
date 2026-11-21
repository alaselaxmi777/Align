# ALIGN Deployment & Operations Guide

This guide provides complete instructions for running, testing, deploying, and maintaining ALIGN across local development, containerized environments, and production hosting.

---

## 1. System Requirements

- **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows 11 with WSL2 / Docker Desktop.
- **Docker & Docker Compose**: Docker 24.0+ and Compose v2.20+.
- **Node.js**: v18.18+ or v20.x LTS.
- **Python**: Python 3.12+ (when running natively outside Docker).
- **RAM**: Minimum 8 GB recommended (16 GB for heavy graph analytics).
- **Disk**: 15 GB free space for database volumes and model caches.

---

## 2. Fast-Track Containerized Deployment (Recommended)

ALIGN is pre-configured with a production-grade Docker Compose orchestration stack consisting of 4 interconnected containers:
1. `align-db`: PostgreSQL 16 with `pgvector` extension.
2. `align-neo4j`: Neo4j 5 Community with APOC plugins.
3. `align-backend`: FastAPI Python 3.12 service.
4. `align-frontend`: React 18 + Vite development/production server.

### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/align.git
cd align
```

### Step 2: Configure Environment Files
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```
Ensure `SECRET_KEY`, `DATABASE_URL`, and `VITE_API_URL` are appropriately set.

### Step 3: Start Services
```bash
docker compose up -d --build
```

### Step 4: Run Database Migrations
```bash
docker exec -e PYTHONPATH=. align-backend-1 alembic upgrade head
```

### Step 5: Seed Master Datasets (Skills, Hobbies, Goals, Interests)
```bash
docker exec -e PYTHONPATH=. align-backend-1 python scripts/import_skills_hobbies.py
docker exec -e PYTHONPATH=. align-backend-1 python scripts/import_goals_interests.py
```

### Step 6: Verify Service Health
- **Frontend Web UI**: Open `http://localhost:5173` in your browser.
- **Backend API Docs (Swagger UI)**: Open `http://localhost:8000/docs`.
- **Backend Health Check**:
  ```bash
  curl http://localhost:8000/api/v1/health
  # Response: {"status":"healthy","database":"connected","vector_extension":"ready"}
  ```
- **Neo4j Browser**: Open `http://localhost:7474` (User: `neo4j`, Password: `align_graph_password`).

---

## 3. Native Local Development Setup

If running without Docker:

### 3.1 Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.2 Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Vite runs at http://localhost:5173
```

---

## 4. Verification & Automated Test Suite

To verify system integrity, run the complete 72-test automated suite inside the container:
```bash
docker exec -e PYTHONPATH=. align-backend-1 pytest tests/ -v
```

To run the full 18-scenario end-to-end integration test:
```bash
docker exec -e PYTHONPATH=. align-backend-1 pytest tests/test_phase6_18_scenarios.py -v
```

To run the frontend production build:
```bash
npm run build --prefix frontend
```

---

## 5. Production Hardening & Best Practices

1. **Reverse Proxy (Nginx / Caddy)**:
   - Terminate SSL/TLS (HTTPS) using Let's Encrypt certificates.
   - Proxy `/api` traffic to backend port 8000 with headers:
     ```nginx
     proxy_set_header Host $host;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto $scheme;
     ```
   - For SSE streaming (`/api/v1/assistant/chat/stream`), disable proxy buffering:
     ```nginx
     proxy_buffering off;
     proxy_cache off;
     proxy_read_timeout 600s;
     ```
2. **Database Backup Strategy**:
   - Schedule daily automated `pg_dump` backups for `align_db`.
   - Preserve `align_postgres_data` Docker volume.
3. **Secret Isolation**:
   - Store production secrets in AWS Secrets Manager, HashiCorp Vault, or Docker Secrets rather than plaintext `.env` files.
