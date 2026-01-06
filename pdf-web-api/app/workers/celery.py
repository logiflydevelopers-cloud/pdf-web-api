from celery import Celery
import os

REDIS_URL = os.environ.get("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL environment variable is required")

celery = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# -------------------------
# Celery configuration
# -------------------------
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# -------------------------
# FORCE task registration
# (REQUIRED on Render)
# -------------------------
import app.workers.ingest_task  # noqa: F401
