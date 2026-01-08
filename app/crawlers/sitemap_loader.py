import xml.etree.ElementTree as ET
from app.services.source_fetcher import fetch_source
from app.services.html_extractor import extract_web_text


def load_sitemap(
    sitemap_url: str,
    *,
    max_pages: int = 20,
):
    content, _ = fetch_source(sitemap_url)
    root = ET.fromstring(content)

    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = [
        loc.text.strip()
        for loc in root.findall(".//ns:loc", ns)
    ][:max_pages]

    pages = []

    for url in urls:
        try:
            html, content_type = fetch_source(url)
            if "text/html" not in content_type:
                continue

            html = html.decode("utf-8", errors="ignore")
            text = extract_web_text(html)

            pages.append({
                "url": url,
                "text": text,
            })

        except Exception:
            continue

    return {
        "combined_text": "\n\n".join(p["text"] for p in pages),
        "pages": pages,
    }
