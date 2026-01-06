import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 25
MIN_TEXT_LENGTH = 500


def extract_web_text(url: str) -> str:
    """
    Scrape readable text from a website.
    Removes scripts, styles, nav, footer, etc.
    """

    if not url.startswith("http"):
        raise ValueError("Invalid URL")

    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --------------------------------------------------
    # REMOVE NOISE
    # --------------------------------------------------
    for tag in soup([
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "header",
        "footer",
        "nav",
        "aside",
        "form",
        "button",
    ]):
        tag.decompose()

    # --------------------------------------------------
    # PRIORITY CONTENT SELECTION
    # --------------------------------------------------
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find("section")
        or soup.body
    )

    if not main:
        raise ValueError("Unable to extract meaningful content")

    # --------------------------------------------------
    # TEXT EXTRACTION
    # --------------------------------------------------
    text_blocks = []

    for el in main.find_all(["p", "li", "h1", "h2", "h3"]):
        txt = el.get_text(" ", strip=True)
        if len(txt) >= 40:
            text_blocks.append(txt)

    text = "\n".join(text_blocks)

    # --------------------------------------------------
    # CLEANUP
    # --------------------------------------------------
    text = clean_text(text)

    if len(text) < MIN_TEXT_LENGTH:
        raise ValueError("Extracted content too short")

    return text


def clean_text(text: str) -> str:
    """
    Normalize whitespace & remove junk.
    """
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
