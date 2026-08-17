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

## v0.3 — Reliable integration — complete

Merged in PR #4. The implemented gate includes:

- transactional outbox for dispatch publication;
- queued/pending domain states until outbound acknowledgement is recorded;
- bounded exponential retry, durable downstream idempotency and terminal failure;
- lease expiry and deterministic crash-recovery behavior;
- OpenADR 3 mapping/validation/transport boundary without a conformance claim;
- low-cardinality outbox health signals and deterministic failure injection;
- migration revision `0002_reliable_outbox`.

See [Reliable integration](RELIABLE_INTEGRATION.md).

## v0.9 — Release-candidate hardening — in progress

The v0.9 branch converts the v0.3 architecture into an independently reviewable
release candidate by adding evidence around deployment, recovery and supply chain:

- PostgreSQL 16/17 migration, dump/restore and integrity regression gates;
- CI-enforced least-privilege separation for migrator, API, worker, recovery and
  auditor database identities;
- production fail-closed no-op worker boundary;
- controlled terminal dispatch re-drive with original idempotency-key preservation;
- versioned outbox payloads with v0.3 queue-drain compatibility;
- public API route contract and persisted-data compatibility policy;
- non-root/read-only hardened reference container/deployment profile;
- runtime vulnerability audit, CodeQL, Dependabot, SPDX SBOM, SHA-256 and GitHub
  build/SBOM attestations;
- database recovery, key rotation, incident response and outbox re-drive runbooks;
- explicit residual-risk register;
- evidence-gated v1.0 release checklist.

A `v0.9.0` tag is not implied by version metadata. The v0.9 gate is complete only
when the exact PR head is green across all release workflows and the PR is reviewed
and merged.

## v1.0 — Production reference release

After v0.9 merges, v1.0 should be a narrow release-hardening pass rather than a new
feature cycle. The exact `v1.0.0` commit must satisfy
[V1 release checklist](V1_RELEASE_CHECKLIST.md), including:

1. supported Python and PostgreSQL paths;
2. deterministic identity, authorization and idempotency behavior;
3. migration, backup/restore and compatibility evidence;
4. signed checkpoint verification and evidence integrity;
5. outbound publication safety, replay and controlled re-drive boundaries;
6. package/container SBOM, provenance, vulnerability and security-analysis gates;
7. documented upgrade, rollback, key-rotation, recovery and incident procedures;
8. explicit disposition of every residual risk;
9. explicit non-claims for market certification, regulatory acceptance and live
   physical-asset safety.

## Non-claims

The roadmap does not claim OpenADR certification, market participation approval,
DORA/NIS2/ISO compliance, grid-code conformity, settlement acceptance, tenant
isolation, device security or safe control of physical energy assets. Those
conclusions require external systems, authoritative evidence and accountable human
review.
