from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.services.source_fetcher import fetch_source
from app.services.html_extractor import extract_web_text


def crawl_site(
    start_url: str,
    *,
    max_pages: int = 20,
    max_depth: int = 2,
):
    base_domain = urlparse(start_url).netloc

    visited = set()
    to_visit = [(start_url, 0)]

    pages = []

    while to_visit and len(pages) < max_pages:
        url, depth = to_visit.pop(0)

        if url in visited or depth > max_depth:
            continue

        visited.add(url)

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

            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                link = urljoin(url, a["href"])
                parsed = urlparse(link)

                if parsed.netloc == base_domain:
                    to_visit.append((link, depth + 1))

        except Exception:
            continue

    return {
        "combined_text": "\n\n".join(p["text"] for p in pages),
        "pages": pages,
    }
