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
    """
    Unified ingestion endpoint.

    - PDF  -> fileUrl (+ optional prompt)
    - WEB  -> sourceUrl (+ optional prompt)
    """

    # Create async job
    job = jobs.create(req.convId)

    # Decide ingestion type (SAFE: schema already validated)
    ingest_type = req.ingest_type()

    if ingest_type == "pdf":
        source = req.fileUrl.strip()
    else:  # web
        source = req.sourceUrl.strip()

    # Enqueue background task
    if USE_CELERY:
        ingest_document.delay(
            jobId=job["jobId"],
            userId=req.userId,
            convId=req.convId,
            source=source,
            prompt=req.prompt   # ✅ PROMPT PASSED SEPARATELY
        )
    else:
        ingest_document(
            job["jobId"],
            req.userId,
            req.convId,
            source,
            req.prompt
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
    store = FirestoreRepo()
    data = store.get(convId)

    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if data.get("status") != "ready":
        raise HTTPException(
            status_code=409,
            detail="Conversation is still processing"
        )

    if not data.get("summary"):
        raise HTTPException(
            status_code=500,
            detail="Conversation summary missing"
        )

    answer, mode, sources = answer_question(
        summary=data["summary"],
        question=req.question,
        userId=data["userId"],
        convId=convId
    )

    return {
        "convId": convId,
        "question": req.question,
        "answer": answer,
        "answerMode": mode,
        "sources": sources
    }
