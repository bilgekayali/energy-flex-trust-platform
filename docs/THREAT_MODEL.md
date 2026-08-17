# Threat model

## Scope

This model covers the v0.3 coordination API, offline OIDC verification boundary,
relational database and migration lifecycle, audit chain, signed checkpoint
evidence, settlement evidence manifest, transactional dispatch outbox, bounded
worker retry/lease behavior, OpenADR 3 contract boundary, low-cardinality
operations endpoint, and read-only synthetic dashboard. The default outbound
publisher remains a no-op; live grid devices and market integrations remain outside
the current trust boundary.

## Assets to protect

- authority to reserve and dispatch capacity;
- authenticated actor identity and effective Energy Flex role;
- integrity of asset, offer, reading, dispatch and settlement data;
- uniqueness and ordering of materially significant commands;
- durable outbound idempotency and delivery state;
- provenance linking decisions to verified actors and inputs;
- integrity and continuity of the audit event stream;
- integrity of independently retained audit checkpoints;
- database schema/version compatibility;
- availability of the coordination, delivery and evidence services;
- confidentiality of future commercially sensitive positions and readings.

## Trust boundaries

1. Institution identity provider to issued access token
2. Client to offline pinned-JWKS verification
3. Verified actor identity to API authorization policy
4. Application transaction to database and transactional outbox
5. Outbox worker claim/lease to outbound publisher
6. Outbound publisher to future protocol transport / destination
7. Operator-managed migration lifecycle to application startup
8. Database event stream to audit verifier
9. Verified audit head to checkpoint signer and external checkpoint retention
10. Domain dispatch signal to OpenADR mapper and schema validator
11. Platform to future market or device network
12. Bundled synthetic fixture to read-only operations dashboard

## STRIDE analysis

| Threat | Example | v0.3 control | Residual risk / production control |
|---|---|---|---|
| Spoofing | Caller claims `market_operator` or forges a token | Non-development runtimes require OIDC; issuer/audience/signature/time claims and one exact role are verified against locally pinned keys | Upstream IdP compromise, account takeover, JWKS distribution error and entitlement lifecycle remain external controls |
| Tampering | Reading, audit payload, migration state, checkpoint or queued outbound payload is altered | Meter fingerprints, evidence hashes, hash-linked audit events, signed checkpoints, managed revision checks and database transaction boundaries | A fully privileged application/DB compromise can rewrite data before independently retained evidence; backup, external anchoring and privileged-access monitoring remain required |
| Repudiation | Operator denies issuing a dispatch or worker delivery | Verified subject, durable command idempotency, queued/published audit events and signed checkpoints provide traceable evidence | Does not prove the human behind a compromised account or external destination acknowledgement beyond the adapter reference |
| Information disclosure | Competitor reads participant positions or queue payloads | Public operations endpoint exposes only aggregate low-cardinality counts; dashboard data is synthetic | Multi-tenant isolation, row-level authorization, encryption, secret management and access logging remain production work |
| Denial of service | Request flood, DB outage, poison message or retry storm | Outbound work is decoupled from request latency; worker batch size, retry count, exponential backoff, max delay and terminal dead state are bounded | Gateway quotas, global rate limits, circuit breaking, SLOs, multi-instance capacity planning and production alerting remain required |
| Elevation of privilege | Owner attempts settlement or token carries multiple roles | Closed role enum, separation of duties, exact OIDC role mapping and operations endpoint role checks | Entitlement approval/review, privileged operator separation and tenant-scoped authorization remain institution responsibilities |

## Outbound delivery abuse and failure cases

### Duplicate external delivery

v0.3 is intentionally at-least-once. A worker can publish successfully and crash
before committing local success. After lease expiry another worker can replay the
message. The durable API `Idempotency-Key` is carried into the publisher contract.
Production transports must map it to a destination-side deduplication mechanism;
without that, duplicate external effects remain possible.

### Worker crash or abandoned claim

A claimed message has a unique claim token and lease expiry. A processing message
can be reclaimed only after lease expiry. PostgreSQL row locking with `SKIP LOCKED`
is the intended concurrent-worker primitive; SQLite is not presented as a
production multi-worker concurrency guarantee.

### Poison message / persistent destination failure

Retry is bounded. Exhaustion moves the message to `dead`, rejects the dispatch,
cancels the reservation and records `dispatch.delivery_failed`. Settlement remains
blocked. v0.3 does not automatically requeue a dead message; production recovery
requires an accountable reconciliation/re-drive procedure with authorization and
audit evidence.

### Malformed OpenADR document

Mapping and schema validation are separated from transport. The transport is not
called when validation fails. Normative schema assets are not bundled or
approximated by the repository; production integrations must use reviewed,
version-pinned authoritative materials.

### Destination compromise / egress abuse

The reference implementation contains no credentialed live transport. A production
transport still requires destination authentication, TLS policy, strict egress
allowlisting, timeout/body limits, SSRF-resistant configuration, secret isolation,
certificate lifecycle management and emergency disable controls.

## Abuse and failure cases tested

- changed payload replayed with the same command idempotency key;
- reservation or dispatch above authorized capacity;
- dispatch outside the offered time window;
- settlement before outbound dispatch acknowledgement;
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
- migration upgrade and downgrade lifecycle;
- transient publisher failure followed by bounded retry and success;
- retry-budget exhaustion into fail-closed dead/rejected/cancelled states;
- expired worker lease recovery;
- operations endpoint authorization and low-cardinality output;
- OpenADR schema rejection before transport;
- downstream idempotency key preservation across the OpenADR contract boundary.

## Key custody and audit checkpoint boundary

`Ed25519SoftwareSigner` exists to exercise the signing contract in tests and
controlled reference deployments. It is not a recommendation to persist a
production private key in the application or database. Production deployments
should implement the signer protocol using institution-owned KMS/HSM or another
segregated signing service.

A valid checkpoint does not make the database immutable. Tail-truncation detection
requires the checkpoint artifact or its digest to be retained outside the database
and outside the same administrative compromise domain.

## Explicit non-goals in v0.3

- protection against a fully compromised application, database, IdP and checkpoint
  custody system acting together;
- automatic OIDC discovery or remote JWKS retrieval;
- tenant-level database row isolation or universal authorization policy;
- production secret/key provisioning and rotation;
- exactly-once outbound delivery;
- automatic operator-approved re-drive of dead messages;
- a credentialed live market/device transport;
- market-specific baseline, tolerance, netting, settlement or dispute rules;
- real-time device safety controls;
- OpenADR conformance or certification;
- DORA, NIS2, ISO, grid-code or market compliance certification;
- legal admissibility or absolute non-repudiation of evidence.

## Next threat-model gate

v0.9 must revisit production deployment and recovery controls: PostgreSQL failure
and restore testing, tenant isolation, service-account privileges, secret/key
rotation, destination authentication, egress restrictions, alert thresholds,
reconciliation/re-drive authorization, dependency/SBOM/provenance controls,
container hardening, incident response and operator emergency-stop procedures.
