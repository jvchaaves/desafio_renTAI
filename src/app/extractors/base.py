from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

ProcessingPath = Literal["pdf_native", "ocr", "image_direct"]


@dataclass
class ExtractedDocument:
    """Resultado normalizado da extração — formato comum a todos os extractors."""

    text: str
    pages: int
    mode: ProcessingPath
    extraction_quality: float  # [0, 1]; quanto maior, mais confiável o texto
    first_page_image_png: bytes  # primeira página renderizada como PNG para CLIP
    metadata: dict[str, Any] = field(default_factory=dict)


class ExtractorBase(ABC):
    """Contrato dos extractors. Cada implementação especializada em uma origem."""

    @abstractmethod
    def extract(self, file_bytes: bytes, mime: str) -> ExtractedDocument:
        """Extrai texto + imagem da primeira página."""
        raise NotImplementedError
