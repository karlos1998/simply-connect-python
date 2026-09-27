"""Verify that the canonical OpenAPI document still contains the SDK surface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT = Path("../modern-simply-connect-api/contracts/openapi/v1/openapi.json")

REQUIREMENTS = [
    ("paths", "/api/v1/external/messages", "post", "responses", "202"),
    ("paths", "/api/v1/external/messages", "get", "responses", "200"),
    ("paths", "/api/v1/external/messages/{messageId}", "get"),
    ("paths", "/api/v1/external/endpoints", "get"),
    ("paths", "/api/v1/external/contacts", "get"),
    ("paths", "/api/v1/external/contacts/{contactId}", "get"),
    ("paths", "/api/v1/external/calls", "get"),
    ("paths", "/api/v1/external/calls/{callId}", "get"),
    ("paths", "/api/v1/external/call-queue", "get", "responses", "200"),
    ("paths", "/api/v1/external/call-queue", "post", "responses", "202"),
    ("paths", "/api/v1/external/call-queue/endpoints", "get"),
    ("paths", "/api/v1/external/call-queue/flows", "get"),
    ("components", "schemas", "ExternalSmsRequest"),
    ("components", "schemas", "SmsSendResult"),
    ("components", "schemas", "ExternalMessagePage"),
    ("components", "schemas", "ExternalMessageDetails"),
    ("components", "schemas", "ExternalContactPage"),
    ("components", "schemas", "ExternalCallPage"),
    ("components", "schemas", "ExternalCallDetails"),
    ("components", "schemas", "ExternalCallQueuePage"),
    ("components", "schemas", "ExternalCallQueueRequest"),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONTRACT
    document: Any = json.loads(path.read_text(encoding="utf-8"))
    missing: list[tuple[str, ...]] = []
    for requirement in REQUIREMENTS:
        value = document
        for segment in requirement:
            if not isinstance(value, dict) or segment not in value:
                missing.append(requirement)
                break
            value = value[segment]

    parameters = document["paths"]["/api/v1/external/messages"]["post"].get("parameters", [])
    if not any(
        parameter.get("name") == "Idempotency-Key" and parameter.get("in") == "header"
        for parameter in parameters
        if isinstance(parameter, dict)
    ):
        missing.append(("paths", "/api/v1/external/messages", "post", "Idempotency-Key"))

    if missing:
        print("The canonical External API contract is missing:", file=sys.stderr)
        for requirement in missing:
            print(f"- {' -> '.join(requirement)}", file=sys.stderr)
        return 1
    print("Simply Connect External API contract is compatible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
