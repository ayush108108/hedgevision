"""Gunicorn configuration for HedgeVision Docker deployment."""

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
workers = int(os.getenv("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "uvicorn.workers.UvicornWorker"

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEP_ALIVE", "5"))

# ---------------------------------------------------------------------------
# Server mechanics
# ---------------------------------------------------------------------------
preload_app = True
forwarded_allow_ips = "*"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# ---------------------------------------------------------------------------
# Request limits
# ---------------------------------------------------------------------------
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190
