from __future__ import annotations


class DomainError(Exception):
    """Base for all domain-level errors."""


class NotFoundError(DomainError):
    def __init__(self, entity: str = "Resource", detail: str | None = None):
        self.entity = entity
        self.detail = detail or f"{entity} not found"
        super().__init__(self.detail)


class ForbiddenError(DomainError):
    def __init__(self, detail: str = "Forbidden"):
        self.detail = detail
        super().__init__(self.detail)


class ConflictError(DomainError):
    def __init__(self, detail: str = "Conflict"):
        self.detail = detail
        super().__init__(self.detail)


class ValidationError(DomainError):
    def __init__(self, detail: str = "Validation error"):
        self.detail = detail
        super().__init__(self.detail)


class InfrastructureError(DomainError):
    def __init__(self, detail: str = "Infrastructure error"):
        self.detail = detail
        super().__init__(self.detail)
