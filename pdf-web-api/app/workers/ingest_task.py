from app.workers.celery import celery
from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages
from app.services.web_scrapper import extract_web_text
from app.services.summarizer import summarize
from app.services.embeddings import build_embeddings
from app.repos.redis_jobs import get_job_repo
from app.repos.firestore_repo import FirestoreRepo


def _ingest_logic(
    jobId: str,
    userId: str,
    convId: str,
    source: dict
):
    """
    Core ingestion logic.
    Handles BOTH:
    - PDF ingestion
    - Website scraping

    Can be called:
    - synchronously (local dev)
    - asynchronously via Celery (production)
    """

    jobs = get_job_repo()
    store = FirestoreRepo()

    try:
        # --------------------------------------------------
        # MARK JOB START
        # --------------------------------------------------
        jobs.update(
            jobId,
            status="processing",
            stage="fetch",
            progress=5,
            convId=convId
        )

        # --------------------------------------------------
        # FETCH SOURCE (PDF or WEB)
        # --------------------------------------------------
        raw_bytes = fetch_source(source)

        # --------------------------------------------------
        # DETECT MODE
        # --------------------------------------------------
        is_pdf = (
            source.get("fileUrl", "").lower().endswith(".pdf")
            or source.get("fileName", "").lower().endswith(".pdf")
        )

        # --------------------------------------------------
        # PDF INGESTION
        # --------------------------------------------------
        if is_pdf:
            jobs.update(jobId, stage="extract", progress=25)

            texts, pages, total_words, ocr_pages = extract_pages(raw_bytes)

            jobs.update(jobId, stage="embed", progress=55)

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=texts,
                sourceType="pdf",
                pages=list(range(1, pages + 1))
            )

            jobs.update(jobId, stage="summary", progress=80)

            summary = summarize(
                text="\n".join(texts),
                total_words=total_words,
                sourceType="pdf",
                prompt=source.get("prompt") 
            )

            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "pdf",
                "summary": summary,
                "meta": {
                    "pages": pages,
                    "totalWords": total_words,
                    "ocrPages": ocr_pages
                },
                "status": "ready"
            })

        # --------------------------------------------------
        # WEB INGESTION
        # --------------------------------------------------
        else:
            jobs.update(jobId, stage="scrape", progress=25)

            web_text = extract_web_text(raw_bytes)

            total_words = len(web_text.split())

            jobs.update(jobId, stage="embed", progress=55)

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=[web_text],
                sourceType="web",
                url=source.get("prompt") or source.get("fileUrl")
            )

            jobs.update(jobId, stage="summary", progress=80)

            summary = summarize(
                text=web_text,
                total_words=total_words,
                sourceType="web"
            )

            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "web",
                "summary": summary,
                "meta": {
                    "totalWords": total_words,
                    "url": source.get("prompt") or source.get("fileUrl")
                },
                "status": "ready"
            })

        # --------------------------------------------------
        # COMPLETE JOB
        # --------------------------------------------------
        jobs.complete(jobId)

    except Exception as e:
        jobs.fail(jobId, str(e))
        store.fail(convId, str(e))
        raise


# --------------------------------------------------
# CELERY TASK WRAPPER
# --------------------------------------------------
@celery.task(bind=True, name="ingest_document")
def ingest_document(
    self,
    jobId: str,
    userId: str,
    convId: str,
    source: dict
):
    return _ingest_logic(jobId, userId, convId, source)
