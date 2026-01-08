# app/repos/redis_jobs.py
import json
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

# 🔑 REDIS KEY PREFIX (CHANGE PER APP)
# pinecone-store  -> "pinecone:"
# pdf-web-api     -> "pdf:"
REDIS_PREFIX = os.getenv("REDIS_PREFIX")

# -------------------------------------------------
# In-memory fallback (LOCAL DEV)
# -------------------------------------------------
_IN_MEMORY_JOBS = {}


class InMemoryJobRepo:
    def _key(self, jobId: str) -> str:
        return f"{REDIS_PREFIX}{jobId}"

    def create(self, sourceId: str):
        jobId = f"job_{uuid.uuid4().hex[:8]}"
        data = {
            "jobId": jobId,
            "sourceId": sourceId,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "createdAt": datetime.utcnow().isoformat(),
        }
        _IN_MEMORY_JOBS[self._key(jobId)] = data
        return data

    def update(self, jobId, **kwargs):
        key = self._key(jobId)
        if key in _IN_MEMORY_JOBS:
            _IN_MEMORY_JOBS[key].update(kwargs)

    def complete(self, jobId):
        self.update(jobId, status="done", progress=100, stage="done")

    def fail(self, jobId, error):
        self.update(jobId, status="failed", error=error)

    def get(self, jobId):
        return _IN_MEMORY_JOBS.get(self._key(jobId), {
            "jobId": jobId,
            "status": "not_found"
        })


# -------------------------------------------------
# Redis-backed repo (PRODUCTION)
# -------------------------------------------------
class RedisJobRepo:
    def __init__(self):
        import redis  # lazy import (IMPORTANT)
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required in production")

        self.client = redis.from_url(redis_url, decode_responses=True)

    def _key(self, jobId: str) -> str:
        return f"{REDIS_PREFIX}{jobId}"

    def create(self, sourceId: str):
        jobId = f"job_{uuid.uuid4().hex[:8]}"
        data = {
            "jobId": jobId,
            "sourceId": sourceId,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "createdAt": datetime.utcnow().isoformat(),
        }
        self.client.set(self._key(jobId), json.dumps(data))
        return data

    def update(self, jobId, **kwargs):
        key = self._key(jobId)
        raw = self.client.get(key)
        if not raw:
            return
        data = json.loads(raw)
        data.update(kwargs)
        self.client.set(key, json.dumps(data))

    def complete(self, jobId):
        self.update(jobId, status="done", progress=100, stage="done")

    def fail(self, jobId, error):
        self.update(jobId, status="failed", error=error)

    def get(self, jobId):
        raw = self.client.get(self._key(jobId))
        return json.loads(raw) if raw else {
            "jobId": jobId,
            "status": "not_found"
        }


# -------------------------------------------------
# Factory (used everywhere)
# -------------------------------------------------
def get_job_repo():
    """
    Returns the correct job repo based on environment.
    """
    if USE_CELERY:
        return RedisJobRepo()
    return InMemoryJobRepo()
