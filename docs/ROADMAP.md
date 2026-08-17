# Roadmap to v1.0

Energy Flex Trust Platform treats `1.0.0` as a production-reference release gate,
not a cosmetic version bump. The repository remains a reference implementation:
production deployment still requires institution-specific security architecture,
market/operator integration, independent assurance, operational ownership and
regulatory/legal applicability decisions.

## v0.2 — Trust boundaries

- replace caller-asserted development identity with an optional fail-closed OIDC
  verification boundary for non-development environments;
- keep identity verification deterministic and testable by separating token
  verification from role mapping;
- introduce signed audit checkpoints so a previously published chain head can be
  independently verified;
- establish explicit schema/version compatibility and migration guidance;
- preserve safe local development defaults and synthetic-only examples.

## v0.3 — Reliable integration

- transactional outbox for dispatch publication;
- bounded retry/idempotency semantics for external publication;
- OpenADR 3 message mapping behind the existing dispatch port using official,
  version-pinned schemas or contract fixtures;
- contract tests that prove domain behavior does not depend on a live VEN/VTN;
- structured operational metrics and health/readiness signals;
- deterministic failure-injection scenarios for recovery testing.

## v0.9 — Release-candidate hardening

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
