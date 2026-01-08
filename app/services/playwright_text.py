from playwright.sync_api import sync_playwright


def extract_dom_text(url: str) -> str:
    """
    Last-resort fallback.
    Extracts visible DOM text only.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()
        page.goto(url, timeout=30_000)
        page.wait_for_load_state("networkidle")

        text = page.evaluate("""
            () => document.body.innerText || ""
        """)

        browser.close()

    if not text or len(text.strip()) < 500:
        raise ValueError("DOM text too short")

    return text.strip()
