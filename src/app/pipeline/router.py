from ..extractors import (
    ExtractedDocument,
    ImageExtractor,
    OcrExtractor,
    PdfNativeExtractor,
)
from ..utils.logging import logger

# Limite mínimo de caracteres para considerar extração nativa válida.
# Abaixo disso, assumimos PDF escaneado e caímos pra OCR.
MIN_CHARS_FOR_NATIVE_PDF = 50


class DocumentRouter:
    """Decide qual extractor usar conforme MIME e qualidade da extração."""

    def __init__(self) -> None:
        self._pdf_native = PdfNativeExtractor()
        self._ocr = OcrExtractor()
        self._image = ImageExtractor()

    def extract(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        """Retorna o ExtractedDocument escolhido pelo melhor caminho."""
        mime = (mime or "").lower()

        if mime == "application/pdf":
            return self._extract_pdf(file_bytes, mime)
        if mime.startswith("image/"):
            logger.debug("router.image", mime=mime)
            return self._image.extract(file_bytes, mime)

        # Fallback defensivo: trata como imagem
        logger.warning("router.unknown_mime", mime=mime, fallback="image")
        return self._image.extract(file_bytes, mime or "image/octet-stream")

    def _extract_pdf(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        """Tenta extração nativa via pypdf; se texto insuficiente, cai pra OCR."""
        native = self._pdf_native.extract(file_bytes, mime)
        if len(native.text) >= MIN_CHARS_FOR_NATIVE_PDF:
            logger.debug(
                "router.pdf_native",
                chars=len(native.text),
                quality=round(native.extraction_quality, 3),
            )
            return native

        logger.info(
            "router.pdf_fallback_ocr",
            native_chars=len(native.text),
            reason="text_too_short_for_native",
        )
        ocr_result = self._ocr.extract(file_bytes, mime)
        # Preservamos a imagem da primeira página vinda do native
        # (já renderizada) para evitar re-render se for igual.
        return ExtractedDocument(
            text=ocr_result.text,
            pages=ocr_result.pages,
            mode="ocr",
            extraction_quality=ocr_result.extraction_quality,
            first_page_image_png=native.first_page_image_png or ocr_result.first_page_image_png,
            metadata={**ocr_result.metadata, "fallback_from": "pdf_native"},
        )
