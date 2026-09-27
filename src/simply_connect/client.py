"""Synchronous and asynchronous clients for the Simply Connect External API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx

from ._version import __version__
from .errors import (
    ApiError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    IdempotencyConflictError,
    NotFoundError,
    ProblemDetail,
    RateLimitError,
    ResponseDecodeError,
    TransportError,
    UnknownOutcomeError,
    ValidationError,
)
from .models import (
    CallDetails,
    CallPage,
    CallQueueEndpoint,
    CallQueueItem,
    CallQueuePage,
    Contact,
    ContactPage,
    MessageDetails,
    MessagePage,
    PublishedCallFlow,
    SmsEndpoint,
    SmsSendResult,
    response_object,
    response_objects,
)

DEFAULT_BASE_URL = "https://api.simply-connect.ovh"
DEFAULT_TIMEOUT = 15.0

QueryValue = str | int | bool | datetime | None


def _require_non_blank(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{name} must be a non-empty string")
    return value.strip()


def _external_api_base(base_url: str) -> str:
    parsed = urlparse(_require_non_blank(base_url, "base_url"))
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ConfigurationError("base_url must be an absolute HTTP or HTTPS URL")
    path = parsed.path.rstrip("/")
    suffix = "/api/v1/external"
    if not path.endswith(suffix):
        path = f"{path}{suffix}"
    return urlunparse((parsed.scheme, parsed.netloc, f"{path}/", "", "", ""))


def _filter_datetime(value: datetime, name: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ConfigurationError(f"{name} must include a timezone")
    return value.isoformat()


def _scheduled_datetime(value: datetime) -> str:
    if value.tzinfo is not None and value.utcoffset() is not None:
        raise ConfigurationError("scheduled_for must be a local wall-clock time without an offset")
    return value.isoformat()


def _params(values: dict[str, QueryValue]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in values.items():
        if value is None or value == "":
            continue
        if isinstance(value, datetime):
            result[key] = _filter_datetime(value, key)
        elif isinstance(value, bool):
            result[key] = "true" if value else "false"
        else:
            result[key] = str(value)
    return result


def _problem(response: httpx.Response) -> ProblemDetail | None:
    try:
        value = response.json()
    except ValueError:
        return None
    return ProblemDetail.from_dict(value) if isinstance(value, dict) else None


def _raise_api_error(response: httpx.Response) -> None:
    problem = _problem(response)
    body = response.text
    message = (
        problem.detail
        if problem and problem.detail
        else f"Simply Connect returned HTTP {response.status_code}"
    )
    kwargs = {
        "status_code": response.status_code,
        "correlation_id": response.headers.get("x-correlation-id"),
        "problem": problem,
        "response_body": body,
    }
    if response.status_code == 401:
        raise AuthenticationError(message, **kwargs)
    if response.status_code == 403:
        raise AuthorizationError(message, **kwargs)
    if response.status_code in (400, 422):
        raise ValidationError(message, **kwargs)
    if response.status_code == 404:
        raise NotFoundError(message, **kwargs)
    if response.status_code == 409:
        raise IdempotencyConflictError(message, **kwargs)
    if response.status_code == 429:
        retry_after = response.headers.get("retry-after")
        raise RateLimitError(
            message,
            **kwargs,
            retry_after_seconds=int(retry_after) if retry_after and retry_after.isdigit() else None,
        )
    raise ApiError(message, **kwargs)


def _json(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as error:
        raise ResponseDecodeError("Simply Connect returned unreadable JSON") from error


class SimplyConnectClient:
    """Blocking client suitable for scripts, workers, Django, Flask, and WSGI apps."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        default_sms_endpoint_id: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout <= 0:
            raise ConfigurationError("timeout must be greater than zero")
        self._default_sms_endpoint_id = default_sms_endpoint_id
        self._client = httpx.Client(
            base_url=_external_api_base(base_url),
            timeout=timeout,
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/json",
                "X-API-Key": _require_non_blank(api_key, "api_key"),
                "User-Agent": user_agent or f"simply-connect-python/{__version__}",
            },
        )

    def __enter__(self) -> SimplyConnectClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        unknown_outcome: tuple[str, str] | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        try:
            response = self._client.request(method, path, params=params, json=json, headers=headers)
        except httpx.RequestError as error:
            if unknown_outcome:
                raise UnknownOutcomeError(
                    "The request outcome is unknown; retry only with the supplied key",
                    retry_kind=unknown_outcome[0],
                    retry_key=unknown_outcome[1],
                ) from error
            raise TransportError("Could not reach Simply Connect") from error
        if not response.is_success:
            _raise_api_error(response)
        return _json(response)

    def list_sms_endpoints(self) -> tuple[SmsEndpoint, ...]:
        return tuple(
            SmsEndpoint.from_dict(item)
            for item in response_objects(self._request("GET", "endpoints"))
        )

    def send_sms(
        self,
        to: str,
        body: str,
        *,
        endpoint_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> SmsSendResult:
        selected_endpoint = endpoint_id or self._default_sms_endpoint_id
        if not selected_endpoint:
            raise ConfigurationError(
                "endpoint_id is required when default_sms_endpoint_id is not configured"
            )
        key = _require_non_blank(idempotency_key or str(uuid4()), "idempotency_key")
        data = self._request(
            "POST",
            "messages",
            json={"endpointId": selected_endpoint, "to": to, "body": body},
            idempotency_key=key,
            unknown_outcome=("idempotency_key", key),
        )
        return SmsSendResult.from_dict(response_object(data), idempotency_key=key)

    def list_messages(
        self,
        *,
        query: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        endpoint_id: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        page: int | None = None,
        size: int | None = None,
    ) -> MessagePage:
        data = self._request(
            "GET",
            "messages",
            params=_params(
                {
                    "query": query,
                    "direction": direction,
                    "status": status,
                    "endpointId": endpoint_id,
                    "occurredFrom": occurred_from,
                    "occurredTo": occurred_to,
                    "page": page,
                    "size": size,
                }
            ),
        )
        return MessagePage.from_dict(response_object(data))

    def get_message(self, message_id: str) -> MessageDetails:
        data = self._request("GET", f"messages/{_require_non_blank(message_id, 'message_id')}")
        return MessageDetails.from_dict(response_object(data))

    def list_contacts(
        self, *, query: str | None = None, page: int | None = None, size: int | None = None
    ) -> ContactPage:
        data = self._request(
            "GET", "contacts", params=_params({"query": query, "page": page, "size": size})
        )
        return ContactPage.from_dict(response_object(data))

    def get_contact(self, contact_id: str) -> Contact:
        data = self._request("GET", f"contacts/{_require_non_blank(contact_id, 'contact_id')}")
        return Contact.from_dict(response_object(data))

    def list_calls(
        self, *, endpoint_id: str | None = None, page: int | None = None, size: int | None = None
    ) -> CallPage:
        data = self._request(
            "GET",
            "calls",
            params=_params({"endpointId": endpoint_id, "page": page, "size": size}),
        )
        return CallPage.from_dict(response_object(data))

    def get_call(self, call_id: str) -> CallDetails:
        data = self._request("GET", f"calls/{_require_non_blank(call_id, 'call_id')}")
        return CallDetails.from_dict(response_object(data))

    def list_call_queue_endpoints(self) -> tuple[CallQueueEndpoint, ...]:
        return tuple(
            CallQueueEndpoint.from_dict(item)
            for item in response_objects(self._request("GET", "call-queue/endpoints"))
        )

    def list_published_call_flows(self) -> tuple[PublishedCallFlow, ...]:
        return tuple(
            PublishedCallFlow.from_dict(item)
            for item in response_objects(self._request("GET", "call-queue/flows"))
        )

    def list_call_queue(
        self,
        *,
        endpoint_id: str | None = None,
        status: str | None = None,
        source: str | None = None,
        search: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        page: int | None = None,
        size: int | None = None,
        sort: str | None = None,
        descending: bool | None = None,
    ) -> CallQueuePage:
        data = self._request(
            "GET",
            "call-queue",
            params=_params(
                {
                    "endpointId": endpoint_id,
                    "status": status,
                    "source": source,
                    "search": search,
                    "from": from_,
                    "to": to,
                    "page": page,
                    "size": size,
                    "sort": sort,
                    "descending": descending,
                }
            ),
        )
        return CallQueuePage.from_dict(response_object(data))

    def create_call_queue_entry(
        self,
        *,
        endpoint_id: str,
        destination: str,
        flow_version_id: str,
        time_zone: str,
        request_id: str | None = None,
        scheduled_for: datetime | None = None,
        interval_seconds: int | None = None,
    ) -> CallQueueItem:
        key = _require_non_blank(request_id or str(uuid4()), "request_id")
        body: dict[str, Any] = {
            "endpointId": endpoint_id,
            "destination": destination,
            "flowVersionId": flow_version_id,
            "requestId": key,
            "timeZone": time_zone,
        }
        if scheduled_for is not None:
            body["scheduledFor"] = _scheduled_datetime(scheduled_for)
        if interval_seconds is not None:
            body["intervalSeconds"] = interval_seconds
        data = self._request(
            "POST",
            "call-queue",
            json=body,
            unknown_outcome=("request_id", key),
        )
        return CallQueueItem.from_dict(response_object(data))


class AsyncSimplyConnectClient:
    """Async client suitable for asyncio workers, FastAPI, Starlette, and ASGI apps."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        default_sms_endpoint_id: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if timeout <= 0:
            raise ConfigurationError("timeout must be greater than zero")
        self._default_sms_endpoint_id = default_sms_endpoint_id
        self._client = httpx.AsyncClient(
            base_url=_external_api_base(base_url),
            timeout=timeout,
            follow_redirects=False,
            transport=transport,
            headers={
                "Accept": "application/json",
                "X-API-Key": _require_non_blank(api_key, "api_key"),
                "User-Agent": user_agent or f"simply-connect-python/{__version__}",
            },
        )

    async def __aenter__(self) -> AsyncSimplyConnectClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        unknown_outcome: tuple[str, str] | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        try:
            response = await self._client.request(
                method, path, params=params, json=json, headers=headers
            )
        except httpx.RequestError as error:
            if unknown_outcome:
                raise UnknownOutcomeError(
                    "The request outcome is unknown; retry only with the supplied key",
                    retry_kind=unknown_outcome[0],
                    retry_key=unknown_outcome[1],
                ) from error
            raise TransportError("Could not reach Simply Connect") from error
        if not response.is_success:
            _raise_api_error(response)
        return _json(response)

    async def list_sms_endpoints(self) -> tuple[SmsEndpoint, ...]:
        return tuple(
            SmsEndpoint.from_dict(item)
            for item in response_objects(await self._request("GET", "endpoints"))
        )

    async def send_sms(
        self,
        to: str,
        body: str,
        *,
        endpoint_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> SmsSendResult:
        selected_endpoint = endpoint_id or self._default_sms_endpoint_id
        if not selected_endpoint:
            raise ConfigurationError(
                "endpoint_id is required when default_sms_endpoint_id is not configured"
            )
        key = _require_non_blank(idempotency_key or str(uuid4()), "idempotency_key")
        data = await self._request(
            "POST",
            "messages",
            json={"endpointId": selected_endpoint, "to": to, "body": body},
            idempotency_key=key,
            unknown_outcome=("idempotency_key", key),
        )
        return SmsSendResult.from_dict(response_object(data), idempotency_key=key)

    async def list_messages(
        self,
        *,
        query: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        endpoint_id: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        page: int | None = None,
        size: int | None = None,
    ) -> MessagePage:
        allowed: dict[str, QueryValue] = {
            "query": query,
            "direction": direction,
            "status": status,
            "endpointId": endpoint_id,
            "occurredFrom": occurred_from,
            "occurredTo": occurred_to,
            "page": page,
            "size": size,
        }
        data = await self._request("GET", "messages", params=_params(allowed))
        return MessagePage.from_dict(response_object(data))

    async def get_message(self, message_id: str) -> MessageDetails:
        data = await self._request(
            "GET", f"messages/{_require_non_blank(message_id, 'message_id')}"
        )
        return MessageDetails.from_dict(response_object(data))

    async def list_contacts(
        self, *, query: str | None = None, page: int | None = None, size: int | None = None
    ) -> ContactPage:
        data = await self._request(
            "GET", "contacts", params=_params({"query": query, "page": page, "size": size})
        )
        return ContactPage.from_dict(response_object(data))

    async def get_contact(self, contact_id: str) -> Contact:
        data = await self._request(
            "GET", f"contacts/{_require_non_blank(contact_id, 'contact_id')}"
        )
        return Contact.from_dict(response_object(data))

    async def list_calls(
        self, *, endpoint_id: str | None = None, page: int | None = None, size: int | None = None
    ) -> CallPage:
        data = await self._request(
            "GET",
            "calls",
            params=_params({"endpointId": endpoint_id, "page": page, "size": size}),
        )
        return CallPage.from_dict(response_object(data))

    async def get_call(self, call_id: str) -> CallDetails:
        data = await self._request("GET", f"calls/{_require_non_blank(call_id, 'call_id')}")
        return CallDetails.from_dict(response_object(data))

    async def list_call_queue_endpoints(self) -> tuple[CallQueueEndpoint, ...]:
        return tuple(
            CallQueueEndpoint.from_dict(item)
            for item in response_objects(await self._request("GET", "call-queue/endpoints"))
        )

    async def list_published_call_flows(self) -> tuple[PublishedCallFlow, ...]:
        return tuple(
            PublishedCallFlow.from_dict(item)
            for item in response_objects(await self._request("GET", "call-queue/flows"))
        )

    async def list_call_queue(
        self,
        *,
        endpoint_id: str | None = None,
        status: str | None = None,
        source: str | None = None,
        search: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        page: int | None = None,
        size: int | None = None,
        sort: str | None = None,
        descending: bool | None = None,
    ) -> CallQueuePage:
        values: dict[str, QueryValue] = {
            "endpointId": endpoint_id,
            "status": status,
            "source": source,
            "search": search,
            "from": from_,
            "to": to,
            "page": page,
            "size": size,
            "sort": sort,
            "descending": descending,
        }
        data = await self._request("GET", "call-queue", params=_params(values))
        return CallQueuePage.from_dict(response_object(data))

    async def create_call_queue_entry(
        self,
        *,
        endpoint_id: str,
        destination: str,
        flow_version_id: str,
        time_zone: str,
        request_id: str | None = None,
        scheduled_for: datetime | None = None,
        interval_seconds: int | None = None,
    ) -> CallQueueItem:
        key = _require_non_blank(request_id or str(uuid4()), "request_id")
        body: dict[str, Any] = {
            "endpointId": endpoint_id,
            "destination": destination,
            "flowVersionId": flow_version_id,
            "requestId": key,
            "timeZone": time_zone,
        }
        if scheduled_for is not None:
            body["scheduledFor"] = _scheduled_datetime(scheduled_for)
        if interval_seconds is not None:
            body["intervalSeconds"] = interval_seconds
        data = await self._request(
            "POST",
            "call-queue",
            json=body,
            unknown_outcome=("request_id", key),
        )
        return CallQueueItem.from_dict(response_object(data))
