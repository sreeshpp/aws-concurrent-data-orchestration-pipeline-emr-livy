"""Resume text extraction from common file formats."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".text"}


def parse_resume(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a resume file."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if suffix == ".pdf":
        return _parse_pdf(file_bytes)
    return file_bytes.decode("utf-8", errors="replace").strip()


def _parse_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("Install pypdf to parse PDF resumes: pip install pypdf") from exc

    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())
    text = "\n\n".join(part for part in pages if part)
    if not text.strip():
        raise ValueError("Could not extract text from the PDF. Try a text-based PDF export.")
    return text.strip()
