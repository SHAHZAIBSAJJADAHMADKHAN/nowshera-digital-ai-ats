"""Trusted, bounded PDF text extraction for private candidate CV objects."""

from io import BytesIO

from pypdf import PdfReader

from app.services.candidate_cvs import MAX_CV_BYTES


class PDFExtractionError(Exception):
    """A controlled extraction failure; no provider call should follow."""


def extract_pdf_text(content: bytes) -> str:
    if not content or len(content) > MAX_CV_BYTES or not content.startswith(b"%PDF-"):
        raise PDFExtractionError("CV PDF is invalid")
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as error:  # pypdf exposes several parser-specific error classes.
        raise PDFExtractionError("CV PDF cannot be read") from error
    if not text:
        raise PDFExtractionError("CV PDF contains no extractable text")
    return text
