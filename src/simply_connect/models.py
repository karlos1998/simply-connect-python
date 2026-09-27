"""Typed value objects returned by the Simply Connect External API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, TypeAlias, cast

JsonValue: TypeAlias = bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"] | None
MessageDirection: TypeAlias = Literal["INBOUND", "OUTBOUND"]
MessageChannel: TypeAlias = Literal["SMS", "MMS"]


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Expected an ISO 8601 date-time string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_datetime(value: Any) -> datetime | None:
    return None if value is None else _datetime(value)


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Expected {field} to be a string")
    return value


def _optional_string(value: Any, field: str) -> str | None:
    return None if value is None else _string(value, field)


def _integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Expected {field} to be an integer")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Expected {field} to be a boolean")
    return value


def _mapping(value: Any, field: str = "response") -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"Expected {field} to be an object")
    return cast(dict[str, Any], value)


def _objects(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"Expected {field} to be an array")
    return [_mapping(item, field) for item in value]


@dataclass(frozen=True, slots=True)
class SmsEndpoint:
    id: str
    name: str
    enabled: bool
    phone_number: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SmsEndpoint:
        return cls(
            id=_string(value.get("id"), "id"),
            name=_string(value.get("name"), "name"),
            enabled=_boolean(value.get("enabled"), "enabled"),
            phone_number=_optional_string(value.get("phoneNumber"), "phoneNumber"),
        )


@dataclass(frozen=True, slots=True)
class SmsSendResult:
    message_id: str
    dispatch_id: str
    command_id: str
    status: str
    idempotency_key: str

    @classmethod
    def from_dict(cls, value: dict[str, Any], *, idempotency_key: str) -> SmsSendResult:
        return cls(
            message_id=_string(value.get("messageId"), "messageId"),
            dispatch_id=_string(value.get("dispatchId"), "dispatchId"),
            command_id=_string(value.get("commandId"), "commandId"),
            status=_string(value.get("status"), "status"),
            idempotency_key=idempotency_key,
        )


@dataclass(frozen=True, slots=True)
class StatusEvent:
    status: str | None
    event_type: str | None
    source: str | None
    error_code: str | None
    occurred_at: datetime | None
    recorded_at: datetime | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> StatusEvent:
        return cls(
            status=_optional_string(value.get("status"), "status"),
            event_type=_optional_string(value.get("eventType"), "eventType"),
            source=_optional_string(value.get("source"), "source"),
            error_code=_optional_string(value.get("errorCode"), "errorCode"),
            occurred_at=_optional_datetime(value.get("occurredAt")),
            recorded_at=_optional_datetime(value.get("recordedAt")),
        )


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    conversation_id: str
    direction: MessageDirection
    channel: MessageChannel
    body: str
    remote_address: str
    occurred_at: datetime
    endpoint: SmsEndpoint
    status: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Message:
        direction = _string(value.get("direction"), "direction")
        channel = _string(value.get("channel"), "channel")
        if direction not in ("INBOUND", "OUTBOUND"):
            raise ValueError("Unknown message direction")
        if channel not in ("SMS", "MMS"):
            raise ValueError("Unknown message channel")
        return cls(
            id=_string(value.get("id"), "id"),
            conversation_id=_string(value.get("conversationId"), "conversationId"),
            direction=cast(MessageDirection, direction),
            channel=cast(MessageChannel, channel),
            body=_string(value.get("body"), "body"),
            remote_address=_string(value.get("remoteAddress"), "remoteAddress"),
            occurred_at=_datetime(value.get("occurredAt")),
            endpoint=SmsEndpoint.from_dict(_mapping(value.get("endpoint"), "endpoint")),
            status=_optional_string(value.get("status"), "status"),
        )


@dataclass(frozen=True, slots=True)
class MessageDetails:
    message: Message
    created_at: datetime
    status_history: tuple[StatusEvent, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> MessageDetails:
        return cls(
            message=Message.from_dict(value),
            created_at=_datetime(value.get("createdAt")),
            status_history=tuple(
                StatusEvent.from_dict(item)
                for item in _objects(value.get("statusHistory"), "statusHistory")
            ),
        )


@dataclass(frozen=True, slots=True)
class MessagePage:
    items: tuple[Message, ...]
    page: int
    size: int
    total_elements: int
    total_pages: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> MessagePage:
        return cls(
            items=tuple(Message.from_dict(item) for item in _objects(value.get("items"), "items")),
            page=_integer(value.get("page"), "page"),
            size=_integer(value.get("size"), "size"),
            total_elements=_integer(value.get("totalElements"), "totalElements"),
            total_pages=_integer(value.get("totalPages"), "totalPages"),
        )


@dataclass(frozen=True, slots=True)
class ContactChannel:
    id: str
    type: str
    value: str
    normalized_value: str
    primary: bool
    label: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ContactChannel:
        return cls(
            id=_string(value.get("id"), "id"),
            type=_string(value.get("type"), "type"),
            value=_string(value.get("value"), "value"),
            normalized_value=_string(value.get("normalizedValue"), "normalizedValue"),
            primary=_boolean(value.get("primary"), "primary"),
            label=_optional_string(value.get("label"), "label"),
        )


@dataclass(frozen=True, slots=True)
class ContactTag:
    id: str
    name: str
    color: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ContactTag:
        return cls(
            id=_string(value.get("id"), "id"),
            name=_string(value.get("name"), "name"),
            color=_optional_string(value.get("color"), "color"),
        )


@dataclass(frozen=True, slots=True)
class Contact:
    id: str
    display_name: str
    first_name: str | None
    last_name: str | None
    company_id: str | None
    company_name: str | None
    job_title: str | None
    notes: str | None
    owner_user_id: str | None
    channels: tuple[ContactChannel, ...]
    tags: tuple[ContactTag, ...]
    custom_fields: dict[str, str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Contact:
        custom_fields = _mapping(value.get("customFields", {}), "customFields")
        if not all(isinstance(item, str) for item in custom_fields.values()):
            raise ValueError("Expected customFields values to be strings")
        return cls(
            id=_string(value.get("id"), "id"),
            display_name=_string(value.get("displayName"), "displayName"),
            first_name=_optional_string(value.get("firstName"), "firstName"),
            last_name=_optional_string(value.get("lastName"), "lastName"),
            company_id=_optional_string(value.get("companyId"), "companyId"),
            company_name=_optional_string(value.get("companyName"), "companyName"),
            job_title=_optional_string(value.get("jobTitle"), "jobTitle"),
            notes=_optional_string(value.get("notes"), "notes"),
            owner_user_id=_optional_string(value.get("ownerUserId"), "ownerUserId"),
            channels=tuple(
                ContactChannel.from_dict(item)
                for item in _objects(value.get("channels", []), "channels")
            ),
            tags=tuple(
                ContactTag.from_dict(item) for item in _objects(value.get("tags", []), "tags")
            ),
            custom_fields=cast(dict[str, str], custom_fields),
            created_at=_datetime(value.get("createdAt")),
            updated_at=_datetime(value.get("updatedAt")),
        )


@dataclass(frozen=True, slots=True)
class ContactPage:
    items: tuple[Contact, ...]
    page: int
    size: int
    total_elements: int
    has_more: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ContactPage:
        return cls(
            items=tuple(Contact.from_dict(item) for item in _objects(value.get("items"), "items")),
            page=_integer(value.get("page"), "page"),
            size=_integer(value.get("size"), "size"),
            total_elements=_integer(value.get("totalElements"), "totalElements"),
            has_more=_boolean(value.get("hasMore"), "hasMore"),
        )


@dataclass(frozen=True, slots=True)
class Call:
    id: str
    endpoint_id: str
    endpoint_name: str
    state: str
    started_at: datetime
    caller_address: str | None
    endpoint_phone_number: str | None
    gateway_name: str | None
    contact_id: str | None
    contact_name: str | None
    answered_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    transcript: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Call:
        duration = value.get("durationSeconds")
        return cls(
            id=_string(value.get("id"), "id"),
            endpoint_id=_string(value.get("endpointId"), "endpointId"),
            endpoint_name=_string(value.get("endpointName"), "endpointName"),
            state=_string(value.get("state"), "state"),
            started_at=_datetime(value.get("startedAt")),
            caller_address=_optional_string(value.get("callerAddress"), "callerAddress"),
            endpoint_phone_number=_optional_string(
                value.get("endpointPhoneNumber"), "endpointPhoneNumber"
            ),
            gateway_name=_optional_string(value.get("gatewayName"), "gatewayName"),
            contact_id=_optional_string(value.get("contactId"), "contactId"),
            contact_name=_optional_string(value.get("contactName"), "contactName"),
            answered_at=_optional_datetime(value.get("answeredAt")),
            ended_at=_optional_datetime(value.get("endedAt")),
            duration_seconds=None if duration is None else _integer(duration, "durationSeconds"),
            transcript=_optional_string(value.get("transcript"), "transcript"),
        )


@dataclass(frozen=True, slots=True)
class CallEvent:
    id: str
    kind: str
    event_type: str
    occurred_at: datetime
    node_id: str | None
    node_label: str | None
    audio_name: str | None
    duration_ms: int | None
    language: str | None
    transcript: str | None
    payload: dict[str, JsonValue]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CallEvent:
        duration = value.get("durationMs")
        return cls(
            id=_string(value.get("id"), "id"),
            kind=_string(value.get("kind"), "kind"),
            event_type=_string(value.get("eventType"), "eventType"),
            occurred_at=_datetime(value.get("occurredAt")),
            node_id=_optional_string(value.get("nodeId"), "nodeId"),
            node_label=_optional_string(value.get("nodeLabel"), "nodeLabel"),
            audio_name=_optional_string(value.get("audioName"), "audioName"),
            duration_ms=None if duration is None else _integer(duration, "durationMs"),
            language=_optional_string(value.get("language"), "language"),
            transcript=_optional_string(value.get("transcript"), "transcript"),
            payload=cast(dict[str, JsonValue], _mapping(value.get("payload", {}), "payload")),
        )


@dataclass(frozen=True, slots=True)
class CallDetails:
    call: Call
    timeline: tuple[CallEvent, ...]
    routing_flow_id: str | None
    routing_flow_name: str | None
    routing_flow_version: int | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CallDetails:
        version = value.get("routingFlowVersion")
        return cls(
            call=Call.from_dict(_mapping(value.get("call"), "call")),
            timeline=tuple(
                CallEvent.from_dict(item)
                for item in _objects(value.get("timeline", []), "timeline")
            ),
            routing_flow_id=_optional_string(value.get("routingFlowId"), "routingFlowId"),
            routing_flow_name=_optional_string(value.get("routingFlowName"), "routingFlowName"),
            routing_flow_version=None
            if version is None
            else _integer(version, "routingFlowVersion"),
        )


@dataclass(frozen=True, slots=True)
class CallPage:
    items: tuple[Call, ...]
    page: int
    size: int
    total_elements: int
    total_pages: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CallPage:
        return cls(
            items=tuple(Call.from_dict(item) for item in _objects(value.get("items"), "items")),
            page=_integer(value.get("page"), "page"),
            size=_integer(value.get("size"), "size"),
            total_elements=_integer(value.get("totalElements"), "totalElements"),
            total_pages=_integer(value.get("totalPages"), "totalPages"),
        )


@dataclass(frozen=True, slots=True)
class CallQueueEndpoint:
    id: str
    name: str
    gateway_id: str
    gateway_name: str
    gateway_status: str
    phone_number: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CallQueueEndpoint:
        return cls(
            id=_string(value.get("id"), "id"),
            name=_string(value.get("name"), "name"),
            gateway_id=_string(value.get("gatewayId"), "gatewayId"),
            gateway_name=_string(value.get("gatewayName"), "gatewayName"),
            gateway_status=_string(value.get("gatewayStatus"), "gatewayStatus"),
            phone_number=_optional_string(value.get("phoneNumber"), "phoneNumber"),
        )


@dataclass(frozen=True, slots=True)
class PublishedCallFlow:
    id: str
    name: str
    published_version_id: str
    updated_at: datetime
    description: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PublishedCallFlow:
        return cls(
            id=_string(value.get("id"), "id"),
            name=_string(value.get("name"), "name"),
            published_version_id=_string(value.get("publishedVersionId"), "publishedVersionId"),
            updated_at=_datetime(value.get("updatedAt")),
            description=_optional_string(value.get("description"), "description"),
        )


@dataclass(frozen=True, slots=True)
class CallQueueItem:
    id: str
    endpoint_id: str
    destination: str
    flow_version_id: str
    flow_name: str
    flow_version: int
    source: str
    status: str
    not_before: datetime
    time_zone: str
    interval_seconds: int
    created_at: datetime
    updated_at: datetime
    reason: str | None
    call_id: str | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CallQueueItem:
        return cls(
            id=_string(value.get("id"), "id"),
            endpoint_id=_string(value.get("endpointId"), "endpointId"),
            destination=_string(value.get("destination"), "destination"),
            flow_version_id=_string(value.get("flowVersionId"), "flowVersionId"),
            flow_name=_string(value.get("flowName"), "flowName"),
            flow_version=_integer(value.get("flowVersion"), "flowVersion"),
            source=_string(value.get("source"), "source"),
            status=_string(value.get("status"), "status"),
            not_before=_datetime(value.get("notBefore")),
            time_zone=_string(value.get("timeZone"), "timeZone"),
            interval_seconds=_integer(value.get("intervalSeconds"), "intervalSeconds"),
            created_at=_datetime(value.get("createdAt")),
            updated_at=_datetime(value.get("updatedAt")),
            reason=_optional_string(value.get("reason"), "reason"),
            call_id=_optional_string(value.get("callId"), "callId"),
        )


@dataclass(frozen=True, slots=True)
class CallQueuePage:
    items: tuple[CallQueueItem, ...]
    page: int
    total_elements: int
    total_pages: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CallQueuePage:
        return cls(
            items=tuple(
                CallQueueItem.from_dict(item) for item in _objects(value.get("items"), "items")
            ),
            page=_integer(value.get("page"), "page"),
            total_elements=_integer(value.get("totalElements"), "totalElements"),
            total_pages=_integer(value.get("totalPages"), "totalPages"),
        )


def response_object(value: Any) -> dict[str, Any]:
    """Validate an HTTP response body before constructing a typed model."""

    return _mapping(value)


def response_objects(value: Any) -> list[dict[str, Any]]:
    """Validate an HTTP response array before constructing typed models."""

    return _objects(value, "response")
