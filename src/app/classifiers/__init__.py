"""Classificadores texto + visual conforme ADR-002 (3 configurações)."""

from .base import ClassificationOutput, TextClassifierBase, VisualClassifierBase
from .embeddings import EmbeddingsCentroidClassifier
from .visual_clip import ClipVisualClassifier

__all__ = [
    "ClassificationOutput",
    "ClipVisualClassifier",
    "EmbeddingsCentroidClassifier",
    "TextClassifierBase",
    "VisualClassifierBase",
]
