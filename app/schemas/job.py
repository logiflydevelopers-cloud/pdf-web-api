# app/repos/job.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class JobStatus(BaseModel):
    jobId: str
    convId: Optional[str] = None

    status: str
    stage: Optional[str] = None
    progress: Optional[int] = None
    error: Optional[str] = None

    # Present only when job is done
    result: Optional[Dict[str, Any]] = None
