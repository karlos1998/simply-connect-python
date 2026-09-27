from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from simply_connect import (
    ApiError,
    AsyncSimplyConnectClient,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    IdempotencyConflictError,
    NotFoundError,
    RateLimitError,
    ResponseDecodeError,
    SimplyConnectClient,
    TransportError,
    UnknownOutcomeError,
    ValidationError,
)

ENDPOINT = {
    "id": "endpoint-1",
    "name": "Main SIM",
    "phoneNumber": "+48500100200",
    "enabled": True,
}
MESSAGE = {
    "id": "message-1",
    "conversationId": "conversation-1",
    "direction": "OUTBOUND",
    "channel": "SMS",
    "body": "Hello",
    "remoteAddress": "+48500100300",
    "occurredAt": "2026-09-27T00:00:00Z",
    "status": "DELIVERED",
    "endpoint": ENDPOINT,
}
CONTACT = {
    "id": "contact-1",
    "displayName": "Ada Lovelace",
    "firstName": "Ada",
    "lastName": "Lovelace",
    "companyId": None,
    "companyName": None,
    "jobTitle": "Engineer",
    "notes": None,
    "ownerUserId": None,
    "channels": [
        {
            "id": "channel-1",
            "type": "PHONE",
            "value": "+48500100300",
            "normalizedValue": "+48500100300",
            "primary": True,
            "label": "mobile",
        }
    ],
    "tags": [{"id": "tag-1", "name": "VIP", "color": "#00a6a6"}],
    "customFields": {"customerNumber": "42"},
    "createdAt": "2026-09-26T00:00:00Z",
    "updatedAt": "2026-09-27T00:00:00Z",
}
CALL = {
    "id": "call-1",
    "endpointId": "endpoint-1",
    "endpointName": "Main SIM",
    "endpointPhoneNumber": "+48500100200",
    "gatewayName": "Pi",
    "callerAddress": "+48500100300",
    "contactId": "contact-1",
    "contactName": "Ada Lovelace",
    "state": "ENDED",
    "startedAt": "2026-09-27T00:00:00Z",
    "answeredAt": "2026-09-27T00:00:02Z",
    "endedAt": "2026-09-27T00:00:12Z",
    "durationSeconds": 10,
    "transcript": "Hello",
}
QUEUE_ENDPOINT = {
    "id": "endpoint-1",
    "name": "Main SIM",
    "phoneNumber": "+48500100200",
    "gatewayId": "gateway-1",
    "gatewayName": "Pi",
    "gatewayStatus": "ONLINE",
}
FLOW = {
    "id": "flow-1",
    "name": "Reminder",
    "description": "Reminder flow",
    "publishedVersionId": "flow-version-1",
    "updatedAt": "2026-09-27T00:00:00Z",
}
QUEUE_ITEM = {
    "id": "queue-1",
    "endpointId": "endpoint-1",
    "destination": "+48500100300",
    "flowVersionId": "flow-version-1",
    "flowName": "Reminder",
    "flowVersion": 2,
    "source": "EXTERNAL_API",
    "status": "QUEUED",
    "reason": None,
    "callId": None,
    "notBefore": "2026-09-27T10:00:00Z",
    "timeZone": "Europe/Warsaw",
    "intervalSeconds": 60,
    "createdAt": "2026-09-27T00:00:00Z",
    "updatedAt": "2026-09-27T00:00:00Z",
}


def json_response(data: Any, status: int = 200, **headers: str) -> httpx.Response:
    return httpx.Response(status, json=data, headers=headers)


