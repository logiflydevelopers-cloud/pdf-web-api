from app.workers.celery import celery

from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages

from app.crawlers.smart_crawler import smart_crawl

from app.services.summarizer import summarize, generate_questions
from app.services.embeddings import build_embeddings

from app.repos.redis_jobs import get_job_repo
from app.repos.firestore_repo import FirestoreRepo


# --------------------------------------------------
# Helper: robust PDF detection (Firebase-safe)
# (KEPT EXACTLY AS REQUESTED)
# --------------------------------------------------
def detect_pdf(url: str, content_type: str) -> bool:
    if content_type and "application/pdf" in content_type:
        return True

    clean_url = url.lower().split("?")[0]
    return clean_url.endswith(".pdf")


# --------------------------------------------------
# Core ingestion logic (RESTART SAFE)
# --------------------------------------------------
def _ingest_logic(
    jobId: str,
    userId: str,
    convId: str,
    source: str,
    prompt: str | None = None,
):
    jobs = get_job_repo()
    store = FirestoreRepo()

    try:
        # -------------------------
        # START JOB
        # -------------------------
        jobs.update(
            jobId,
            status="processing",
            stage="fetch",
            progress=5,
            convId=convId,
        )

        # 🔒 Persist job immediately (survives restarts)
        store.update(convId, {
            "convId": convId,
            "userId": userId,
            "status": "processing",
            "stage": "fetch",
            "progress": 5,
        })

        if not source or not isinstance(source, str):
            raise ValueError("source must be a valid URL string")

        url = source.strip()
        prompt = prompt.strip() if prompt else None

        # -------------------------
        # FETCH SOURCE (URL ONLY)
        # -------------------------
        content, content_type = fetch_source(url)
        is_pdf = detect_pdf(url, content_type)

        # ==================================================
        # PDF INGESTION
        # ==================================================
        if is_pdf:
            jobs.update(jobId, stage="extract", progress=25)
            store.update(convId, {
                "status": "processing",
                "stage": "extract",
                "progress": 25,
            })

            texts, page_count, total_words, ocr_pages = extract_pages(content)
            final_text = "\n\n".join(texts)

            if prompt:
                final_text = f"{prompt}\n\n{final_text}"

            jobs.update(jobId, stage="embed", progress=55)
            store.update(convId, {
                "status": "processing",
                "stage": "embed",
                "progress": 55,
            })

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=texts,
                sourceType="pdf",
                pages=list(range(1, page_count + 1)),
            )

            jobs.update(jobId, stage="summary", progress=80)
            store.update(convId, {
                "status": "processing",
                "stage": "summary",
                "progress": 80,
            })

            summary = summarize(
                text=final_text,
                total_words=total_words,
                sourceType="pdf",
            )

            questions = generate_questions(summary)

            # ✅ FINAL STATE
            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "pdf",
                "summary": summary,
                "questions": questions,
                "meta": {
                    "url": url,
                    "pages": page_count,
                    "totalWords": total_words,
                    "ocrPages": ocr_pages,
                },
                "status": "ready",
            })

        # ==================================================
        # WEB INGESTION
        # ==================================================
        else:
            jobs.update(jobId, stage="crawl", progress=25)
            store.update(convId, {
                "status": "processing",
                "stage": "crawl",
                "progress": 25,
            })

            pages = smart_crawl(
                url,
                max_pages=100,
                max_depth=5,
            )

            if not pages:
                raise ValueError("No usable web content extracted")

            jobs.update(jobId, stage="embed", progress=60)
            store.update(convId, {
                "status": "processing",
                "stage": "embed",
                "progress": 60,
            })

            combined_texts = []

            for idx, page in enumerate(pages):
                text = page["text"]
                if prompt:
                    text = f"{prompt}\n\n{text}"

                combined_texts.append(text)

                build_embeddings(
                    userId=userId,
                    convId=convId,
                    texts=[text],
                    sourceType="web",
                    url=page["url"],
                    chunkId=f"web-{idx}",
                )

            full_text = "\n\n".join(combined_texts)

            summary = summarize(
                text=full_text,
                total_words=len(full_text.split()),
                sourceType="web",
            )

            questions = generate_questions(summary)

            # ✅ FINAL STATE
            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "web",
                "summary": summary,
                "questions": questions,
                "meta": {
                    "url": url,
                    "pages": len(pages),
                },
                "status": "ready",
            })

        # -------------------------
        # COMPLETE JOB
        # -------------------------
        jobs.complete(jobId)

    except Exception as e:
        jobs.fail(jobId, str(e))

        # 🔒 Persist failure (restart safe)
        store.update(convId, {
            "status": "failed",
            "error": str(e),
        })

        raise


# --------------------------------------------------
# Celery Task Wrapper (SAFE)
# --------------------------------------------------
@celery.task(bind=True, name="ingest_document")
def ingest_document(self, *args, **kwargs):
    if kwargs:
        return _ingest_logic(
            jobId=kwargs["jobId"],
            userId=kwargs["userId"],
            convId=kwargs["convId"],
            source=kwargs["source"],
            prompt=kwargs.get("prompt"),
        )

    return _ingest_logic(*args)
