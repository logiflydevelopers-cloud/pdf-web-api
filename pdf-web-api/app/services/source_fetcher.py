# app/repos/source_fetcher.py
import requests
from typing import Tuple

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def fetch_source(source: str) -> Tuple[bytes, str]:
    """
    Fetch raw content from a URL.

    Returns:
    - content bytes
    - content_type (from HTTP headers)
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string URL")

    resp = requests.get(
        source,
        timeout=30,
        allow_redirects=True,
        headers=HEADERS
    )

    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "").lower()
    return resp.content, content_type
