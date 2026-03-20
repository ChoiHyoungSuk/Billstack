# Billstack

Billstack minimal vertical slice with CLI + HTTP service for Railway deployment.

## Local CLI

```bash
python3 app/main.py --client "Acme Co" --project "Landing Page" --hourly-rate 100 --hours 5.5 --tax-rate 0.1
```

## Local Server

```bash
python3 app/main.py --serve
```

- `GET /health` -> health check
- `POST /invoice` -> invoice summary JSON

Example:

```bash
curl -sS -X POST http://localhost:8000/invoice \\
  -H "Content-Type: application/json" \\
  -d "{\"client\":\"Acme Co\",\"project\":\"Landing Page\",\"hourly_rate\":100,\"hours\":5.5,\"tax_rate\":0.1}"
```
