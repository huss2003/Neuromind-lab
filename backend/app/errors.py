from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    """HTTP error with a stable machine-readable code (see API_SPEC error shape)."""

    def __init__(self, status: int, code: str, message: str = "Request could not be processed",
                 details: list[dict[str, Any]] | None = None):
        super().__init__(status_code=status, detail=message)
        self.code = code
        self.message = message
        self.details = details or []
