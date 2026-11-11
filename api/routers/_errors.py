import logging
from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException

from api.schemas import ErrorResponse
from api.services import ServiceError

logger = logging.getLogger("api")

T = TypeVar("T")

# Shown in the OpenAPI docs for every endpoint that runs a script.
ERROR_RESPONSES = {
    500: {"model": ErrorResponse, "description": "The underlying script failed."},
    502: {"model": ErrorResponse, "description": "The symbolic WSD service could not be reached."},
}


def run_script(operation: str, fn: Callable[..., T], *args, **kwargs) -> T:
    """Call a service function and turn any failure into an HTTPException with a useful status code."""
    try:
        return fn(*args, **kwargs)
    except ServiceError as e:
        logger.warning("%s failed: %s", operation, e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("%s failed", operation)
        raise HTTPException(status_code=500, detail=f"{operation} failed: {type(e).__name__}: {e}") from e
