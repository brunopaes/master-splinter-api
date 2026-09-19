"""Turns library ``ValueError``s into a 422 response.

``master_splinter.validation`` and the analysers raise plain ``ValueError``
with a message already written for the caller (see
``master_splinter/validation.py``). Registered once on the app rather than
duplicated in every handler.

"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValueError)
    async def _on_value_error(request: Request, error: ValueError):
        logger.warning(
            f"request rejected | path={request.url.path} | detail={error}"
        )
        return JSONResponse(status_code=422, content={"detail": str(error)})
