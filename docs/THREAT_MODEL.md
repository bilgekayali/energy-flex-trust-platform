# Threat model

## Scope

This model covers the v0.1 coordination API, relational database, audit chain,
evidence manifest, and outbound dispatch port. The default adapter is a no-op; live
grid devices and market integrations are outside the current trust boundary.

## Assets to protect

- authority to reserve and dispatch capacity;
- integrity of asset, offer, reading, and settlement data;
- uniqueness and ordering of material commands;
- provenance linking decisions to actors and inputs;
- availability of the coordination and evidence service;
- confidentiality of future commercially sensitive positions and readings.

## Trust boundaries

1. Client to API
2. API identity assertion to policy logic
3. Application transaction to database
4. Database event stream to verifier
5. Domain service to dispatch adapter
6. Platform to future market or device network

## STRIDE analysis

| Threat | Example | v0.1 control | Residual risk / production control |
|---|---|---|---|
| Spoofing | Caller claims `market_operator` | Role policy is executable | Headers are untrusted; require OIDC, audience/issuer validation and workload identity |
| Tampering | Reading or audit payload is edited | Fingerprints, evidence hashes, audit chain | DB administrator can rewrite hashes; add signed external checkpoints and immutable retention |
| Repudiation | Operator denies issuing dispatch | Actor, correlation key and event recorded | Add verified identity, trusted time and digital signatures |
| Information disclosure | Competitor reads positions | No list/search endpoints in v0.1 | Add tenant isolation, row-level authorization, encryption and access logging |
| Denial of service | Request flood or oversized input | Typed and bounded contracts | Add gateway limits, quotas, backpressure, monitoring and tested recovery |
| Elevation of privilege | Owner attempts settlement | Role and separation-of-duties checks | Central policy, least-privilege scopes and periodic entitlement review |

## Abuse cases tested

- changed payload replayed with the same idempotency key;
- reservation or dispatch above authorized capacity;
- dispatch outside the offered time window;
- settlement by the same identity that reserved/dispatched;
- duplicate meter reading;
- settlement without qualifying evidence;
- offer from a suspended asset;
- mutation of a committed audit payload.

## Explicit non-goals

- protection against a fully compromised application and database acting together;
- market-specific baseline, tolerance, netting, or dispute rules;
- real-time device safety controls;
- OpenADR conformance or certification;
- legal admissibility or non-repudiation of evidence.

