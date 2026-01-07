import time
import random
import re
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse, urljoin, urldefrag
from collections import deque

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

from app.services.js_renderer import render_js_page


# =========================
# Crawler Defaults
# =========================
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120 Safari/537.36"
)

MAX_PAGES = 40
MAX_DEPTH = 2
MIN_TEXT_LEN = 120
POLITE_DELAY_SEC = 0.25

USE_SITEMAP = True
USE_COMMON_ROUTES = True

SKIP_EXTENSIONS = (
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav",
    ".css", ".js", ".json"
)

COMMON_PATHS = [
    "/about", "/about-us", "/company", "/team",
    "/contact", "/contact-us", "/support",
    "/pricing", "/plans",
    "/services", "/products", "/features",
    "/faq", "/docs", "/blog"
]


# =========================
# URL helpers
# =========================
def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    url, _ = urldefrag(url)
    return url.rstrip("/")


def base_origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def same_domain(root_url: str, other_url: str) -> bool:
    return urlparse(root_url).hostname == urlparse(other_url).hostname


def should_skip_url(url: str) -> bool:
    return any(url.lower().endswith(ext) for ext in SKIP_EXTENSIONS)


# =========================
# HTML extraction helpers
# =========================
def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def extract_main_text(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    for tag in soup(["header", "footer", "nav", "aside"]):
        tag.decompose()

    title = clean_text(soup.title.get_text(" ")) if soup.title else ""

    main = soup.find("main") or soup.find("article")
    if main:
        text = clean_text(main.get_text(" "))
    else:
        text = clean_text(soup.get_text(" "))

    return title, text


def extract_links(current_url: str, html: str, root_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        abs_url = normalize_url(urljoin(current_url, href))
        if (
            abs_url.startswith(("http://", "https://"))
            and same_domain(root_url, abs_url)
            and not should_skip_url(abs_url)
        ):
            links.add(abs_url)

    return list(links)


def looks_like_js_shell(html: str) -> bool:
    if not html or len(html) < 2000:
        return True

    markers = ["id=\"root\"", "id=\"app\"", "__next", "react", "vite", "webpack"]
    score = sum(m in html.lower() for m in markers)

    soup = BeautifulSoup(html, "html.parser")
    body_text = clean_text(
        soup.body.get_text(" ") if soup.body else soup.get_text(" ")
    )

    return score >= 2 or len(body_text) < 200


# =========================
# Fetch HTML
# =========================
def fetch_html_requests(url: str, timeout: int = 20) -> Optional[str]:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        if r.status_code != 200:
            return None
        return r.text or ""
    except Exception:
        return None


def fetch_html(url: str) -> Optional[str]:
    html = fetch_html_requests(url)
    if html and not looks_like_js_shell(html):
        return html

    # JS-render fallback
    try:
        return render_js_page(url)
    except Exception:
        return html


# =========================
# Sitemap helpers
# =========================
def parse_sitemap(xml_text: str, root_url: str, limit: int = 300) -> List[str]:
    urls = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            if elem.tag.lower().endswith("loc"):
                u = normalize_url(elem.text or "")
                if same_domain(root_url, u) and not should_skip_url(u):
                    urls.append(u)
    except Exception:
        pass

    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= limit:
            break
    return out


def load_sitemap_urls(root_url: str) -> List[str]:
    base = base_origin(root_url)
    sitemap_urls = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
    ]

    found = []
    for sm in sitemap_urls:
        try:
            r = requests.get(sm, headers={"User-Agent": USER_AGENT}, timeout=15)
            if r.status_code == 200 and r.text.strip().startswith("<"):
                found.extend(parse_sitemap(r.text, root_url))
        except Exception:
            pass

    return found


# =========================
# SMART CRAWLER (MAIN)
# =========================
def smart_crawl(
    root_url: str,
    max_pages: int = MAX_PAGES,
    max_depth: int = MAX_DEPTH,
) -> List[Dict[str, str]]:
    root_url = normalize_url(root_url)
    origin = base_origin(root_url)

    visited = set()
    pages: List[Dict[str, str]] = []

    # -------- Seed URLs --------
    seeds = [root_url]

    if USE_COMMON_ROUTES:
        for p in COMMON_PATHS:
            seeds.append(normalize_url(origin + p))

    if USE_SITEMAP:
        seeds.extend(load_sitemap_urls(root_url))

    queue = deque((u, 0) for u in seeds if u)

    # -------- Crawl --------
    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue

        visited.add(url)

        html = fetch_html(url)
        if not html:
            continue

        title, text = extract_main_text(html)
        if len(text) < MIN_TEXT_LEN:
            continue

        pages.append({
            "url": url,
            "title": title,
            "text": text,
        })

        if depth < max_depth:
            links = extract_links(url, html, root_url)
            random.shuffle(links)
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1))

        time.sleep(POLITE_DELAY_SEC)

    return pages
