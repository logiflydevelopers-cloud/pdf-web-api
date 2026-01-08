# app/repos/pdf_extractor.py
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
import tempfile
import os
from typing import List, Tuple


OCR_ENABLE = os.getenv("OCR_ENABLE", "true").lower() == "true"
OCR_MIN_TEXT_CHARS = int(os.getenv("OCR_MIN_TEXT_CHARS", 80))
OCR_DPI = int(os.getenv("OCR_DPI", 220))
OCR_LANG = os.getenv("OCR_LANG", "eng")


def extract_pages(pdf_bytes: bytes) -> Tuple[List[str], int, int, List[int]]:
    """
    Extract text from PDF pages.
    OCR fallback if text is too small.

    Returns:
    - page_texts
    - page_count
    - total_words
    - ocr_pages
    """

    texts: List[str] = []
    ocr_pages: List[int] = []

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_bytes)
        pdf_path = f.name

    try:
        reader = PdfReader(pdf_path)
        pages = len(reader.pages)

        for i, page in enumerate(reader.pages):
            page_num = i + 1

            try:
                raw = (page.extract_text() or "").strip()
            except Exception:
                raw = ""

            needs_ocr = (
                OCR_ENABLE
                and len(raw) < OCR_MIN_TEXT_CHARS
            )

            if needs_ocr:
                try:
                    images = convert_from_path(
                        pdf_path,
                        dpi=OCR_DPI,
                        first_page=page_num,
                        last_page=page_num,
                    )
                    ocr_text = pytesseract.image_to_string(
                        images[0],
                        lang=OCR_LANG
                    ).strip()

                    if len(ocr_text) > len(raw):
                        raw = ocr_text
                        ocr_pages.append(page_num)
                except Exception:
                    pass

            texts.append(raw)

        full_text = "\n\n".join(t for t in texts if t.strip())
        total_words = len(full_text.split())

        return texts, pages, total_words, ocr_pages

    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
