"""
Endpoints da API conforme docs/01-spec/api-contract.openapi.yaml.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import __version__
from ..config import settings
from ..pipeline import get_orchestrator
from ..thresholds.policy import SPECIALTY_ADJUSTMENTS
from ..utils.logging import logger
from .schemas import ConfigResponse, HealthResponse, ValidateResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(version=__version__)


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Snapshot da configuracao para auditoria pelo P01 ou avaliador."""
    return ConfigResponse(
        classification_threshold_base=settings.classification_threshold,
        adaptive_threshold_enabled=settings.adaptive_threshold_enabled,
        specialty_adjustments=SPECIALTY_ADJUSTMENTS,
        text_weight=settings.text_weight,
        visual_weight=settings.visual_weight,
        max_file_size_mb=settings.max_file_size_mb,
        allowed_mime_types=settings.allowed_mime_list,
        active_configuration=settings.active_configuration,
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_document(
    file: UploadFile = File(..., description="PDF ou imagem do documento"),
    specialty: str | None = Form(default=None, description="Especialidade clinica (opcional)"),
) -> ValidateResponse:
    """Classifica um arquivo como documento clinico valido ou invalido."""
    # Validacao de input
    if not file.content_type or file.content_type not in settings.allowed_mime_list:
        raise HTTPException(
            status_code=400,
            detail=(
                f"MIME nao suportado: {file.content_type!r}. "
                f"Aceitos: {settings.allowed_mime_list}"
            ),
        )

    file_bytes = await file.read()
    size = len(file_bytes)
    if size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Arquivo de {size // 1024 // 1024}MB excede limite de "
                f"{settings.max_file_size_mb}MB"
            ),
        )
    if size == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    logger.info(
        "validate.in",
        filename=file.filename,
        mime=file.content_type,
        size_kb=size // 1024,
        specialty=specialty,
    )

    orch = get_orchestrator()
    return orch.validate(
        file_bytes=file_bytes,
        mime=file.content_type,
        specialty=specialty,
    )
