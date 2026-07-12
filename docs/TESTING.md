# Testing guide — Karzar backend

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## SQLite vs PostgreSQL

| Mode | When | Command |
|------|------|---------|
| SQLite (default) | Fast local unit tests | `pytest` |
| PostgreSQL | CI parity / JSONB behavior | `USE_POSTGRES_TESTS=1 pytest` |

CI always runs with `USE_POSTGRES_TESTS=1` against Postgres 15 and Redis 7.

Local Postgres example:

```bash
export USE_POSTGRES_TESTS=1
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_SERVER=127.0.0.1
export POSTGRES_PORT=5435
export POSTGRES_DB=karzar_db
export REDIS_HOST=127.0.0.1
pytest
```

## Test layout

| File | Focus |
|------|-------|
| `test_p5_category_admin.py` | Category CRUD + step-up delete |
| `test_p5_product_images.py` | Image add/primary/reorder/delete |
| `test_p5_spec_endpoints.py` | spec-labels, filter-options, templates |
| `test_p5_redis_rate_limit.py` | Redis limiter integration (`@integration`) |
| `test_p5_e2e_checkout.py` | Checkout → payment → tracking (`@integration`) |
| `test_p5_contract.py` | API envelope contract regression |
| `test_p5_performance_smoke.py` | Lightweight latency smoke (`@slow`) |
| `test_zarinpal_provider.py` | Zarinpal HTTP mocks |

## Markers

```bash
pytest -m "not integration and not slow"   # fast local loop
pytest -m integration                      # Redis / E2E flows
```

## Coverage

Minimum **62%** enforced in CI (`--cov-fail-under=62`).

```bash
pytest --cov=app --cov-report=term-missing
```

## Lint & types

```bash
ruff check app tests
mypy app
```

## Pre-commit

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Contract alignment

`tests/test_p5_contract.py` guards shapes expected by the storefront/admin clients
(error envelope, checkout fields, pagination meta). Update this file when the
public API contract changes.
