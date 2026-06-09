"""Extract clean text from a résumé PDF.

Primary path is ``pypdf`` (pure-Python, no system deps). If it yields too little
text — common with image-heavy or oddly-encoded PDFs — we lazily try
``pdfplumber`` if it happens to be installed. Whitespace is normalized so the
downstream embedding/LLM steps see clean input.
"""
from __future__ import annotations

import io
import re

MIN_USEFUL_CHARS = 50


class PdfExtractionError(Exception):
    """Raised when no usable text can be extracted from the uploaded file."""


def _clean(text: str) -> str:
    # Normalize newlines, collapse runs of spaces/tabs, and squeeze blank lines.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_with_pypdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages)


def _extract_with_pdfplumber(data: bytes) -> str:
    try:
        import pdfplumber  # optional dependency
    except ImportError:
        return ""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [(page.extract_text() or "") for page in pdf.pages]
    return "\n".join(pages)


def extract_text_from_pdf(data: bytes) -> str:
    """Return cleaned text, or raise PdfExtractionError if the PDF has no text."""
    if not data:
        raise PdfExtractionError("Empty file.")

    try:
        text = _extract_with_pypdf(data)
    except Exception as exc:  # corrupt/encrypted/not-a-PDF
        raise PdfExtractionError(f"Could not read PDF: {exc}") from exc

    if len(_clean(text)) < MIN_USEFUL_CHARS:
        # Fall back to the richer extractor for messy layouts, if available.
        fallback = _extract_with_pdfplumber(data)
        if len(_clean(fallback)) > len(_clean(text)):
            text = fallback

    cleaned = _clean(text)
    if len(cleaned) < MIN_USEFUL_CHARS:
        raise PdfExtractionError(
            "Couldn't extract readable text. If this is a scanned/image PDF, "
            "the résumé needs a text layer (OCR) to be analyzed."
        )
    return cleaned
