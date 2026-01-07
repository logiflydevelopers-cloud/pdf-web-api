from app.workers.celery import celery

from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages
from app.services.html_extractor import extract_web_text

from app.crawlers.site_crawler import crawl_site
from app.crawlers.sitemap_loader import load_sitemap

from app.services.summarizer import summarize, generate_questions
from app.services.embeddings import build_embeddings

from app.repos.redis_jobs import get_job_repo
from app.repos.firestore_repo import FirestoreRepo


# --------------------------------------------------
# Helper: robust PDF detection (Firebase-safe)
# --------------------------------------------------
def detect_pdf(url: str, content_type: str) -> bool:
    if content_type and "application/pdf" in content_type:
        return True

    clean_url = url.lower().split("?")[0]
    return clean_url.endswith(".pdf")


# --------------------------------------------------
# Core ingestion logic
# --------------------------------------------------
def _ingest_logic(
    jobId: str,
    userId: str,
    convId: str,
    source: str,
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

        if not source or not isinstance(source, str):
            raise ValueError("source must be a non-empty string URL")

        url = source.strip()

        # -------------------------
        # FETCH HEAD SOURCE
        # -------------------------
        content, content_type = fetch_source(url)
        is_pdf = detect_pdf(url, content_type)

        # ==================================================
        # PDF INGESTION
        # ==================================================
        if is_pdf:
            jobs.update(jobId, stage="extract", progress=25)

            texts, pages, total_words, ocr_pages = extract_pages(content)

            jobs.update(jobId, stage="embed", progress=55)

            build_embeddings(
                userId=userId,
                convId=convId,
                texts=texts,
                sourceType="pdf",
                pages=list(range(1, pages + 1)),
            )

            jobs.update(jobId, stage="summary", progress=80)

            summary = summarize(
                text="\n".join(texts),
                total_words=total_words,
                sourceType="pdf",
            )

            questions = generate_questions(summary)

            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "pdf",
                "summary": summary,
                "questions": questions,
                "meta": {
                    "url": url,
                    "pages": pages,
                    "totalWords": total_words,
                    "ocrPages": ocr_pages,
                },
                "status": "ready",
            })

        # ==================================================
        # WEB INGESTION
        # ==================================================
        else:
            jobs.update(jobId, stage="scrape", progress=25)

            pages = []
            combined_text = ""

            # -------- SITEMAP MODE --------
            if url.endswith("sitemap.xml"):
                jobs.update(jobId, stage="sitemap", progress=35)

                result = load_sitemap(
                    url,
                    max_pages=40
                )

                combined_text = result["combined_text"]
                pages = result["pages"]

            # -------- CONTROLLED CRAWL MODE --------
            elif "?crawl=true" in url:
                jobs.update(jobId, stage="crawl", progress=35)

                clean_url = url.split("?")[0]

                result = crawl_site(
                    clean_url,
                    max_pages=20,
                    max_depth=2
                )

                combined_text = result["combined_text"]
                pages = result["pages"]

            # -------- SINGLE PAGE MODE --------
            else:
                html = content.decode("utf-8", errors="ignore")
                text = extract_web_text(html)

                combined_text = text
                pages = [{
                    "url": url,
                    "text": text,
                }]

            if not pages or not combined_text.strip():
                raise ValueError("No usable web content extracted")

            total_words = sum(len(p["text"].split()) for p in pages)

            jobs.update(jobId, stage="embed", progress=55)

            # ---- Build embeddings per page (URL preserved) ----
            for idx, page in enumerate(pages):
                build_embeddings(
                    userId=userId,
                    convId=convId,
                    texts=[page["text"]],
                    sourceType="web",
                    url=page["url"],
                    chunkId=f"web-{idx}",
                )

            jobs.update(jobId, stage="summary", progress=80)

            summary = summarize(
                text=combined_text,
                total_words=total_words,
                sourceType="web",
            )

            questions = generate_questions(summary)

            store.save(convId, {
                "userId": userId,
                "convId": convId,
                "sourceType": "web",
                "summary": summary,
                "questions": questions,
                "meta": {
                    "rootUrl": url,
                    "pagesIngested": len(pages),
                    "totalWords": total_words,
                    "pageUrls": [p["url"] for p in pages],
                },
                "status": "ready",
            })


        # -------------------------
        # COMPLETE JOB
        # -------------------------
        jobs.complete(jobId)

    except Exception as e:
        jobs.fail(jobId, str(e))
        try:
            store.fail(convId, str(e))
        except Exception:
            pass
        raise


# --------------------------------------------------
# Celery Task Wrapper
# --------------------------------------------------
@celery.task(bind=True, name="ingest_document")
def ingest_document(self, *args, **kwargs):
    if kwargs:
        return _ingest_logic(
            kwargs["jobId"],
            kwargs["userId"],
            kwargs["convId"],
            kwargs["source"],
        )

    return _ingest_logic(*args)
