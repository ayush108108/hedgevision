# syntax=docker/dockerfile:1

# ==============================================================================
# HedgeVision Backend — Multi-stage Production Build
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder — compile C extensions (numpy, scipy, psycopg2)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY hedgevision/ ./hedgevision/

RUN pip install --no-cache-dir --prefix=/install .

# ------------------------------------------------------------------------------
# Stage 2: Runtime — minimal footprint, no compiler toolchain
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl tini \
    && rm -rf /var/lib/apt/lists/*

# Pull in pre-built Python packages
COPY --from=builder /install /usr/local

WORKDIR /app

# Application code
COPY backend/  ./backend/
COPY hedgevision/ ./hedgevision/
COPY config/   ./config/
COPY pyproject.toml ./

# Gunicorn configuration
COPY docker/gunicorn.conf.py ./gunicorn.conf.py

# Python path: resolve both "from api.utils…" and "from backend.api…" imports
ENV PYTHONPATH=/app:/app/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd -r hedgevision && useradd -r -g hedgevision -d /app -s /sbin/nologin hedgevision \
    && mkdir -p /app/data \
    && chown -R hedgevision:hedgevision /app

USER hedgevision

# Runtime defaults (override via env or compose)
ENV API_HOST=0.0.0.0 \
    API_PORT=8000 \
    DATA_BACKEND=sqlite \
    DB_PATH=/app/data/prices.db \
    WEB_CONCURRENCY=2 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_GRACEFUL_TIMEOUT=30 \
    GUNICORN_KEEP_ALIVE=5

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["curl", "-sf", "http://localhost:8000/health", "-o", "/dev/null"]

ENTRYPOINT ["tini", "--"]
CMD ["gunicorn", "backend.api.main:app", "-c", "gunicorn.conf.py"]
