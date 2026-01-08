from playwright.sync_api import sync_playwright

JS_TIMEOUT = 25_000


def render_js_page(url: str) -> str:
    """
    Returns fully rendered HTML after JS execution.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()
        page.goto(url, timeout=JS_TIMEOUT)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()

    return html
