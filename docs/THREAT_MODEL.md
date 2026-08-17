# Threat model

## Scope

This model covers the v0.9 coordination API, offline OIDC verification boundary,
managed PostgreSQL lifecycle, least-privilege process identities, audit chain,
signed checkpoint evidence, settlement evidence, transactional dispatch outbox,
bounded worker retry/lease behavior, controlled terminal re-drive, OpenADR 3
contract boundary, release-evidence workflows and hardened reference container.

A credentialed live market/device transport, institution IAM/PAM, external
checkpoint custody and production network controls remain outside the repository's
implemented trust boundary.

## Assets to protect

- authority to reserve, dispatch and settle capacity;
- authenticated actor identity and effective application role;
- recovery/re-drive authority;
- integrity of asset, offer, reading, dispatch and settlement data;
- uniqueness and ordering of materially significant commands;
- original idempotency identity across retry and re-drive;
- provenance linking decisions to verified actors and inputs;
- integrity and continuity of the audit event stream and settlement evidence;
- independently retained audit checkpoint evidence;
- database schema/version and backup/restore compatibility;
- build artifact, dependency and SBOM provenance;
- availability of coordination, delivery and evidence services;
- confidentiality of commercially sensitive positions/readings in a real deployment.

## Trust boundaries

1. Institution identity provider → issued access token
2. Client → offline pinned-JWKS verification
3. Verified identity → application authorization policy
4. API process identity → least-privilege PostgreSQL role
5. Application transaction → database and transactional outbox
6. Outbox worker DB identity → claim/finalization state
7. Worker → institution-owned outbound publisher
8. Publisher → mapping / authoritative-schema validation / transport
9. Transport → external market/device destination
10. Recovery operator/PAM process → dedicated recovery application and DB authority
11. Operator-controlled migration identity → schema lifecycle
12. Database → backup/restore system
13. Database audit stream → verifier → checkpoint signer → external custody
14. Source/dependencies → CI build → wheel/container/SBOM/attestation
15. Synthetic fixtures → read-only dashboard

## STRIDE analysis

| Threat | Example | v0.9 control/evidence | Residual production/institution control |
|---|---|---|---|
| Spoofing | Caller claims operator/recovery authority or presents forged token | Production-like API requires OIDC; exact issuer/audience/time/signature and one supported role against pinned keys; recovery has separate application/DB role | IdP compromise, MFA, entitlement lifecycle, PAM-backed recovery identity and secure JWKS distribution remain external |
| Tampering | DB rows, queued payload, migration state, backup, audit/checkpoint or build artifact is altered | Hash/evidence verification, exact Alembic head, versioned payload parser, signed checkpoints, dump/restore verification, artifact SHA-256/SBOM/attestation | Fully privileged compromise, backup immutability, external checkpoint custody and protected artifact registry remain institution controls |
| Repudiation | Operator denies dispatch/re-drive/settlement | Verified subject for API operations; durable idempotency; audit events for queued/published/failed/re-drive; signed checkpoint evidence | Compromised human account/PAM or destination acknowledgment cannot be disproved solely by local evidence |
| Information disclosure | Participant reads another participant or queue/error data | Operations endpoint exposes aggregate counts; DB process roles are separated; dashboard synthetic | Tenant isolation/RLS, encryption, logging, data classification and secret management remain deployment-specific |
| Denial of service | Request flood, DB outage, poison message, retry storm, restore failure | Bounded worker batch/retry/delay, terminal dead state, decoupled request/outbound path, PostgreSQL restore drill | Gateway quotas/WAF, circuit breaking, SLOs, capacity/failover planning and production alerting remain required |
| Elevation of privilege | API/worker/recovery process attempts unrelated DB action | CI-verified PostgreSQL role matrix; no general runtime DDL/DELETE; recovery role scoped to re-drive state | DB owner/superuser/PAM governance, host/container escape prevention and tenant-scoped authorization remain external |

## Key abuse and failure cases

### Duplicate external delivery

Delivery is intentionally at least once. A publish can succeed immediately before
local finalization is lost. Lease expiry can then replay the message. The original
idempotency key is preserved through normal retries and authorized terminal
re-drive. A production destination must provide authoritative deduplication; without
it duplicate external effects remain possible.

### Production no-op false success

The reference `NoopDispatchPublisher` can acknowledge without contacting an
external destination, which is useful only for tests. v0.9 prevents the default
worker from selecting it outside `development`/`test`. Production orchestration
must inject an institution-owned publisher. This prevents an accidental reference
adapter from being treated as a live delivery mechanism.

