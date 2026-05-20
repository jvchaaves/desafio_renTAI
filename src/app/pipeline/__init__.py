"""Orquestracao do pipeline: router -> extrator -> classificadores -> fusao -> decisao."""

from .orchestrator import Orchestrator, get_orchestrator
from .router import DocumentRouter

__all__ = ["DocumentRouter", "Orchestrator", "get_orchestrator"]
