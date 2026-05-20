from .base import ExtractedDocument, ExtractorBase
from .ocr import OcrExtractor


class ImageExtractor(ExtractorBase):
    """Imagens diretas — delega para OcrExtractor mas marca mode=image_direct."""

    def __init__(self) -> None:
        self._ocr = OcrExtractor()

    def extract(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        result = self._ocr.extract(file_bytes, mime)
        # Garante que o modo reflete imagem direta, mesmo se for PNG renderizado
        # internamente como pdf-like (não deveria acontecer aqui, mas defesa)
        if result.mode != "image_direct":
            result = ExtractedDocument(
                text=result.text,
                pages=result.pages,
                mode="image_direct",
                extraction_quality=result.extraction_quality,
                first_page_image_png=result.first_page_image_png,
                metadata={**result.metadata, "extractor_chain": "image -> ocr"},
            )
        return result
