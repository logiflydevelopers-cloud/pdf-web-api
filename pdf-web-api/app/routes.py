from fastapi import APIRouter, HTTPException
from app.repos.redis_jobs import get_job_repo
from app.repos.firestore_repo import FirestoreRepo
from app.workers.ingest_task import ingest_document
from app.schemas.ingest import IngestRequest
from app.schemas.qa import AskRequest
from app.services.qa_engine import answer_question
import os

USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

router = APIRouter(prefix="/v1")

jobs = get_job_repo()


# --------------------------------------------------
# Ingest PDF or Website
# --------------------------------------------------
@router.post("/ingest", status_code=202)
def ingest(req: IngestRequest):
    job = jobs.create(req.convId)

    # --------------------------------------------------
    # Resolve source
    # Priority:
    # 1. fileUrl (PDF or website)
    # 2. prompt (plain text or URL)
    # --------------------------------------------------
    source = req.fileUrl or req.prompt

    if not source or not isinstance(source, str) or not source.strip():
        raise HTTPException(
            status_code=400,
            detail="Either fileUrl or prompt must be provided as a non-empty string"
        )

    source = source.strip()

    if USE_CELERY:
        ingest_document.delay(
        jobId=job["jobId"],
        userId=req.userId,
        convId=req.convId,
        source=source   # STRING URL
    )

    else:
        ingest_document(
            job["jobId"],
            req.userId,
            req.convId,
            source
        )

    return {
        "jobId": job["jobId"],
        "convId": req.convId,
        "status": "queued"
    }


# --------------------------------------------------
# Job Status
# --------------------------------------------------
@router.get("/jobs/{jobId}")
def job_status(jobId: str):
    data = jobs.get(jobId)
    store = FirestoreRepo()

    if data["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    if data["status"] == "done":
        result = store.get(data.get("convId"))
        data["result"] = result

    return data

# --------------------------------------------------
# Ask Question (Summary → RAG)
# --------------------------------------------------
@router.post("/conversations/{convId}/ask")
def ask(convId: str, req: AskRequest):
    data = store.get(convId)

    if not data or "summary" not in data:
        raise HTTPException(
            status_code=404,
            detail="Conversation not ready or not found"
        )

    answer, mode, sources = answer_question(
        summary=data["summary"],
        question=req.question,
        convId=convId
    )

    return {
        "convId": convId,
        "question": req.question,
        "answer": answer,
        "answerMode": mode,
        "sources": sources
    }





