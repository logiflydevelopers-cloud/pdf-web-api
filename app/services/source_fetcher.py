import requests
from typing import Tuple

from app.exceptions.restricted_site import RestrictedWebsiteError


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

    Raises:
    - RestrictedWebsiteError
    - ValueError
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string URL")

    try:
        resp = requests.get(
            source.strip(),
            timeout=10,               # ⬅️ FAST FAIL
            allow_redirects=True,
            headers=HEADERS,
        )

        status = resp.status_code

        # 🚫 Explicitly blocked or restricted sites
        if status in (403, 404, 429):
            raise RestrictedWebsiteError(
                source,
                reason=f"Website blocked automated access (HTTP {status})"
            )

        # ❌ Any other non-200
        if status != 200:
            raise ValueError(f"Failed to fetch URL (HTTP {status})")

        content_type = resp.headers.get("Content-Type", "").lower()
        return resp.content, content_type

    except RestrictedWebsiteError:
        raise

    except requests.exceptions.Timeout:
        raise ValueError("Request timed out while fetching URL")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error while fetching URL: {str(e)}")
