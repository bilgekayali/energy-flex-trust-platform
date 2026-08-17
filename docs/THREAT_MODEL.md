# Threat model

## Scope

This model covers the v0.2 coordination API, offline OIDC verification boundary,
relational database and migration lifecycle, audit chain, signed checkpoint
evidence, settlement evidence manifest, read-only synthetic dashboard, and outbound
dispatch port. The default dispatch adapter is a no-op; live grid devices and market
integrations remain outside the current trust boundary.

## Assets to protect

- authority to reserve and dispatch capacity;
- authenticated actor identity and effective Energy Flex role;
- integrity of asset, offer, reading, and settlement data;
- uniqueness and ordering of materially significant commands;
- provenance linking decisions to verified actors and inputs;
- integrity and continuity of the audit event stream;
- integrity of independently retained audit checkpoints;
- database schema/version compatibility;
- availability of the coordination and evidence service;
- confidentiality of future commercially sensitive positions and readings.

## Trust boundaries

1. Institution identity provider to issued access token
2. Client to offline pinned-JWKS verification
3. Verified actor identity to API authorization policy
4. Application transaction to database
5. Operator-managed migration lifecycle to application startup
6. Database event stream to audit verifier
7. Verified audit head to checkpoint signer and external checkpoint retention
8. Domain service to dispatch adapter
9. Platform to future market or device network
10. Bundled synthetic fixture to read-only operations dashboard

## STRIDE analysis

| Threat | Example | v0.2 control | Residual risk / production control |
|---|---|---|---|
| Spoofing | Caller claims `market_operator` or forges a token | Non-development runtimes require OIDC; issuer/audience/signature/time claims and one exact role are verified against locally pinned keys | Upstream IdP compromise, account takeover, JWKS distribution error and entitlement lifecycle remain external controls |
| Tampering | Reading, audit payload, migration state or checkpoint is altered | Meter fingerprints, evidence hashes, hash-linked audit events, exact Alembic revision check and Ed25519 checkpoint signatures | A fully privileged DB/application compromise can rewrite data between externally retained checkpoints; secure backup, external anchoring and privileged-access monitoring remain required |
| Repudiation | Operator denies issuing a dispatch | Verified OIDC subject, correlation/idempotency evidence, audit event and signed checkpoint can bind the recorded sequence | Does not prove the human behind a compromised account; trusted IdP assurance, MFA and institution-owned signing/key custody remain required |
| Information disclosure | Competitor reads another participant's positions | API surface is narrow and dashboard uses bundled synthetic data only | Multi-tenant isolation, row-level authorization, encryption, secret management and access logging are not yet implemented as production controls |
| Denial of service | Request flood, oversized input, database outage or stuck publisher | Typed contracts, transactional boundaries and fail-closed startup configuration reduce ambiguous failure | Gateway limits, quotas, backpressure, transactional outbox, observability, SLOs and tested recovery are v0.3/v0.9 work |
| Elevation of privilege | Owner attempts settlement or token carries multiple roles | Closed role enum, separation-of-duties checks, and OIDC boundary requires exactly one supported role | Entitlement approval/review, privileged operator separation and tenant-scoped authorization remain institution responsibilities |

## Abuse and failure cases tested

- changed payload replayed with the same idempotency key;
- reservation or dispatch above authorized capacity;
- dispatch outside the offered time window;
- settlement by the same identity that reserved/dispatched;
- duplicate meter reading;
- settlement without qualifying evidence;
- offer from a suspended asset;
- mutation of a committed audit payload;
- OIDC token with a wrong audience;
- OIDC token with an ambiguous or unsupported role;
- non-development startup using caller-asserted development headers;
- signed checkpoint whose chain head is modified after signing;
- checkpoint signed by an untrusted key;
- checkpoint attempt over an invalid audit chain;
- managed application startup against an unmigrated or wrong-revision database;
- migration upgrade and downgrade lifecycle on the reference schema.

## Key custody and audit checkpoint boundary

`Ed25519SoftwareSigner` exists to exercise the signing contract in tests and
controlled reference deployments. It is not a recommendation to persist a
production private key in the application or database. Production deployments
should implement the signer protocol using institution-owned KMS/HSM or another
segregated signing service.

A valid checkpoint does not make the database immutable. Tail-truncation detection
requires the checkpoint artifact or its digest to be retained outside the database
and outside the same administrative compromise domain.

## Explicit non-goals in v0.2

- protection against a fully compromised application, database, IdP and checkpoint
  custody system acting together;
- automatic OIDC discovery or remote JWKS retrieval;
- tenant-level database row isolation or universal authorization policy;
- production secret/key provisioning and rotation;
- transactional external dispatch publication or guaranteed delivery;
- market-specific baseline, tolerance, netting, settlement or dispute rules;
- real-time device safety controls;
- OpenADR conformance or certification;
- DORA, NIS2, ISO, grid-code or market compliance certification;
- legal admissibility or absolute non-repudiation of evidence.

## Next threat-model gate

v0.3 must revisit the model when transactional outbound publication and OpenADR
mapping are added. That review must cover duplicate delivery, retry storms,
malformed/hostile external messages, destination authentication, SSRF/egress scope,
queue poisoning, dead-letter handling, reconciliation and operator emergency stop.
