"""Custom exceptions for maestro_runner."""

from __future__ import annotations


class MaestroError(Exception):
    """Base exception for maestro-runner client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SessionError(MaestroError):
    """Raised when session creation or management fails."""


class StepError(MaestroError):
    """Raised when a step execution fails and optional=False."""
