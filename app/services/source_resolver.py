from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages
from app.services.html_extractor import extract_web_text
from app.services.js_renderer import render_js_page

from app.exceptions.restricted_site import RestrictedWebsiteError


def resolve_source(source_url: str):
    """
    Resolves a SINGLE URL into normalized text.
    (NOT a crawler)

    Returns:
    {
        text: str,
        sourceType: "pdf" | "web",
        pages: Optional[List[int]],
        total_words: int
    }
    """

    # -------------------------
    # SAFETY CHECK
    # -------------------------
    if not source_url or not isinstance(source_url, str):
        raise ValueError("source_url must be a non-empty string")

    source_url = source_url.strip()

    if not source_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL provided: {source_url}")

    # -------------------------
    # FETCH SOURCE (FAST FAIL)
    # -------------------------
    data, content_type = fetch_source(source_url)

    # -------------------------
    # PDF (FAST PATH)
    # -------------------------
    if (
        (content_type and "application/pdf" in content_type)
        or data.startswith(b"%PDF")
    ):
        texts, page_count, total_words, ocr_pages = extract_pages(data)

        return {
            "text": "\n\n".join(texts),
            "sourceType": "pdf",
            "pages": list(range(1, page_count + 1)),
            "total_words": total_words,
        }

    # -------------------------
    # STATIC HTML (FAST)
    # -------------------------
    html = data.decode("utf-8", errors="ignore")

    try:
        text = extract_web_text(html)
        if text and len(text.split()) > 200:
            return {
                "text": text,
                "sourceType": "web",
                "pages": None,
                "total_words": len(text.split()),
            }
    except Exception:
        pass

    # -------------------------
    # JS RENDER (ONLY IF NEEDED)
    # -------------------------
    try:
        rendered_html = render_js_page(source_url)
        text = extract_web_text(rendered_html)

        if text and len(text.split()) > 200:
            return {
                "text": text,
                "sourceType": "web",
                "pages": None,
                "total_words": len(text.split()),
            }
    except RestrictedWebsiteError:
        raise

    except Exception as e:
        raise RuntimeError(
            f"Unable to extract usable content from URL: {source_url}\n"
            f"Reason: {str(e)}"
        )

    # -------------------------
    # FINAL FAIL
    # -------------------------
    raise RuntimeError(
        f"Website returned no meaningful content: {source_url}"
    )