### Terminal re-drive abuse

Blindly resetting a dead message can repeat a financially/physically material
action. v0.9 requires `recovery_operator`, dedicated DB privileges, exact
`dead/rejected/cancelled` state, a specific reason and a replay-risk acknowledgement
in the reference CLI. Re-drive retains the original key and emits
`dispatch.redrive_authorized`.

The CLI actor identifier is audit metadata, not proof of human identity. Production
use still requires authenticated operator/PAM workflow and external destination
reconciliation before authorization.

### Payload format drift during upgrade

v0.3 queued payloads were unversioned. v0.9 writes
`energy-flex-dispatch.v1` but accepts only the exact legacy v0.3 shape as an upgrade
compatibility path. Unknown versions/fields fail closed. Removal of legacy support
requires evidence that supported upgrades cannot leave legacy work queued.

### Database restore inconsistency

A database that merely starts after restore may still have missing/corrupt evidence
or delivery state. PostgreSQL 16/17 CI seeds a complete workflow, dumps/restores to
an isolated database and compares settlement amount, evidence hash, audit count/head
and published outbox state. Production backup encryption, retention and RPO/RTO are
not established by this test.

### Supply-chain compromise

A vulnerable dependency, altered package or unsafe image can bypass application
logic. v0.9 adds CodeQL security-extended analysis, installed-runtime dependency
audit, `pip check`, SPDX runtime SBOM, SHA-256 release evidence, non-root/read-only
container tests and push artifact/SBOM attestations.

Remaining supply-chain risks include mutable action/base-image tag references,
registry compromise and institution deployment tooling; these are tracked in the
residual-risk register.

### Destination compromise / egress abuse

The repository contains no credentialed live transport. Production integration
still requires destination authentication, TLS/certificate policy, egress
allow-listing, timeout/body limits, SSRF-resistant configuration, credential
rotation and emergency stop controls.

## Abuse and failure cases tested or release-gated

- changed payload replay under the same command idempotency key;
- capacity/window/state violations;
- settlement before dispatch acknowledgement;
- separation-of-duties violation;
- duplicate meter reading and missing settlement evidence;
- audit mutation and signed-checkpoint tampering;
- invalid/ambiguous OIDC tokens and production development-header rejection;
- mismatched/unmigrated managed database;
- transient retry, terminal delivery failure and expired lease recovery;
- outbox operations authorization and low-cardinality response;
- OpenADR validation failure before transport;
- production-like no-op worker rejection;
- controlled terminal re-drive plus non-recovery-role denial;
- original idempotency-key preservation across re-drive;
- versioned and exact legacy outbox payload parsing;
- public `/v1` route-surface contract;
- PostgreSQL 16/17 dump/restore integrity;
- PostgreSQL least-privilege required/denied grant matrix;
- hardened non-root/read-only container execution;
- CodeQL/runtime dependency and release-evidence workflows.

## Key custody and audit checkpoint boundary

`Ed25519SoftwareSigner` remains a reference/test implementation of the signer
contract. Production checkpoint private keys should be held behind an
institution-owned KMS/HSM or segregated signing service.

Historical public verification keys must remain available for retained checkpoints.
A valid checkpoint does not make the database immutable; tail-truncation detection
requires independently retained evidence outside the database compromise domain.

## Explicit non-goals / residual risks

The complete engineering register is [RESIDUAL_RISK.md](RESIDUAL_RISK.md). Key
non-goals include:

- protection against simultaneous compromise of application, DB owner, IdP,
  checkpoint custody and deployment supply chain;
- tenant-level row isolation/RLS;
- repository-managed production secrets/PAM;
- exactly-once external delivery;
- credentialed live market/device transport;
- production RPO/RTO or immutable backup guarantee;
- in-process WAF/rate limiting or infrastructure SLOs;
- field-level encryption for classified production data;
- OpenADR certification/conformance;
- DORA/NIS2/ISO/grid-code/market certification;
- legal admissibility or absolute non-repudiation;
- safe control of physical energy assets.

## v1.0 threat-model gate

Before `v1.0.0`, every residual risk must have an explicit disposition and the exact
release commit must satisfy [V1_RELEASE_CHECKLIST.md](V1_RELEASE_CHECKLIST.md).
Production-reference status must not be presented as institution-specific security,
safety, market or regulatory approval.
