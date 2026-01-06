import requests


def fetch_source(source: dict) -> bytes:
    """
    Fetch raw content from a URL.
    Works for:
    - PDF URLs
    - Website URLs (HTML)

    Returns raw bytes.
    """

    url = source.get("fileUrl") or source.get("prompt")

    if not url:
        raise ValueError("No URL provided in source")

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (PDF-Parser-Bot)"
        }
    )
    response.raise_for_status()
    return response.content
