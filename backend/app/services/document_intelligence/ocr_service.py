import logging
from io import BytesIO
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.models.document_version import DocumentFile
from app.services.document_storage_service import get_document_file_content


logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    text: str = ""
    page_count: int = 0
    char_count: int = 0
    engine: str = "none"
    status: str = "unsupported"
    error_message: Optional[str] = None


def extract_text_from_document_file(
    db,
    document_file: DocumentFile,
    max_pages: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> OCRResult:
    if not settings.DOCUMENT_OCR_ENABLED:
        return OCRResult(status="unsupported", error_message="Document OCR is disabled")
    max_pages = max_pages or settings.DOCUMENT_OCR_MAX_PAGES
    max_chars = max_chars or settings.DOCUMENT_OCR_MAX_CHARS
    try:
        content = get_document_file_content(db, document_file.id)
    except Exception as exc:
        logger.exception("Unable to read document file for OCR file_id=%s", document_file.id)
        return OCRResult(status="failed", error_message=str(exc))

    content_type = (document_file.content_type or "").lower()
    filename = (document_file.sanitized_filename or "").lower()
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return extract_text_from_pdf_bytes(content, max_pages, max_chars)
    if (
        content_type.startswith("text/")
        or content_type in {"application/csv", "text/csv"}
        or filename.endswith((".txt", ".csv"))
    ):
        return extract_text_from_text_bytes(content, max_chars)
    if content_type.startswith("image/") or filename.endswith((".png", ".jpg", ".jpeg")):
        return extract_text_from_image_bytes(content, max_chars)
    return OCRResult(status="unsupported", error_message=f"OCR unsupported for {content_type or 'unknown type'}")


def extract_text_from_pdf_bytes(content_bytes: bytes, max_pages: int, max_chars: int) -> OCRResult:
    try:
        from pypdf import PdfReader
    except Exception:
        return OCRResult(
            status="unsupported",
            engine="pypdf-unavailable",
            error_message="PDF text extraction requires pypdf",
        )
    try:
        reader = PdfReader(BytesIO(content_bytes))
        pages = reader.pages[: max(max_pages, 1)]
        chunks = []
        for page in pages:
            chunks.append(page.extract_text() or "")
            if sum(len(chunk) for chunk in chunks) >= max_chars:
                break
        text = _limit_text("\n".join(chunks), max_chars)
        if not text.strip():
            return OCRResult(
                text="",
                page_count=len(pages),
                char_count=0,
                engine="pypdf",
                status="unsupported",
                error_message="No embedded PDF text found",
            )
        return OCRResult(text=text, page_count=len(pages), char_count=len(text), engine="pypdf", status="completed")
    except Exception as exc:
        logger.exception("PDF text extraction failed")
        return OCRResult(status="failed", engine="pypdf", error_message=str(exc))


def extract_text_from_text_bytes(content_bytes: bytes, max_chars: int) -> OCRResult:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            text = content_bytes.decode(encoding)
            text = _limit_text(text, max_chars)
            return OCRResult(text=text, page_count=1, char_count=len(text), engine=f"text-{encoding}", status="completed")
        except UnicodeDecodeError:
            continue
    return OCRResult(status="failed", engine="text", error_message="Unable to decode text document")


def extract_text_from_image_bytes(content_bytes: bytes, max_chars: int) -> OCRResult:
    if not settings.DOCUMENT_OCR_IMAGE_ENABLED:
        return OCRResult(status="unsupported", engine="image-disabled", error_message="Image OCR is disabled")
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return OCRResult(status="unsupported", engine="tesseract-unavailable", error_message="Image OCR engine unavailable")
    try:
        image = Image.open(BytesIO(content_bytes))
        text = _limit_text(pytesseract.image_to_string(image), max_chars)
        return OCRResult(text=text, page_count=1, char_count=len(text), engine="tesseract", status="completed")
    except Exception as exc:
        logger.exception("Image OCR failed")
        return OCRResult(status="failed", engine="tesseract", error_message=str(exc))


def _limit_text(text: str, max_chars: int) -> str:
    return (text or "")[: max(max_chars, 0)]
