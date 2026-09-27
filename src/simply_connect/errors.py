"""Public exception hierarchy for the Simply Connect SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProblemDetail:
    type: str | None
    title: str | None
    status: int | None
    detail: str | None
    instance: str | None
    code: str | None
    properties: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ProblemDetail:
        properties = value.get("properties")
        return cls(
            type=value.get("type") if isinstance(value.get("type"), str) else None,
            title=value.get("title") if isinstance(value.get("title"), str) else None,
            status=value.get("status") if isinstance(value.get("status"), int) else None,
            detail=value.get("detail") if isinstance(value.get("detail"), str) else None,
            instance=value.get("instance") if isinstance(value.get("instance"), str) else None,
            code=value.get("code") if isinstance(value.get("code"), str) else None,
            properties=properties if isinstance(properties, dict) else {},
        )


class SimplyConnectError(Exception):
    """Base class for every SDK error."""


class ConfigurationError(SimplyConnectError):
    """The local client configuration is invalid."""


class TransportError(SimplyConnectError):
    """The server could not be reached or the response could not be read."""


class UnknownOutcomeError(TransportError):
    """A mutation may have reached the API; retry only with the supplied key."""

    def __init__(self, message: str, *, retry_kind: str, retry_key: str) -> None:
        super().__init__(message)
        self.retry_kind = retry_kind
        self.retry_key = retry_key


class ResponseDecodeError(TransportError):
    """The API returned a successful response that did not match the public contract."""


class ApiError(SimplyConnectError):
    """The API returned a non-success HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        correlation_id: str | None,
        problem: ProblemDetail | None,
        response_body: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.correlation_id = correlation_id
        self.problem = problem
        self.response_body = response_body


class AuthenticationError(ApiError):
    """The API key is missing, invalid, expired, or revoked."""


class AuthorizationError(ApiError):
    """The API key does not have the required scope or endpoint access."""


class ValidationError(ApiError):
    """The request is malformed or violates a domain validation rule."""


class NotFoundError(ApiError):
    """The requested resource does not exist or is not visible to this key."""


class IdempotencyConflictError(ApiError):
    """A retry key was reused for a different operation."""


class RateLimitError(ApiError):
    """The API key exceeded its request budget."""

    def __init__(self, *args: Any, retry_after_seconds: int | None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after_seconds = retry_after_seconds
