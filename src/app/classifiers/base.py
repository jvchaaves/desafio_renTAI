"""Interface comum dos classificadores."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..extractors.base import ExtractedDocument


@dataclass
class ClassificationOutput:
    """Saida normalizada de cada classifier (texto OU visual)."""

    score: float  # [0,1] prob de ser clinico valido
    label: str  # rotulo bruto do classifier (clinical/non_clinical/neutral)
    justification: str  # explicacao legivel
    sub_signals: dict[str, Any] = field(default_factory=dict)
    classifier_name: str = ""


class TextClassifierBase(ABC):
    """Classifica baseado em texto extraido."""

    @abstractmethod
    def classify(self, doc: ExtractedDocument) -> ClassificationOutput:
        raise NotImplementedError


class VisualClassifierBase(ABC):
    """Classifica baseado na imagem da primeira pagina."""

    @abstractmethod
    def classify_image(self, image_png: bytes) -> ClassificationOutput:
        raise NotImplementedError
