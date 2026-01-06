from app.workers.celery import celery
from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages
from app.services.web_scrapper import extract_web_text
from app.services.summarizer import summarize, generate_questions
from app.services.embeddings import build_embeddings
from app.repos.redis_jobs import get_job_repo
from app.repos.firestore_repo import FirestoreRepo


def _ingest_logic(
    jobId: str,
    userId: str,
    convId: str,
    source: dict
):
    jobs = get_job_repo()
    store = FirestoreRepo()

    try:
        # -------------------------
        # START
        # -------------------------
        jobs.update(
            jobId,
            status="processing",
            stage="fetch",
            progress=5,
            convId=convId
        )

        file_url = source.get("fileUrl")
        file_name = source.get("fileName", "")
        prompt = source.get("prompt")

        is_pdf = (
            (file_url and file_url.lower().endswith(".pdf")) or
            (file_name and file_name.lower().endswith(".pdf"))
        )

        # ==================================================
        # PDF INGESTION
        # ==================================================
        if is_pdf:
            jobs.update(jobId, stage="download", progress=15)

            pdf_bytes = fetch_source(file_url)

            jobs.update(jobId, stage="extract", progress=30)

            texts, pages, total_words, ocr_pages = extract_pages(pdf_bytes)

            jobs.update(jobId, stage="embed", progress=55)

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=texts,
                sourceType="pdf",
                metadata={
                    "pages": list(range(1, pages + 1))
                }
            )

            jobs.update(jobId, stage="summary", progress=80)

            summary = summarize(
                text="\n".join(texts),
                total_words=total_words,
                sourceType="pdf",
                prompt=prompt
            )

            questions = generate_questions(summary)

            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "pdf",
                "summary": summary,
                "questions": questions,
                "meta": {
                    "pages": pages,
                    "totalWords": total_words,
                    "ocrPages": ocr_pages
                },
                "status": "ready"
            })

        # ==================================================
        # WEB INGESTION
        # ==================================================
        else:
            jobs.update(jobId, stage="scrape", progress=25)

            web_text = extract_web_text(file_url)

            total_words = len(web_text.split())

            jobs.update(jobId, stage="embed", progress=55)

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=[web_text],
                sourceType="web",
                metadata={
                    "url": file_url
                }
            )

            jobs.update(jobId, stage="summary", progress=80)

            summary = summarize(
                text=web_text,
                total_words=total_words,
                sourceType="web",
                prompt=prompt
            )

            questions = generate_questions(summary)

            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "web",
                "summary": summary,
                "questions": questions,
                "meta": {
                    "url": file_url,
                    "totalWords": total_words
                },
                "status": "ready"
            })

        # -------------------------
        # DONE
        # -------------------------
        jobs.complete(jobId)

    except Exception as e:
        jobs.fail(jobId, str(e))
        store.fail(convId, str(e))
        raise


# --------------------------------------------------
# CELERY TASK
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

