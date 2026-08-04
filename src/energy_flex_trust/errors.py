"""Errors that can be safely translated to API responses."""

from __future__ import annotations


class DomainError(Exception):
    code = "domain_error"
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404


class ConflictError(DomainError):
    code = "conflict"
    status_code = 409


class ForbiddenError(DomainError):
    code = "forbidden"
    status_code = 403


class InvalidTransitionError(ConflictError):
    code = "invalid_transition"
