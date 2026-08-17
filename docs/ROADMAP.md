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

## v0.9 — Release-candidate hardening — complete

Merged in PR #5. The v0.9 gate added independently reviewable deployment, recovery
and supply-chain evidence:

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

## v1.0 — Production reference release — final gate

The v1.0 branch is deliberately a narrow compatibility/evidence freeze rather than a
new feature cycle. It stages `1.0.0` and must satisfy
[V1 release checklist](V1_RELEASE_CHECKLIST.md) and
[V1 release decision](V1_RELEASE_DECISION.md).

The final release gate includes:

1. stable package/runtime/OpenAPI/container version `1.0.0`;
2. frozen public `/v1` route contract in `contracts/api-surface-v1.json`;
3. supported Python 3.11/3.12/3.13 and PostgreSQL 16/17 gates;
4. migration, backup/restore and compatibility evidence;
5. signed checkpoint verification and evidence integrity;
6. outbound publication safety, replay and controlled re-drive boundaries;
7. package/container SBOM, provenance, vulnerability and security-analysis gates;
8. machine-readable exact release record binding source SHA, wheel/SBOM digests and
   container image identity;
9. explicit disposition of every residual risk;
10. explicit non-claims for market certification, regulatory acceptance and live
    physical-asset safety.

After the final PR is approved and merged, push-triggered provenance/SBOM
attestations must succeed on the exact `main` commit before a `v1.0.0` tag is
created.

## Post-v1 maintenance

The 1.x line should prioritize compatible security/reliability maintenance. Breaking
API, persisted-data or idempotency semantics require an explicit major-version
compatibility decision. The temporary `cryptography` advisory exception must be
removed as soon as the upstream fixed release is available and cannot silently
survive its expiry.

## Non-claims

The roadmap does not claim OpenADR certification, market participation approval,
DORA/NIS2/ISO compliance, grid-code conformity, settlement acceptance, tenant
isolation, device security or safe control of physical energy assets. Those
conclusions require external systems, authoritative evidence and accountable human
review.
