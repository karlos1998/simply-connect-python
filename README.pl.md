# Simply Connect dla Pythona

Oficjalny, typowany SDK do External API Simply Connect. To jedna paczka dla zwykłego Pythona,
Django, Flask, FastAPI, Starlette i workerów — nie trzeba instalować osobnej integracji dla każdego
frameworka.

## Instalacja

```bash
python -m pip install \
  https://github.com/karlos1998/simply-connect-python/releases/download/v0.1.0/simply_connect-0.1.0-py3-none-any.whl
```

Paczka obsługuje Python 3.11, 3.12, 3.13 i 3.14. Nazwa projektu w PyPI to `simply-connect`; zwykłe
`pip install simply-connect` zostanie uruchomione po jednorazowym skonfigurowaniu Trusted Publishing
przez właściciela projektu.

## Pierwszy SMS

W panelu Simply Connect utwórz klucz API z uprawnieniami `SMS_SEND` i `ENDPOINTS_READ`, ogranicz go
do właściwej bramki i zapisz sekret w zmiennej środowiskowej.

```python
import os
from simply_connect import SimplyConnectClient

with SimplyConnectClient(
    os.environ["SIMPLY_CONNECT_API_KEY"],
    default_sms_endpoint_id=os.environ["SIMPLY_CONNECT_SMS_ENDPOINT_ID"],
) as client:
    result = client.send_sms(
        "+48500100200",
        "Twoje zamówienie jest gotowe.",
        idempotency_key="zamowienie-1842-gotowe",
    )
    print(result.message_id, result.status)
```

Nie ponawiaj wysyłki z nowym kluczem po timeoutcie. SDK nie wykonuje ukrytych retry; wyjątek
`UnknownOutcomeError` zwraca dokładny `retry_key`, którego należy użyć ponownie.

Klient `AsyncSimplyConnectClient` ma ten sam model i jest przeznaczony m.in. do FastAPI oraz
workerów `asyncio`. Pełne przykłady znajdują się w [instrukcji integracji](docs/integration.md).

