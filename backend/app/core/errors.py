from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Ocorreu um erro interno.",
                    "details": [],
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
