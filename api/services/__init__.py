"""Thin wrappers around the existing CLI scripts.

The scripts are imported lazily (inside each function) because some of them read
required environment variables, or call sys.exit(), at import time. Importing them
on demand keeps a missing variable from crashing the whole server on startup and
turns it into a per-request error instead.
"""


class ServiceError(Exception):
    """Raised when a script fails; carries the HTTP status the router should return."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class IngestionInProgressError(ServiceError):
    def __init__(self, name: str):
        super().__init__(f"{name} ingestion is already running. Try again when it finishes.", 409)
