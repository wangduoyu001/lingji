from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("lingji.control.read_model")

READ_MODEL_ERROR_CODE = "READ_MODEL_UNAVAILABLE"
READ_MODEL_ERROR_MESSAGE = "Structured read model is unavailable"


def install_control_api_contract(api_module: Any) -> None:
    """Wrap the app factory once and sanitize Inspector 503 responses."""

    original = api_module.create_control_app
    if getattr(original, "_lingji_read_model_contract", False):
        return

    def create_control_app(*args: Any, **kwargs: Any):
        app = original(*args, **kwargs)
        try:
            from fastapi import HTTPException, Request
            from fastapi.exception_handlers import http_exception_handler
            from fastapi.responses import JSONResponse
        except ImportError:
            return app

        async def sanitized_http_exception_handler(request: Request, exc: HTTPException):
            if (
                exc.status_code == 503
                and request.url.path.startswith("/api/memory/inspector")
            ):
                internal = exc.__cause__ or exc
                logger.error(
                    "Structured read model request failed",
                    exc_info=(type(internal), internal, internal.__traceback__),
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": {
                            "code": READ_MODEL_ERROR_CODE,
                            "message": READ_MODEL_ERROR_MESSAGE,
                        }
                    },
                )
            return await http_exception_handler(request, exc)

        app.add_exception_handler(HTTPException, sanitized_http_exception_handler)
        return app

    create_control_app._lingji_read_model_contract = True
    api_module.create_control_app = create_control_app
