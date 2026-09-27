import os

from simply_connect import SimplyConnectClient

with SimplyConnectClient(
    os.environ["SIMPLY_CONNECT_API_KEY"],
    default_sms_endpoint_id=os.environ["SIMPLY_CONNECT_SMS_ENDPOINT_ID"],
) as client:
    result = client.send_sms(
        os.environ["SMS_TO"],
        "Simply Connect Python SDK test",
        idempotency_key=os.environ["SMS_IDEMPOTENCY_KEY"],
    )
    print(result)
