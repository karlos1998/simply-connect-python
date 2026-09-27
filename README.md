# Simply Connect for Python

The official typed Python SDK for the Simply Connect External API. One package works in ordinary
scripts, background workers, Django, Flask, FastAPI, Starlette, and any other Python application.

- Python 3.11–3.14
- blocking and `asyncio` clients
- typed immutable response models
- SMS, message history, contacts, calls, and the outbound IVR call queue
- RFC 9457 errors with correlation IDs
- explicit unknown-outcome recovery and no automatic mutation retries

## Install

The immutable `v0.1.0` wheel can be installed directly from the GitHub release:

```bash
python -m pip install \
  https://github.com/karlos1998/simply-connect-python/releases/download/v0.1.0/simply_connect-0.1.0-py3-none-any.whl
```

The canonical PyPI project name is `simply-connect`; PyPI installation becomes available after the
publisher enables Trusted Publishing for this repository.

## Send an SMS

Create an API key in the Simply Connect panel with `SMS_SEND` and `ENDPOINTS_READ`, then copy the
permitted endpoint ID.

```python
import os

from simply_connect import SimplyConnectClient

with SimplyConnectClient(
    os.environ["SIMPLY_CONNECT_API_KEY"],
    default_sms_endpoint_id=os.environ["SIMPLY_CONNECT_SMS_ENDPOINT_ID"],
) as client:
    result = client.send_sms(
        "+48500100200",
        "Your order is ready.",
        idempotency_key="order-1842-ready",
    )
    print(result.message_id, result.status)
```

Use a stable business idempotency key for every logical SMS. If the connection fails after a send,
`UnknownOutcomeError.retry_key` contains the only key that is safe to retry.

## Async / FastAPI

```python
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from simply_connect import AsyncSimplyConnectClient

client = AsyncSimplyConnectClient(
    os.environ["SIMPLY_CONNECT_API_KEY"],
    default_sms_endpoint_id=os.environ["SIMPLY_CONNECT_SMS_ENDPOINT_ID"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await client.close()


app = FastAPI(lifespan=lifespan)


@app.post("/orders/{order_id}/notify")
async def notify(order_id: str) -> dict[str, str]:
    result = await client.send_sms(
        "+48500100200",
        "Your order is ready.",
        idempotency_key=f"order-{order_id}-ready",
    )
    return {"message_id": result.message_id, "status": result.status}
```

## Django

Create one long-lived blocking client in a module or service container and close it during process
shutdown. Do not create a new HTTP client per request.

```python
from django.conf import settings
from simply_connect import SimplyConnectClient

simply_connect = SimplyConnectClient(
    settings.SIMPLY_CONNECT_API_KEY,
    default_sms_endpoint_id=settings.SIMPLY_CONNECT_SMS_ENDPOINT_ID,
)
```

The complete setup, scopes, queue examples, error handling, and verification checklist are in the
[Polish guide](README.pl.md) and [integration documentation](docs/integration.md).

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff format --check .
ruff check .
mypy
pytest
python scripts/verify_openapi.py
python -m build
python -m twine check dist/*
```

## Security

Keep API keys server-side. Never put a Simply Connect key in browser JavaScript, a mobile binary,
or a public repository. See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

MIT. Simply Connect is not affiliated with the Python Software Foundation, Django Software
Foundation, or FastAPI.

