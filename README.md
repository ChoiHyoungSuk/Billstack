# Billstack

Minimal vertical slice for Billstack: generate invoice summary from CLI inputs.

## Run

```bash
python3 app/main.py --client "Acme Co" --project "Landing Page" --hourly-rate 100 --hours 5.5 --tax-rate 0.1
```

## Test

```bash
PYTHONPATH=. pytest -q tests/test_main.py
```
