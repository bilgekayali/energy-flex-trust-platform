# Energy Flex Trust Platform

[![CI](https://github.com/bilgekayali/energy-flex-trust-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bilgekayali/energy-flex-trust-platform/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](pyproject.toml)

A secure, auditable reference platform for coordinating distributed energy
flexibility—from asset registration and capacity reservation to dispatch, meter
evidence, and settlement proof.

The project demonstrates how operational decisions can remain traceable and safe
when several organizations exchange data and trigger financially material actions.
It uses only synthetic data and its default dispatch adapter never contacts a live
energy asset.

> **Status:** v0.1 reference implementation. Not production-ready, OpenADR
> certified, or connected to an energy market or physical device.

## Why this project exists

Energy-flexibility workflows cross organizational and technical trust boundaries.
Duplicate requests, conflicting roles, altered readings, and incomplete provenance
can turn an otherwise valid dispatch into an operational or settlement dispute.

Energy Flex Trust makes the critical controls executable:

- idempotent reservation, dispatch, and settlement commands;
- explicit state transitions and capacity checks;
- role policy and settlement separation of duties;
- deduplicated meter readings with deterministic fingerprints;
- append-only, hash-linked audit events;
- reproducible settlement evidence packages;
- a safe outbound adapter boundary for future OpenADR 3 integration.

## Workflow

```mermaid
flowchart LR
    A[Register asset] --> B[Create flex offer]
    B --> C[Reserve capacity]
    C --> D[Issue dispatch]
    D --> E[Record meter evidence]
    E --> F[Calculate settlement]
    F --> G[Verify evidence and audit chain]
```

The main happy path is intentionally small enough to understand and strict enough
to expose the trust decisions that are often hidden in integration code.

## Visual operations dashboard

The credential-free dashboard turns the trust model into an inspectable operations
view. It includes healthy coordination, capacity stress, meter-evidence gap, and
audit-tampering scenarios. Every value is synthetic and the dashboard is read-only:
it never contacts the API, database, a market, meter, or physical asset.

```bash
python -m pip install -e ".[dashboard]"
python app.py
```

Open `http://127.0.0.1:7860`. See the [dashboard guide](docs/DASHBOARD.md) for
the scenario definitions and safety boundary.

## Quick start

### Local Python

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn energy_flex_trust.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI interface.

SQLite is the safe local default. No infrastructure is required.

### PostgreSQL with Docker

```bash
docker compose up --build
```

This starts PostgreSQL 16 and the API at `http://127.0.0.1:8000`.

## Minimal API example

Every protected request carries a development actor identity. These headers model
policy behavior; they are **not authentication**. A production adapter must derive
the actor and role from verified OIDC claims.

Register an asset:

```bash
curl -X POST http://127.0.0.1:8000/v1/assets \
  -H 'Content-Type: application/json' \
  -H 'X-Actor-ID: owner-001' \
  -H 'X-Actor-Role: asset_owner' \
  -d '{
    "external_id": "BATTERY-GB-001",
    "owner_id": "owner-001",
    "asset_type": "battery",
    "capacity_kw": "100",
    "location_code": "GB-LON"
  }'
```

Create an offer with the returned asset ID:

```bash
curl -X POST http://127.0.0.1:8000/v1/offers \
  -H 'Content-Type: application/json' \
  -H 'X-Actor-ID: owner-001' \
  -H 'X-Actor-Role: asset_owner' \
  -d '{
    "asset_id": "<asset-id>",
    "window_start": "2026-08-10T18:00:00Z",
    "window_end": "2026-08-10T19:00:00Z",
    "direction": "decrease",
    "quantity_kw": "80",
    "price_per_kwh": "0.50"
  }'
```

Reservation, dispatch, and settlement endpoints also require an
`Idempotency-Key`. Repeating the same request with the same key returns the same
resource; reusing the key for a changed payload returns `409 Conflict`.

## API surface

| Method | Endpoint | Required role | Purpose |
|---|---|---|---|
| `GET` | `/health` | Public | Runtime health and version |
| `POST` | `/v1/assets` | `asset_owner` | Register a synthetic flexible asset |
| `POST` | `/v1/offers` | `asset_owner` | Offer capacity within the registered limit |
| `POST` | `/v1/offers/{id}/reservations` | `market_operator` | Reserve open capacity idempotently |
| `POST` | `/v1/reservations/{id}/dispatches` | `market_operator` | Record a safe dispatch intent idempotently |
| `POST` | `/v1/meter-readings` | `asset_owner`, `system` | Record and deduplicate interval evidence |
| `POST` | `/v1/reservations/{id}/settlements` | `settlement_analyst` | Calculate settlement with role separation |
| `GET` | `/v1/settlements/{id}/evidence` | Auditor/operator/analyst | Retrieve and verify the evidence manifest |
| `GET` | `/v1/audit/verify` | `auditor` | Recalculate the full audit hash chain |

## Architecture

```mermaid
flowchart TB
    Client[Market participant or operator]
    API[FastAPI contracts and role boundary]
    Service[Transactional coordination service]
    Policy[State, capacity, idempotency and SoD invariants]
    DB[(PostgreSQL / SQLite)]
    Audit[Hash-linked audit stream]
    Port[Dispatch publisher port]
    Noop[Safe no-op adapter]
    Future[Future OpenADR 3 adapter]

    Client --> API --> Service
    Service --> Policy
    Service --> DB
    Service --> Audit --> DB
    Service --> Port
    Port --> Noop
    Port -. explicit future boundary .-> Future
```

See [Architecture](docs/ARCHITECTURE.md),
[API workflow](docs/API_WORKFLOW.md), and
[Threat model](docs/THREAT_MODEL.md) for the detailed design and limitations.

## Trust guarantees in v0.1

- A reservation cannot exceed its offer.
- A dispatch cannot exceed its reservation or escape the offer window.
- A reservation and an offer cannot be dispatched twice.
- Replayed command keys cannot silently change their payload.
- Settlement requires meter evidence fully inside the dispatch window.
- The settlement actor must differ from the reservation and dispatch actor.
- Evidence manifests are content-hashed and point to an audit-chain head.
- Audit mutation, reordering, and non-tail deletion are detectable by full-chain
  verification.

The hash chain is tamper-evident, not tamper-proof. Tail truncation cannot be
detected without a previously anchored head. Production-grade non-repudiation
therefore requires signed checkpoints and an independently controlled anchor.

## Test

```bash
ruff check .
pytest
```

Tests cover the complete workflow, replay behavior, changed-payload conflicts,
separation of duties, suspended assets, meter deduplication, evidence verification,
and deliberate audit tampering.

## Roadmap

- **v0.1:** transactional reference workflow, evidence chain, PostgreSQL deployment;
- **v0.2:** credential-free operations dashboard, followed by versioned migrations,
  OIDC adapter, signed audit checkpoints, and OpenADR 3 contract tests;
- **v0.3:** synthetic multi-asset simulator, observability, and failure injection.

## Standards boundary

OpenADR 3 is a future interoperability target, not a current compliance claim. The
`DispatchPublisher` port isolates domain behavior from external protocols so an
official-schema adapter and certification tests can be added without weakening the
core transaction guarantees.

## License

Apache License 2.0. See [LICENSE](LICENSE).
