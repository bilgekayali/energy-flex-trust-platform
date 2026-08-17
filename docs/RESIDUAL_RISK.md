# v1.0 residual-risk register

This register prevents reference controls from being mistaken for production facts.
Every item has an explicit **reference-release disposition** and accountable owner
role. A disposition applies only to the repository's v1.0 production-reference
release; a deploying institution must perform its own risk acceptance and control
assessment.

Disposition values are `closed`, `accepted`, `transferred`, or `out_of_scope`.

| ID | Residual risk | Current control/evidence | v1.0 disposition | Accountable owner role | Rationale / required deployment action |
|---|---|---|---|---|---|
| R-01 | No credentialed live dispatch transport or destination authentication is shipped | Domain/transport port separation; OpenADR validation-before-transport contract; production Noop worker fails closed | `transferred` | Deploying institution integration/security owner | A real deployment must supply authenticated transport, TLS/destination identity, egress allow-listing and downstream idempotency evidence. The reference release intentionally does not embed market/device credentials. |
| R-02 | No tenant-level row isolation | Application ownership/role checks and least-privilege process identities | `out_of_scope` | Repository maintainer; deploying institution data-platform owner | v1.0 makes no shared-tenancy claim. A deployment using shared persistence must define a tenancy model and add RLS/tenant-scoped authorization before relying on tenant isolation. |
| R-03 | Pinned OIDC JWKS distribution is an operator-controlled configuration path | Offline verifier, exact issuer/audience, RS256/ES256 allow-list, one-role requirement | `transferred` | Deploying institution identity/security owner | Secure JWKS distribution/rotation, IdP assurance, MFA and entitlement lifecycle are authoritative identity-system controls. |
| R-04 | Software checkpoint signer exists and external checkpoint retention is not automated | Signer interface, Ed25519 verification and key-rotation runbook | `transferred` | Deploying institution key-management/audit owner | Production use requires KMS/HSM or segregated signing custody plus independent checkpoint retention/anchoring and monitoring. |
| R-05 | Recovery CLI `--actor-id` is audit metadata, not proof of human identity | Dedicated `recovery_operator` application role, separate DB role, replay acknowledgement and audit event | `transferred` | Deploying institution security-operations/PAM owner | Production recovery must run behind authenticated/PAM-controlled operator identity and approval evidence. CLI metadata alone is not identity proof. |
| R-06 | Runtime dependency ranges are not a hashed source lockfile | Runtime `pip-audit`, `pip check`, CodeQL, Dependabot, build-time SPDX SBOM, exact wheel digest and GitHub attestations | `accepted` | Repository maintainer | v1.0 freezes immutable built-artifact digests and SBOM evidence rather than claiming source-lock reproducibility. Deployments that require deterministic dependency resolution must add reviewed constraints/lock policy and retain deployed digests. |
| R-07 | OpenADR certification/conformance is not established | Explicit schema-validator/transport boundary and non-claims | `out_of_scope` | Deploying institution interoperability/compliance owner | The repository is not an OpenADR certification artifact. Certification/conformance, if required, must use authoritative version-pinned schemas and the applicable external process. |
| R-08 | In-process rate limiting, WAF and DDoS controls are absent | Narrow typed API and bounded worker batches | `transferred` | Deploying institution platform/SRE owner | Gateway/service-mesh rate limits, quotas, abuse controls and SLOs belong to the deployment environment. |
| R-09 | Application-field encryption is not implemented | Database access separation and external secret boundary | `transferred` | Deploying institution data-security owner | Storage/platform encryption and field-level protection must follow institution data classification and threat model. |
| R-10 | Backup encryption, immutable retention and RPO/RTO are deployment-specific | PostgreSQL 16/17 dump/restore integrity drill and recovery runbook | `transferred` | Deploying institution business-continuity/database owner | Production backup platform, encryption, retention, restore cadence and approved RPO/RTO are environment-specific operational controls. |
| R-11 | Database audit data can be rewritten by a sufficiently privileged compromise | Hash-linked events and independently verifiable signed checkpoints | `transferred` | Deploying institution database-security/audit owner | Tail-truncation and privileged rewrite resistance require external checkpoint custody/anchoring, privileged-access controls and DB audit monitoring. |
| R-12 | No claim that local dispatch state equals external physical/market outcome | At-least-once semantics, original idempotency key, terminal reconciliation/re-drive process | `transferred` | Deploying institution market/device operations owner | Authoritative destination reconciliation and physical/market safety controls must establish actual outcome. Local acknowledgement is not proof of physical execution. |
| R-13 | Exact-schema startup limits rolling mixed-version deployments | Fail-closed Alembic revision gate, migration/recovery tests and documented deployment choreography | `accepted` | Repository maintainer | The v1 reference contract assumes stop/drain/migrate/start deployment for data-changing migrations and does not claim zero-downtime mixed-version rollout. Expand-contract migration is required before making that claim. |
| R-14 | Supply-chain workflow actions referenced by version tags may move within the major release | GitHub-owned security/attestation actions, Dependabot update review and exact build evidence | `accepted` | Repository maintainer | v1.0 retains major-version action references as an explicit supply-chain residual risk. High-assurance deployments should pin reviewed action commit SHAs and base-image digests under their software-supply-chain policy. |
| R-15 | `cryptography` PYSEC-2026-3552 remains reported until upstream 50.0.0 is released; affected PKCS#7 EnvelopedData decrypt APIs are outside the implemented platform surface | Dependency floor 49.x; bounded exception expires 2026-09-30; AST guard rejects affected decrypt APIs; runtime audit ignores only this advisory ID | `accepted` | Repository maintainer / security owner | Acceptance is temporary and scoped only to the unused affected API surface. The exception must be removed and the dependency upgraded when the upstream fixed release is available. Expiry or introduction of an affected API is a release blocker. |

## Release interpretation

- `accepted` means the stated residual risk remains visible and bounded for the
  repository's production-reference release; it is not a blanket production-risk
  acceptance for any institution.
- `transferred` means an external authoritative system or accountable deployment
  role must implement and evidence the control before production reliance.
- `out_of_scope` means v1.0 explicitly makes no claim for that capability.
- No item is silently treated as `closed` merely because CI is green.

## Security-advisory exception rule

A security-advisory exception is not closure. `security/advisory-exceptions.json`
contains temporary, expiring scope assertions; an expired exception is a CI failure.
The exception for R-15 cannot be broadened to cover use of the affected PKCS#7
decryption APIs.

## Non-claims

This register is not a regulatory risk assessment, safety case, penetration-test
report or certification record. It is an engineering release-control artifact.
