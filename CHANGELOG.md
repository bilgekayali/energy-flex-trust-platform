# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Transactional dispatch outbox committed atomically with domain, idempotency and
  audit state.
- Explicit `queued` / `dispatch_pending` states that keep settlement fail-closed
  until outbound publication is acknowledged.
- Bounded exponential retry, worker leases, expired-lease recovery and terminal
  dead-message handling.
- Durable downstream idempotency keys for at-least-once outbound delivery.
- Deterministic outbound failure injection for retry and recovery tests.
- Low-cardinality outbox operations endpoint for pending, processing, published,
  dead, due and oldest-pending-age signals.
- OpenADR 3 mapping, schema-validation and transport protocols with a
  credential-free recording fixture and explicit non-conformance boundary.
- Alembic revision `0002_reliable_outbox` and exact managed-schema startup gate.
- Safe bounded local outbox worker entry point.
- Pytest failure annotations in CI for diagnosable GitHub Actions failures.
- Offline, pinned-JWKS OIDC identity verification for non-development runtimes.
- Fail-closed runtime configuration that rejects caller-asserted development
  identity headers outside development and test environments.
- Ed25519-signed audit checkpoints with explicit public-key trust verification.
- Provider-neutral checkpoint signer interface for institution-owned KMS/HSM
  integration, with a software signer limited to reference/test use.
- Versioned Alembic schema baseline with upgrade and downgrade regression tests.
- Managed-schema startup verification for revision and required table integrity.
- Credential-free visual operations dashboard with four synthetic trust scenarios.
- Read-only capacity, evidence, control, timeline, and settlement-readiness views.
- FastAPI coordination workflow for assets, offers, reservations, dispatches,
  meter evidence, settlements, and audit verification.
- PostgreSQL-compatible SQLAlchemy persistence with a safe SQLite default.
- Idempotency controls for financially material commands.
- Role policy, ownership checks, and settlement separation of duties.
- Hash-linked audit events and content-hashed settlement evidence manifests.
- Safe no-op dispatch adapter and explicit external protocol boundaries.
- Docker Compose environment, CI, architecture records, threat model, trust
  boundary documentation, reliable-integration documentation and a release-gated
  roadmap to v1.0.

### Changed

- Dispatch publication no longer occurs inline with the API transaction. The API
  records a durable intent and a separate worker performs outbound publication.
- Package version advanced to `0.3.0` for the reliable-integration gate.
