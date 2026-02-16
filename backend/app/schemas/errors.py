from typing import Any
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    detail: Any | None = Field(None, description="Additional error details (optional)")

class ErrorResponse(BaseModel):
    error: ErrorDetail
