from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__
from .api.errors import register_error_handlers
from .api.routes import router
from .config import settings
from .utils.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings.log_level)
    logger.info(
        "startup",
        version=__version__,
        active_configuration=settings.active_configuration,
        adaptive_threshold=settings.adaptive_threshold_enabled,
    )
    # Warm-up: forca instanciacao do orchestrator e load do artifact de
    # centroides no startup (em vez de na primeira requisicao).
    # Evita que o primeiro POST /v1/validate fique segurando o cliente
    # enquanto carrega modelos. Ver ADR-005.
    from .pipeline import get_orchestrator
    get_orchestrator()
    logger.info("startup.warmup_done")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Servico de Validacao de Documentos Clinicos",
    description=(
        "Backend de IA do Desafio P04 ReNTAI — classifica se um arquivo "
        "(PDF ou imagem) e documento clinico valido no escopo de "
        "teleconsultoria SUS via APS. Consumido pelo modulo Fullstack P01."
    ),
    version=__version__,
    lifespan=lifespan,
)

register_error_handlers(app)
app.include_router(router, prefix="/v1")