def api_handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["x-api-key"] == "secret"
    assert request.headers["user-agent"].startswith("simply-connect-python/")
    path = request.url.path.split("/api/v1/external/", 1)[1]
    if path == "endpoints":
        return json_response([ENDPOINT])
    if path == "messages" and request.method == "POST":
        assert request.headers["idempotency-key"]
        assert json.loads(request.content) == {
            "endpointId": "endpoint-1",
            "to": "+48500100300",
            "body": "Hello",
        }
        return json_response(
            {
                "messageId": "message-1",
                "dispatchId": "dispatch-1",
                "commandId": "command-1",
                "status": "QUEUED",
            },
            202,
        )
    if path == "messages":
        assert request.url.params["direction"] == "OUTBOUND"
        assert request.url.params["occurredFrom"].endswith("+00:00")
        return json_response(
            {"items": [MESSAGE], "page": 0, "size": 25, "totalElements": 1, "totalPages": 1}
        )
    if path == "messages/message-1":
        return json_response(
            {
                **MESSAGE,
                "createdAt": "2026-09-27T00:00:01Z",
                "statusHistory": [
                    {
                        "status": "DELIVERED",
                        "eventType": "SEGMENT_DELIVERED",
                        "source": "GATEWAY",
                        "errorCode": None,
                        "occurredAt": "2026-09-27T00:00:02Z",
                        "recordedAt": "2026-09-27T00:00:03Z",
                    }
                ],
            }
        )
    if path == "contacts":
        return json_response(
            {"items": [CONTACT], "page": 0, "size": 30, "totalElements": 1, "hasMore": False}
        )
    if path == "contacts/contact-1":
        return json_response(CONTACT)
    if path == "calls":
        return json_response(
            {"items": [CALL], "page": 0, "size": 25, "totalElements": 1, "totalPages": 1}
        )
    if path == "calls/call-1":
        return json_response(
            {
                "call": CALL,
                "routingFlowId": "flow-1",
                "routingFlowName": "Reminder",
                "routingFlowVersion": 2,
                "timeline": [
                    {
                        "id": "event-1",
                        "kind": "ROUTING",
                        "eventType": "PROMPT_PLAYED",
                        "occurredAt": "2026-09-27T00:00:04Z",
                        "nodeId": "welcome",
                        "nodeLabel": "Welcome",
                        "audioName": "welcome.wav",
                        "durationMs": 1200,
                        "language": "pl",
                        "transcript": None,
                        "payload": {"attempt": 1},
                    }
                ],
            }
        )
    if path == "call-queue/endpoints":
        return json_response([QUEUE_ENDPOINT])
    if path == "call-queue/flows":
        return json_response([FLOW])
    if path == "call-queue" and request.method == "POST":
        body = json.loads(request.content)
        assert body["requestId"]
        assert body["scheduledFor"] == "2026-09-28T09:30:00"
        return json_response(QUEUE_ITEM, 202)
    if path == "call-queue":
        assert request.url.params["descending"] == "true"
        return json_response(
            {"items": [QUEUE_ITEM], "page": 0, "totalElements": 1, "totalPages": 1}
        )
    raise AssertionError(f"Unexpected request: {request.method} {request.url}")


def test_sync_client_covers_external_api() -> None:
    transport = httpx.MockTransport(api_handler)
    with SimplyConnectClient(
        "secret",
        base_url="https://example.test/root/",
        default_sms_endpoint_id="endpoint-1",
        transport=transport,
    ) as client:
        assert client.list_sms_endpoints()[0].phone_number == "+48500100200"
        sent = client.send_sms("+48500100300", "Hello", idempotency_key="order-42")
        assert sent.idempotency_key == "order-42"
        messages = client.list_messages(
            direction="OUTBOUND", occurred_from=datetime(2026, 9, 27, tzinfo=UTC)
        )
        assert messages.items[0].body == "Hello"
        assert client.get_message("message-1").status_history[0].source == "GATEWAY"
        assert client.list_contacts(query="Ada").items[0].channels[0].primary
        assert client.get_contact("contact-1").tags[0].name == "VIP"
        assert client.list_calls(endpoint_id="endpoint-1").items[0].duration_seconds == 10
        assert client.get_call("call-1").timeline[0].payload == {"attempt": 1}
        assert client.list_call_queue_endpoints()[0].gateway_status == "ONLINE"
        assert client.list_published_call_flows()[0].description == "Reminder flow"
        assert client.list_call_queue(descending=True).items[0].status == "QUEUED"
        queued = client.create_call_queue_entry(
            endpoint_id="endpoint-1",
            destination="+48500100300",
            flow_version_id="flow-version-1",
            time_zone="Europe/Warsaw",
            request_id="request-1",
            scheduled_for=datetime(2026, 9, 28, 9, 30),
            interval_seconds=60,
        )
        assert queued.flow_version == 2


