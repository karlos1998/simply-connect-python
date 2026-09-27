# Integration guide

## Scopes

Grant only what the application needs:

| Feature | Required scope |
| --- | --- |
| discover SMS endpoints | `ENDPOINTS_READ` |
| send SMS | `SMS_SEND` |
| list/read messages | `MESSAGES_READ` |
| list/read contacts | `CONTACTS_READ` |
| list/read calls | `CALLS_READ` |
| inspect the outbound call queue | `CALL_QUEUE_READ` |
| discover voice endpoints/flows and enqueue calls | `CALL_QUEUE_WRITE` |

The API key can additionally be restricted to selected physical endpoints. A scope does not bypass
that endpoint allowlist.

## Configuration

Use environment variables or a secret manager:

```dotenv
SIMPLY_CONNECT_API_KEY=sc_live_...
SIMPLY_CONNECT_SMS_ENDPOINT_ID=019...
```

The default API origin is `https://api.simply-connect.ovh`. Pass `base_url` only for a controlled
development environment. The client appends `/api/v1/external` exactly once.

## Reading messages

```python
from datetime import UTC, datetime, timedelta

page = client.list_messages(
    direction="INBOUND",
    occurred_from=datetime.now(UTC) - timedelta(days=1),
    size=50,
)

for message in page.items:
    print(message.remote_address, message.body, message.status)
```

Filter date-times must be timezone-aware. Returned date-times are parsed into `datetime` values.

## Outbound call queue

```python
from datetime import datetime

entry = client.create_call_queue_entry(
    endpoint_id="019...",
    destination="+48500100200",
    flow_version_id="019...",
    request_id="019...",  # stable UUID for retries
    time_zone="Europe/Warsaw",
    scheduled_for=datetime(2026, 10, 1, 9, 30),  # local wall clock, no offset
    interval_seconds=60,
)
```

Discover permitted voice endpoints with `list_call_queue_endpoints()` and immutable published flow
versions with `list_published_call_flows()`.

## Errors and recovery

- `AuthenticationError`: invalid, expired, revoked, or missing key.
- `AuthorizationError`: missing scope or endpoint access.
- `ValidationError`: malformed input; inspect `problem.properties`.
- `IdempotencyConflictError`: a key was reused with different content.
- `RateLimitError`: back off for `retry_after_seconds` when available.
- `UnknownOutcomeError`: the mutation may have reached the API. Retry only with `retry_key`.
- `ResponseDecodeError`: a successful response did not match readable JSON.

Every `ApiError` exposes `status_code`, `correlation_id`, `problem`, and `response_body`. Give the
correlation ID to support; do not log API keys or message bodies by default.

## Controlled verification

1. Call `list_sms_endpoints()` and confirm only expected endpoints are visible.
2. Send one SMS to a number you control with a stable test idempotency key.
3. Save the returned `message_id` and fetch it with `get_message()`.
4. Confirm the expected terminal status before enabling production traffic.
5. Revoke the temporary key if it was created only for verification.

