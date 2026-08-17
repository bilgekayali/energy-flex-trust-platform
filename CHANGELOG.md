# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

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
- Safe no-op dispatch adapter and a protocol boundary for future OpenADR 3 work.
- Docker Compose environment, CI, architecture records, threat model, v0.2 trust
  boundary documentation, and a release-gated roadmap to v1.0.
