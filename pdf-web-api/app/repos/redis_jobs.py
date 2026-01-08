import json
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

# TTL for job keys (seconds)
JOB_TTL = int(os.getenv("JOB_TTL", "3600"))  # 1 hour


# -------------------------------------------------
# In-memory fallback (LOCAL DEV)
# -------------------------------------------------
_IN_MEMORY_JOBS = {}


class InMemoryJobRepo:
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
        _IN_MEMORY_JOBS[jobId] = data
        return data

    def update(self, jobId, **kwargs):
        if jobId in _IN_MEMORY_JOBS:
            _IN_MEMORY_JOBS[jobId].update(kwargs)

    def complete(self, jobId):
        self.update(jobId, status="done", progress=100, stage="done")

    def fail(self, jobId, error):
        self.update(jobId, status="failed", error=error)

    def get(self, jobId):
        return _IN_MEMORY_JOBS.get(jobId, {
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

        # 🔒 SET TTL ON CREATE
        self.client.set(
            jobId,
            json.dumps(data),
            ex=JOB_TTL
        )

        return data

    def update(self, jobId, **kwargs):
        raw = self.client.get(jobId)
        if not raw:
            return

        data = json.loads(raw)
        data.update(kwargs)
        data["updatedAt"] = datetime.utcnow().isoformat()

        # 🔒 RESET TTL ON UPDATE
        self.client.set(
            jobId,
            json.dumps(data),
            ex=JOB_TTL
        )

    def complete(self, jobId):
        self.update(jobId, status="done", progress=100, stage="done")

    def fail(self, jobId, error):
        self.update(jobId, status="failed", error=error)

    def get(self, jobId):
        raw = self.client.get(jobId)
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
