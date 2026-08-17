# v0.9 residual-risk register

This register prevents reference controls from being mistaken for production facts.
Every v1.0 release review must disposition each item as closed, accepted, transferred
or explicitly out of scope with accountable ownership.

| ID | Residual risk | Current v0.9 control/evidence | Required production/v1 decision |
|---|---|---|---|
| R-01 | No credentialed live dispatch transport or destination authentication is shipped | Domain/transport port separation; OpenADR validation-before-transport contract; production Noop worker fails closed | Institution-owned authenticated transport, TLS/destination identity, egress allow-list and downstream idempotency evidence |
| R-02 | No tenant-level row isolation | Application ownership/role checks and least-privilege process identities | Decide tenancy model; add RLS/tenant-scoped authorization where shared persistence requires it |
| R-03 | Pinned OIDC JWKS distribution is an operator-controlled configuration path | Offline verifier, exact issuer/audience, RS256/ES256 allow-list, one-role requirement | Secure JWKS distribution/rotation, IdP assurance, MFA and entitlement lifecycle |
| R-04 | Software checkpoint signer exists and external checkpoint retention is not automated | Signer interface, Ed25519 verification and key-rotation runbook | Institution KMS/HSM signer plus independent retention/anchoring and monitoring |
| R-05 | Recovery CLI `--actor-id` is audit metadata, not proof of human identity | Dedicated `recovery_operator` application role, separate DB role, replay acknowledgement and audit event | Authenticated operator wrapper/PAM workflow and approval evidence |
| R-06 | Runtime dependency ranges are not a hashed source lockfile | Dependency Review, CodeQL, Dependabot, build-time SPDX SBOM, wheel SHA-256 and GitHub attestations | Decide reproducible dependency pin/constraints policy and retain deployed image/package digest + SBOM |
| R-07 | OpenADR certification/conformance is not established | Explicit schema-validator/transport boundary and non-claims | Validate against authoritative version-pinned schemas and external certification/conformance process if required |
| R-08 | In-process rate limiting, WAF and DDoS controls are absent | Narrow typed API and bounded worker batches | Gateway/service-mesh rate limits, quotas, abuse controls and SLOs |
| R-09 | Application-field encryption is not implemented | Database access separation and external secret boundary | Storage/platform encryption plus field-level protection where data classification requires it |
| R-10 | Backup encryption, immutable retention and RPO/RTO are deployment-specific | PostgreSQL 16/17 dump/restore integrity drill and recovery runbook | Production backup platform, encryption, retention, restore cadence and approved RPO/RTO |
| R-11 | Database audit data can be rewritten by a sufficiently privileged compromise | Hash-linked events and independently verifiable signed checkpoints | External checkpoint custody/anchoring, privileged-access controls and DB audit monitoring |
| R-12 | No claim that local dispatch state equals external physical/market outcome | At-least-once semantics, original idempotency key, terminal reconciliation/re-drive process | Authoritative destination reconciliation and market/device safety controls |
| R-13 | Exact-schema startup limits rolling mixed-version deployments | Fail-closed Alembic revision gate and explicit deployment choreography | Adopt stop/drain migration procedure or design/test expand-contract compatibility before claiming zero-downtime rolling upgrade |
| R-14 | Supply-chain workflow actions referenced by version tags may move within the major release | GitHub-owned security/attestation actions and Dependabot update review | Decide commit-SHA pinning policy for all third-party/GitHub Actions before v1.0 release |

## Review rule

A green CI run does not close a residual risk by itself. Closure requires evidence
that addresses the risk statement, an accountable owner and a documented decision.

## Non-claims

This register is not a regulatory risk assessment, safety case, penetration-test
report or certification record. It is an engineering release-control artifact.
