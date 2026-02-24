FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir celery[redis] psycopg2-binary

# Copy application code
COPY packages/ packages/
COPY apps/api/ apps/api/

# Create logs and backups directories
RUN mkdir -p /app/logs /app/backups && \
    chmod -R 755 /app/logs /app/backups

# Run Celery worker
CMD ["celery", "-A", "apps.api.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=${CONCURRENCY:-2}", \
     "--max-tasks-per-child=1000", \
     "--time-limit=3600", \
     "--soft-time-limit=3300"]
