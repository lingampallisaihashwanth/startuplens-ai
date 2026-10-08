import io
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class DocumentError(Exception):
    """Base exception for document operations."""
    pass


class DocumentValidationError(DocumentError):
    """Raised when uploaded file fails validation (size, extension, empty)."""
    pass


class DocumentParseError(DocumentError):
    """Raised when file parsing fails."""
    pass


class DocumentService:
    """Service to parse, validate, and normalize attached research documents."""

    def validate_file(self, filename: str, file_bytes: bytes) -> str:
        """Validate filename extension and file size. Returns normalized extension without dot."""
        if not filename or "." not in filename:
            raise DocumentValidationError("Invalid filename: missing extension.")

        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise DocumentValidationError(f"Unsupported file type '{ext}'. Supported formats: {allowed}.")

        if not file_bytes or len(file_bytes.strip()) == 0:
            raise DocumentValidationError("File is empty.")

        if len(file_bytes) > MAX_FILE_SIZE:
            max_mb = MAX_FILE_SIZE // (1024 * 1024)
            raise DocumentValidationError(f"File size exceeds maximum limit of {max_mb}MB.")

        return ext.lstrip(".")

    def parse_document(self, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Validate and parse document bytes into structured metadata and sections.
        Returns document dict with id, filename, file_type, file_size, content_text, sections, created_at.
        """
        file_type = self.validate_file(filename, file_bytes)
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            if file_type == "pdf":
                sections, full_text = self._parse_pdf(file_bytes)
            elif file_type == "docx":
                sections, full_text = self._parse_docx(file_bytes)
            elif file_type in ("txt", "md"):
                sections, full_text = self._parse_text(file_bytes)
            else:
                raise DocumentValidationError(f"Unsupported file type: {file_type}")
        except DocumentValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse document '{filename}': {e}", exc_info=True)
            raise DocumentParseError(f"Could not parse document '{filename}': {str(e)}")

        if not full_text.strip():
            raise DocumentValidationError(f"Document '{filename}' contains no readable text.")

        return {
            "id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": len(file_bytes),
            "content_text": full_text,
            "sections": sections,
            "created_at": now_iso,
        }

    def _parse_pdf(self, file_bytes: bytes) -> Tuple[List[Dict[str, str]], str]:
        if PdfReader is None:
            raise DocumentParseError("PDF parsing library (pypdf) is not available.")

        reader = PdfReader(io.BytesIO(file_bytes))
        sections: List[Dict[str, str]] = []
        full_text_parts: List[str] = []

        if len(reader.pages) == 0:
            raise DocumentValidationError("PDF file has 0 pages.")

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            text = (page.extract_text() or "").strip()
            if text:
                sections.append({"page_or_section": f"p. {page_num}", "text": text})
                full_text_parts.append(f"[Page {page_num}]\n{text}")

        return sections, "\n\n".join(full_text_parts)

    def _parse_docx(self, file_bytes: bytes) -> Tuple[List[Dict[str, str]], str]:
        if docx is None:
            raise DocumentParseError("DOCX parsing library (python-docx) is not available.")

        doc = docx.Document(io.BytesIO(file_bytes))
        sections: List[Dict[str, str]] = []
        full_text_parts: List[str] = []

        current_heading = "Introduction"
        current_paragraphs: List[str] = []
        section_idx = 1

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            if p.style and p.style.name and p.style.name.startswith("Heading"):
                if current_paragraphs:
                    sec_text = "\n".join(current_paragraphs)
                    sections.append({"page_or_section": f"Section {section_idx}: {current_heading}", "text": sec_text})
                    full_text_parts.append(sec_text)
                    section_idx += 1
                    current_paragraphs = []
                current_heading = text
            else:
                current_paragraphs.append(text)

        if current_paragraphs:
            sec_text = "\n".join(current_paragraphs)
            sections.append({"page_or_section": f"Section {section_idx}: {current_heading}", "text": sec_text})
            full_text_parts.append(sec_text)

        # Fallback if no sections formed
        if not sections and full_text_parts:
            sections.append({"page_or_section": "Document Body", "text": "\n".join(full_text_parts)})

        return sections, "\n\n".join(full_text_parts)

    def _parse_text(self, file_bytes: bytes) -> Tuple[List[Dict[str, str]], str]:
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = file_bytes.decode("latin-1", errors="replace")

        lines = content.splitlines()
        sections: List[Dict[str, str]] = []
        full_text_parts: List[str] = []

        current_title = "Section 1"
        current_lines: List[str] = []
        sec_num = 1

        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("#"):
                if current_lines:
                    sec_text = "\n".join(current_lines).strip()
                    if sec_text:
                        sections.append({"page_or_section": current_title, "text": sec_text})
                        full_text_parts.append(sec_text)
                        sec_num += 1
                        current_lines = []
                current_title = trimmed.lstrip("#").strip() or f"Section {sec_num}"
            else:
                current_lines.append(line)

        if current_lines:
            sec_text = "\n".join(current_lines).strip()
            if sec_text:
                sections.append({"page_or_section": current_title, "text": sec_text})
                full_text_parts.append(sec_text)

        if not sections and content.strip():
            sections.append({"page_or_section": "Paragraph 1", "text": content.strip()})
            full_text_parts = [content.strip()]

        return sections, "\n\n".join(full_text_parts)


document_service = DocumentService()
