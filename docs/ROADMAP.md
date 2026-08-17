# Roadmap to v1.0

Energy Flex Trust Platform treats `1.0.0` as a production-reference release gate,
not a cosmetic version bump. The repository remains a reference implementation:
production deployment still requires institution-specific security architecture,
market/operator integration, independent assurance, operational ownership and
regulatory/legal applicability decisions.

## v0.2 — Trust boundaries — complete

- fail-closed OIDC verification boundary for non-development environments;
- deterministic token verification and role mapping with pinned trust material;
- signed audit checkpoints for independently retained chain-head evidence;
- explicit schema/version compatibility with managed Alembic migrations;
- safe local development defaults and synthetic-only examples.

## v0.3 — Reliable integration — implemented in PR #4

- transactional outbox for dispatch publication;
- queued/pending domain states until outbound acknowledgement is recorded;
- bounded exponential retry, durable downstream idempotency and terminal failure;
- lease expiry and deterministic crash-recovery behavior;
- OpenADR 3 mapping/validation/transport boundary without a conformance claim;
- contract tests that do not require a live VEN/VTN, market or device;
- low-cardinality outbox health signals and deterministic failure injection;
- migration revision `0002_reliable_outbox`.

The gate is complete only after the exact release head is green in CI and the PR is
reviewed/merged. See [Reliable integration](RELIABLE_INTEGRATION.md) for delivery
semantics and residual risk.

## v0.9 — Release-candidate hardening — next

- PostgreSQL migration/rollback/backup-restore regression coverage;
- service-account and least-privilege deployment guidance;
- secret/key rotation, incident, recovery and audit-checkpoint runbooks;
- dependency, SBOM, provenance and container hardening gates;
- threat-model refresh and explicit residual-risk register;
- upgrade compatibility policy for persisted data and public API contracts.

## v1.0 — Production reference release

A `1.0.0` tag is permitted only when all prior gates are complete and CI verifies:

1. supported Python and PostgreSQL paths;
2. deterministic identity, authorization and idempotency behavior;
3. migration and recovery compatibility;
4. signed checkpoint verification and evidence integrity;
5. outbound publication safety and replay controls;
6. package/container provenance and security scanning;
7. documented upgrade, rollback, key-rotation and incident procedures;
8. explicit non-claims for market certification, regulatory acceptance and live
   physical-asset safety.

## Non-claims

The roadmap does not claim OpenADR certification, market participation approval,
DORA/NIS2/ISO compliance, grid-code conformity, settlement acceptance, device
security, or safe control of physical energy assets. Those conclusions require
external systems, authoritative evidence and accountable human review.
