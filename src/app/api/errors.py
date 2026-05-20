from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .schemas import Problem

PROBLEM_MEDIA_TYPE = "application/problem+json"


def _problem_response(problem: Problem) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    problem = Problem(
        title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
        status=exc.status_code,
        detail=exc.detail if isinstance(exc.detail, str) else None,
        instance=str(request.url.path),
    )
    return _problem_response(problem)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    problem = Problem(
        title="Validation error",
        status=422,
        detail=f"{len(exc.errors())} field(s) failed validation",
        instance=str(request.url.path),
    )
    return _problem_response(problem)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    problem = Problem(
        title="Internal server error",
        status=500,
        detail=str(exc) if str(exc) else None,
        instance=str(request.url.path),
    )
    return _problem_response(problem)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
