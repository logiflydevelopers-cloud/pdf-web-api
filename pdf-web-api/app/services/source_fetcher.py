import requests


def fetch_source(source: str) -> bytes:
    """
    Fetch raw content from a URL.
    SOURCE MUST BE A STRING.

    Works for:
    - PDF URLs
    - Website URLs (HTML)

    Returns raw bytes.
    """

    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string URL")

    response = requests.get(
        source,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (PDF-Web-Parser-Bot)"
        }
    )

    response.raise_for_status()
    return response.content
