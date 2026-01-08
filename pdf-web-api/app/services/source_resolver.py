from app.services.source_fetcher import fetch_source
from app.services.pdf_extractor import extract_pages
from app.services.html_extractor import extract_web_text
from app.services.js_renderer import render_js_page
from app.services.playwright_text import extract_dom_text


def resolve_source(source_url: str):
    """
    Resolves a URL into normalized text.

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
    # FETCH SOURCE
    # -------------------------
    data, content_type = fetch_source(source_url)

    # -------------------------
    # TIER 3: PDF
    # -------------------------
    if content_type and "application/pdf" in content_type or data.startswith(b"%PDF"):
        texts, page_count, total_words, ocr_pages = extract_pages(data)

        return {
            "text": "\n\n".join(texts),
            "sourceType": "pdf",
            "pages": list(range(1, page_count + 1)),
            "total_words": total_words
        }

    html = data.decode("utf-8", errors="ignore")

    # -------------------------
    # TIER 1: Static HTML
    # -------------------------
    try:
        text = extract_web_text(html)
        if text and text.strip():
            return {
                "text": text,
                "sourceType": "web",
                "pages": None,
                "total_words": len(text.split())
            }
    except Exception as e:
        tier1_error = str(e)

    # -------------------------
    # TIER 2: JS Rendering
    # -------------------------
    try:
        rendered_html = render_js_page(source_url)
        text = extract_web_text(rendered_html)

        if text and text.strip():
            return {
                "text": text,
                "sourceType": "web",
                "pages": None,
                "total_words": len(text.split())
            }
    except Exception as e:
        tier2_error = str(e)

    # -------------------------
    # TIER 4: DOM Fallback (LAST RESORT)
    # -------------------------
    try:
        text = extract_dom_text(source_url)

        if not text or not text.strip():
            raise RuntimeError("DOM extraction returned empty text")

        return {
            "text": text,
            "sourceType": "web",
            "pages": None,
            "total_words": len(text.split())
        }
    except Exception as e:
        raise RuntimeError(
            f"Failed to resolve web source.\n"
            f"TIER1 error: {tier1_error if 'tier1_error' in locals() else 'N/A'}\n"
            f"TIER2 error: {tier2_error if 'tier2_error' in locals() else 'N/A'}\n"
            f"TIER4 error: {str(e)}"
        )
