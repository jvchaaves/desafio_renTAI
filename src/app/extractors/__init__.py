"""Extratores de texto e imagem de PDFs e arquivos de imagem."""

from .base import ExtractedDocument, ExtractorBase
from .image import ImageExtractor
from .ocr import OcrExtractor
from .pdf_native import PdfNativeExtractor
from .quality import compute_extraction_quality

__all__ = [
    "ExtractedDocument",
    "ExtractorBase",
    "ImageExtractor",
    "OcrExtractor",
    "PdfNativeExtractor",
    "compute_extraction_quality",
]
