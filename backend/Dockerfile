FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies (FFmpeg for video transcoding, curl for container healthchecks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Install lightweight PyTorch CPU wheel
RUN pip install --no-cache-dir --timeout 1000 --retries 10 torch --index-url https://download.pytorch.org/whl/cpu

# Install Python application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 1000 --retries 10 -r requirements.txt

# Create non-root system user and working directories
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1001 -m -d /home/appuser appuser && \
    mkdir -p /app/uploads/tmp && \
    chown -R appuser:appgroup /app /home/appuser

# Copy database migration files and application code
COPY alembic ./alembic
COPY alembic.ini .
COPY app ./app

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Dynamically listen on host-assigned $PORT (Render, Railway, Koyeb, Fly.io) with default to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
