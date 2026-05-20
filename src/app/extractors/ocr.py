import io
import threading
from typing import Any

from pdf2image import convert_from_bytes
from PIL import Image

from ..utils.logging import logger
from .base import ExtractedDocument, ExtractorBase
from .quality import compute_extraction_quality

# Singleton lazy do PaddleOCR — inicializa uma vez, reutiliza
_ocr_lock = threading.Lock()
_ocr_instance: Any | None = None


def _get_paddleocr() -> Any:
    global _ocr_instance
    if _ocr_instance is None:
        with _ocr_lock:
            if _ocr_instance is None:
                from paddleocr import PaddleOCR
                logger.info("paddleocr.init", lang="pt")
                _ocr_instance = PaddleOCR(lang="pt")
                logger.info("paddleocr.ready")
    return _ocr_instance


def _ocr_image_bytes(image: Image.Image) -> str:
    """Roda OCR numa imagem PIL e retorna texto concatenado."""
    import numpy as np
    ocr = _get_paddleocr()
    arr = np.array(image.convert("RGB"))
    # PaddleOCR v3+ retorna lista de resultados estruturados
    result = ocr.predict(arr)
    if not result:
        return ""
    lines: list[str] = []
    for page_result in result:
        # Estrutura v3+: page_result tem 'rec_texts' (lista) e 'rec_scores'
        rec_texts = (
            page_result.get("rec_texts")
            if isinstance(page_result, dict)
            else getattr(page_result, "rec_texts", None)
        )
        if rec_texts:
            lines.extend(str(t) for t in rec_texts)
    return "\n".join(lines)


def _png_bytes_of(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class OcrExtractor(ExtractorBase):
    """Extrai texto via PaddleOCR; processa PDFs ou imagens diretas."""

    def extract(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        if mime == "application/pdf":
            return self._extract_pdf(file_bytes, mime)
        else:
            return self._extract_image(file_bytes, mime)

    def _extract_pdf(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        logger.info("ocr.pdf_render_start", dpi=130)
        images = convert_from_bytes(file_bytes, dpi=130)
        pages = len(images)
        logger.info("ocr.pdf_rendered", pages=pages)
        text_parts: list[str] = []
        for idx, img in enumerate(images):
            logger.info("ocr.page_start", page=idx + 1, total=pages, size=img.size)
            text_parts.append(_ocr_image_bytes(img))
            logger.info("ocr.page_done", page=idx + 1)
        text = "\n".join(text_parts).strip()
        first_page_png = _png_bytes_of(images[0]) if images else b""
        quality = compute_extraction_quality(text, pages)
        return ExtractedDocument(
            text=text,
            pages=pages,
            mode="ocr",
            extraction_quality=quality,
            first_page_image_png=first_page_png,
            metadata={"mime": mime, "extractor": "paddleocr"},
        )

    def _extract_image(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        logger.info("ocr.image_start", size=image.size)
        text = _ocr_image_bytes(image)
        logger.info("ocr.image_done", chars=len(text))
        first_page_png = _png_bytes_of(image)
        quality = compute_extraction_quality(text, pages=1)
        return ExtractedDocument(
            text=text,
            pages=1,
            mode="image_direct",
            extraction_quality=quality,
            first_page_image_png=first_page_png,
            metadata={"mime": mime, "extractor": "paddleocr"},
        )
