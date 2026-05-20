"""Fusao de scores texto+visao conforme ADR-002."""

from .score_fusion import FusedResult, fuse_scores

__all__ = ["FusedResult", "fuse_scores"]
