from bs4 import BeautifulSoup
import re

MIN_TEXT_LENGTH = 500


def extract_web_text(html: str) -> str:
    if not html or len(html.strip()) < 200:
        raise ValueError("HTML too short")

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup([
        "script", "style", "noscript", "iframe", "svg",
        "header", "footer", "nav", "aside", "form", "button"
    ]):
        tag.decompose()

    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find("section")
        or soup.body
    )

    if not main:
        raise ValueError("No meaningful content")

    blocks = []
    for el in main.find_all(["p", "li", "h1", "h2", "h3"]):
        txt = el.get_text(" ", strip=True)
        if len(txt) >= 40:
            blocks.append(txt)

    text = "\n".join(blocks)
    text = clean_text(text)

    if len(text) < MIN_TEXT_LENGTH:
        raise ValueError("Content too short")

    return text


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
