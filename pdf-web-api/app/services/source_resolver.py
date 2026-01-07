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
        pages: Optional[List[int]]
    }
    """

    data, content_type = fetch_source(source_url)

    # -------------------------
    # TIER 3: PDF
    # -------------------------
    if "application/pdf" in content_type or data.startswith(b"%PDF"):
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
        return {
            "text": text,
            "sourceType": "web",
            "pages": None,
            "total_words": len(text.split())
        }
    except Exception:
        pass

    # -------------------------
    # TIER 2: JS Rendering
    # -------------------------
    try:
        html = render_js_page(source_url)
        text = extract_web_text(html)
        return {
            "text": text,
            "sourceType": "web",
            "pages": None,
            "total_words": len(text.split())
        }
    except Exception:
        pass

    # -------------------------
    # TIER 4: DOM Fallback
    # -------------------------
    text = extract_dom_text(source_url)
    return {
        "text": text,
        "sourceType": "web",
        "pages": None,
        "total_words": len(text.split())
    }
