# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### v1.0 production-reference release

- Staged package/runtime/OpenAPI/container version `1.0.0` without creating a tag
  before exact-head release approval.
- Frozen stable public `/v1` route contract in `contracts/api-surface-v1.json`.
- Defined v1 compatibility policy for API behavior, idempotency, persisted evidence,
  database migration choreography and legacy outbox queue draining.
- Retained exact v0.3 legacy outbox payload parsing as part of the v1.0 upgrade
  contract while new messages remain `energy-flex-dispatch.v1`.
- Added machine-readable `RELEASE_RECORD.json` generation binding exact Git commit,
  wheel SHA-256, SPDX SBOM SHA-256, hardened container image ID and reproducible
  build epoch.
- Dispositioned every residual risk R-01 through R-15 with accountable owner roles;
  institution-specific controls remain transferred/out of scope rather than falsely
  reported as closed.
- Added explicit v1 release-decision governance requiring all release workflows to
  be green on one reviewed SHA and push-only provenance/SBOM attestations after
  merge.
- Preserved the temporary, expiring `cryptography` PYSEC-2026-3552 exception while
  upstream 50.0.0 remains unavailable; affected PKCS#7 decrypt APIs remain forbidden
  by CI and the exception expires 2026-09-30.
- Preserved explicit non-claims for OpenADR certification, market acceptance,
  regulatory compliance, tenant isolation, exactly-once external effects and safe
  physical-asset control.

### v0.9 release-candidate hardening

- Staged package/runtime version `0.9.0` without creating a release tag.
- PostgreSQL 16/17 recovery gate covering migration, deterministic workflow seed,
  `pg_dump`/isolated restore, audit/evidence/outbox verification and empty-database
  downgrade/upgrade mechanics.
- Reference PostgreSQL least-privilege matrix separating migrator, API, worker,
  recovery and auditor identities, with CI assertions for required and prohibited
  privileges.
- Dedicated `recovery_operator` application role and controlled terminal dispatch
  re-drive that preserves the original idempotency key and emits audit evidence.
- Production fail-closed worker boundary: the built-in no-op publisher is limited
  to development/test; production-like runtimes require an injected
  institution-owned publisher.
- Versioned `energy-flex-dispatch.v1` outbox payloads while retaining exact v0.3
  legacy-payload parsing for safe queue draining during upgrade.
- Public HTTP route snapshot and compatibility tests for the v0.9 `/v1` surface.
- Multi-stage non-root container build and hardened reference compose profile with
  read-only filesystems, dropped Linux capabilities and `no-new-privileges`.
- Runtime dependency audit, `pip check`, CodeQL security-extended analysis,
  Dependabot configuration, SPDX 2.3 SBOM, artifact SHA-256 and GitHub build/SBOM
  attestation workflow.
- Raised `cryptography` to the released 49.x line after runtime audit findings.
  PYSEC-2026-3552 remains an explicit temporary exception because its upstream fix
  is 50.0.0, which is not yet released; CI expires the exception and forbids the
  affected PKCS#7 EnvelopedData decrypt APIs while it exists.
- Database recovery, terminal outbox re-drive, key/credential rotation and incident
  response runbooks.
- Explicit least-privilege, compatibility and residual-risk documentation.
- Evidence-gated `v1.0` release checklist.

### v0.3 reliable integration

- Transactional dispatch outbox committed atomically with domain, idempotency and
  audit state.
- Explicit `queued` / `dispatch_pending` states that keep settlement fail-closed
  until outbound publication is acknowledged.
- Bounded exponential retry, worker leases, expired-lease recovery and terminal
  dead-message handling.
- Durable downstream idempotency keys for at-least-once outbound delivery.
- Deterministic outbound failure injection for retry and recovery tests.
- Low-cardinality outbox operations endpoint.
- OpenADR 3 mapping, schema-validation and transport protocols with explicit
  non-conformance boundary.
- Alembic revision `0002_reliable_outbox` and exact managed-schema startup gate.
- Safe bounded local outbox worker entry point.

### v0.2 trust boundaries

- Offline, pinned-JWKS OIDC identity verification for non-development runtimes.
- Fail-closed runtime configuration rejecting caller-asserted development identity
  outside development/test.
- Ed25519-signed audit checkpoints and provider-neutral KMS/HSM signer interface.
- Versioned Alembic schema baseline and managed-schema verification.
- Credential-free read-only operations dashboard with synthetic scenarios.

### Foundation

- FastAPI coordination workflow for assets, offers, reservations, dispatches,
  meter evidence, settlements and audit verification.
- PostgreSQL-compatible SQLAlchemy persistence with a safe SQLite default.
- Idempotency controls, role/ownership policy and settlement separation of duties.
- Hash-linked audit events and content-hashed settlement evidence manifests.
- Safe outbound protocol ports and synthetic/no-op reference adapters.
