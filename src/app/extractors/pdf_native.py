import io

from pdf2image import convert_from_bytes
from pypdf import PdfReader

from .base import ExtractedDocument, ExtractorBase
from .quality import compute_extraction_quality


def _render_first_page_png(pdf_bytes: bytes, dpi: int = 150) -> bytes:
    """Renderiza a primeira página do PDF como PNG (para CLIP)."""
    images = convert_from_bytes(pdf_bytes, dpi=dpi, first_page=1, last_page=1)
    if not images:
        # PDF sem páginas renderizáveis — retorna PNG de 1x1 transparente
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
        return buf.getvalue()
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return buf.getvalue()


class PdfNativeExtractor(ExtractorBase):
    """Extrai texto via pypdf; renderiza imagem via pdf2image."""

    def extract(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = len(reader.pages)
        text_parts: list[str] = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            text_parts.append(page_text)
        text = "\n".join(text_parts).strip()
        first_page_png = _render_first_page_png(file_bytes)
        quality = compute_extraction_quality(text, pages)
        return ExtractedDocument(
            text=text,
            pages=pages,
            mode="pdf_native",
            extraction_quality=quality,
            first_page_image_png=first_page_png,
            metadata={"mime": mime, "extractor": "pypdf"},
        )
