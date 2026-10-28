# ==============================================================================
# Service: api (Proximity Search Backend API)
# Base Image: Python 3.11 Slim (Minimal attack surface & small image size)
# ==============================================================================
FROM python:3.11-slim

LABEL maintainer="Katari Venu (12341110)"
LABEL description="Lab 7 Proximity Search Graph Traversal API Service"
LABEL version="1.0.0"

# Python runtime optimizations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    WORKERS=3 \
    TIMEOUT=60 \
    DATA_CSV_PATH=/app/data/locations.csv \
    DEFAULT_LINK_PATH=/app/data/link.txt

WORKDIR /app

# Install dependencies first for efficient layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Security hardening: Create non-root application user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Copy application source code and default assets
COPY . /app/

# Ensure runtime directories exist with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 5000

# Docker Healthcheck to monitor service readiness
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Launch production WSGI Gunicorn server
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers ${WORKERS} --timeout ${TIMEOUT} --access-logfile - --error-logfile - app:app"]
