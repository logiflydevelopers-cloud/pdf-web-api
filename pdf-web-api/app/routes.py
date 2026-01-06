from fastapi import APIRouter, HTTPException
from app.repos.redis_jobs import get_job_repo
from app.repos.firestore_repo import FirestoreRepo
from app.workers.ingest_task import ingest_pdf
from app.schemas.ingest import IngestRequest
from app.schemas.qa import AskRequest
from app.services.qa_engine import answer_question
import os

USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

router = APIRouter(prefix="/v1")

jobs = get_job_repo()
store = FirestoreRepo()

# --------------------------------------------------
# Ingest PDF or Website
# --------------------------------------------------
@router.post("/ingest", status_code=202)
def ingest(req: IngestRequest):
    """
    Ingest a PDF or Website into the system.
    """
    job = jobs.create(req.convId)

    source = {
        "fileUrl": req.fileUrl,
        "storagePath": req.storagePath,
        "fileName": req.fileName,
        "prompt": req.prompt,  # website URL
    }

    if USE_CELERY:
        ingest_pdf.delay(
            job["jobId"],
            req.userId,
            req.convId,
            source
        )
    else:
        ingest_pdf(
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

    if data["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    if data["status"] == "done":
        data["result"] = store.get(data["convId"])

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
