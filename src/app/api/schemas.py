from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Enums semânticos refletindo as decisões ---

LabelType = Literal["clinical", "non_clinical"]

ReasonType = Literal[
    "non_clinical",        # decisão classificatória
    "file_unreadable",     # 5.3 — arquivo corrompido
    "no_content",          # 5.3 — sem conteúdo extraível
    "file_protected",      # 5.3 — PDF com senha
    "unsupported_format",  # 5.3 — MIME não suportado
]

ProcessingPath = Literal["pdf_native", "ocr", "image_direct"]
ConfigurationType = Literal["A", "B", "C"]


# --- Sub-modelos ---

class FusionWeights(BaseModel):
    """Pesos efetivamente aplicados na fusão (ADR-002)."""
    text: float = Field(..., ge=0.0, le=1.0)
    visual: float = Field(..., ge=0.0, le=1.0)


class SubSignals(BaseModel):
    """Sinais individuais de cada branch, expostos para auditoria."""
    text: dict[str, Any] = Field(default_factory=dict)
    visual: dict[str, Any] = Field(default_factory=dict)
    extraction_quality: float = Field(..., ge=0.0, le=1.0)
    fusion_weights: FusionWeights


# --- Response principal ---

class ValidateResponse(BaseModel):
    """Resposta do POST /v1/validate — corresponde 1:1 ao schema OpenAPI."""

    valid: bool
    score: float = Field(..., ge=0.0, le=1.0)
    label: LabelType
    threshold_applied: float = Field(..., ge=0.0, le=1.0)
    threshold_reason: str
    justification: str
    reason: ReasonType | None = None
    doc_type_detected: str | None = None
    processing_path: ProcessingPath
    sub_signals: SubSignals
    request_id: str
    latency_ms: int


# --- /v1/health ---

class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


# --- /v1/config ---

class ConfigResponse(BaseModel):
    """Snapshot da configuração corrente — útil para P01 auditar/explicar."""

    classification_threshold_base: float
    adaptive_threshold_enabled: bool
    specialty_adjustments: dict[str, float]
    text_weight: float
    visual_weight: float
    max_file_size_mb: int
    allowed_mime_types: list[str]
    active_configuration: ConfigurationType


# --- RFC 7807 Problem (erros) ---

class Problem(BaseModel):
    """Erro em formato problem+json (RFC 7807)."""
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