@pytest.mark.asyncio
async def test_async_client_covers_external_api() -> None:
    transport = httpx.MockTransport(api_handler)
    async with AsyncSimplyConnectClient(
        "secret", default_sms_endpoint_id="endpoint-1", transport=transport
    ) as client:
        assert (await client.list_sms_endpoints())[0].name == "Main SIM"
        assert (await client.send_sms("+48500100300", "Hello")).status == "QUEUED"
        assert (
            await client.list_messages(
                direction="OUTBOUND", occurred_from=datetime(2026, 9, 27, tzinfo=UTC)
            )
        ).total_elements == 1
        assert (await client.get_message("message-1")).message.id == "message-1"
        assert (await client.list_contacts()).items[0].display_name == "Ada Lovelace"
        assert (await client.get_contact("contact-1")).custom_fields["customerNumber"] == "42"
        assert (await client.list_calls()).items[0].state == "ENDED"
        assert (await client.get_call("call-1")).routing_flow_version == 2
        assert (await client.list_call_queue_endpoints())[0].gateway_name == "Pi"
        assert (await client.list_published_call_flows())[0].name == "Reminder"
        assert (await client.list_call_queue(descending=True)).total_pages == 1
        assert (
            await client.create_call_queue_entry(
                endpoint_id="endpoint-1",
                destination="+48500100300",
                flow_version_id="flow-version-1",
                time_zone="Europe/Warsaw",
                scheduled_for=datetime(2026, 9, 28, 9, 30),
            )
        ).id == "queue-1"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, ValidationError),
        (401, AuthenticationError),
        (403, AuthorizationError),
        (404, NotFoundError),
        (409, IdempotencyConflictError),
        (422, ValidationError),
        (500, ApiError),
    ],
)
def test_api_errors(status: int, expected: type[ApiError]) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response(
            {"title": "Error", "detail": "Something failed", "status": status, "code": "TEST"},
            status,
            **{"x-correlation-id": "correlation-1"},
        )

    with (
        SimplyConnectClient("secret", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(expected) as caught,
    ):
        client.list_sms_endpoints()
    assert caught.value.correlation_id == "correlation-1"
    assert caught.value.problem and caught.value.problem.code == "TEST"


def test_rate_limit_retry_after() -> None:
    transport = httpx.MockTransport(
        lambda _: json_response({"detail": "Slow down"}, 429, **{"retry-after": "12"})
    )
    with (
        SimplyConnectClient("secret", transport=transport) as client,
        pytest.raises(RateLimitError) as caught,
    ):
        client.list_sms_endpoints()
    assert caught.value.retry_after_seconds == 12


def test_unknown_sms_outcome_exposes_same_retry_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lost", request=request)

    with (
        SimplyConnectClient(
            "secret", default_sms_endpoint_id="endpoint-1", transport=httpx.MockTransport(handler)
        ) as client,
        pytest.raises(UnknownOutcomeError) as caught,
    ):
        client.send_sms("+48500100300", "Hello", idempotency_key="order-42")
    assert caught.value.retry_kind == "idempotency_key"
    assert caught.value.retry_key == "order-42"


def test_read_transport_error_is_not_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with (
        SimplyConnectClient("secret", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(TransportError) as caught,
    ):
        client.list_sms_endpoints()
    assert not isinstance(caught.value, UnknownOutcomeError)


def test_unreadable_success_response() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="not json"))
    with (
        SimplyConnectClient("secret", transport=transport) as client,
        pytest.raises(ResponseDecodeError),
    ):
        client.list_sms_endpoints()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SimplyConnectClient(""),
        lambda: SimplyConnectClient("secret", base_url="ftp://example.test"),
        lambda: SimplyConnectClient("secret", timeout=0),
    ],
)
def test_configuration_is_validated(factory: Any) -> None:
    with pytest.raises(ConfigurationError):
        factory()


def test_default_endpoint_and_datetime_rules() -> None:
    transport = httpx.MockTransport(api_handler)
    with SimplyConnectClient("secret", transport=transport) as client:
        with pytest.raises(ConfigurationError):
            client.send_sms("+48500100300", "Hello")
        with pytest.raises(ConfigurationError):
            client.list_messages(occurred_from=datetime(2026, 9, 27))
        with pytest.raises(ConfigurationError):
            client.create_call_queue_entry(
                endpoint_id="endpoint-1",
                destination="+48500100300",
                flow_version_id="flow-version-1",
                time_zone="Europe/Warsaw",
                scheduled_for=datetime(2026, 9, 28, 9, 30, tzinfo=UTC),
            )


def test_invalid_model_is_reported_as_contract_failure() -> None:
    transport = httpx.MockTransport(lambda _: json_response([{"id": 42}]))
    with (
        SimplyConnectClient("secret", transport=transport) as client,
        pytest.raises(ValueError, match="id"),
    ):
        client.list_sms_endpoints()
