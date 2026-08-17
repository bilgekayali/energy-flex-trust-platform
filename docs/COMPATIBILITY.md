# v1 compatibility and upgrade policy

The v1.0 production-reference release freezes the repository's first stable public
compatibility boundary. This document describes repository guarantees; it does not
replace institution-specific deployment, safety or regulatory review.

## Public HTTP API

The approved v1 `/v1` route set is recorded in `contracts/api-surface-v1.json` and
enforced by CI. The version reported by package metadata, `/health`, generated
OpenAPI information and the release-evidence workflow must resolve to `1.0.0` on the
release candidate.

For the 1.x line:

- additive optional fields/endpoints may be introduced in compatible minor releases
  only when existing clients can safely ignore them;
- removing or renaming endpoints, adding required request fields, changing field
  meaning/types, changing idempotency semantics, or weakening authorization
  semantics requires an explicit major compatibility decision;
- error status codes and idempotency behavior are part of the behavioral contract
  even when exact human-readable error text is not;
- administrative recovery capability remains intentionally outside the public
  `/v1` HTTP surface;
- generated OpenAPI schemas and behavior tests must be reviewed alongside the route
  snapshot before a compatible release is approved.

The route snapshot is intentionally small and reviewable; it is not a substitute
for semantic OpenAPI and behavior review.

## Database schema

Managed application startup requires the **exact expected Alembic head revision**.
The v1.0 reference does not claim mixed-version application instances can safely
operate against one database during a rolling schema change.

Reference deployment choreography:

1. stop or drain writers according to the deployment plan;
2. take and verify required backup/checkpoint evidence;
3. apply Alembic migrations with the dedicated migrator identity;
4. re-apply/review least-privilege grants for new objects;
5. start the new application release;
6. verify managed-schema startup, audit chain and operations health;
7. enable the institution-owned dispatch worker last.

A populated-database downgrade is not automatically safe merely because an Alembic
`downgrade()` exists. The operator must choose application rollback, forward-fix or
database restore based on the actual migration and recovery plan.

## Supported upgrade sources

v1.0 is tested against the versioned migration chain established by v0.2/v0.3 and
the v0.9 release-candidate baseline. Because v1.0 introduces no new database
revision beyond that validated chain, the managed-schema gate remains fail-closed at
the existing expected head.

Deployments skipping intermediate application versions must still apply every
Alembic revision in order and follow the stop/drain choreography above.

## Outbox payloads

New dispatch work uses `energy-flex-dispatch.v1`.

v1.0 **retains exact legacy v0.3 payload parsing** for pending work committed before
an upgrade. Legacy payload support is part of the v1.0 upgrade contract and must not
be removed in a 1.x release unless both conditions are met:

1. supported upgrade paths prove no legacy payload can remain pending, or operators
   are required to prove the queue is empty before upgrade; and
2. the compatibility change is explicitly documented and tested.

Unknown payload versions or malformed/extra/missing fields continue to fail closed.

## Idempotency

Reservation, dispatch and settlement idempotency keys are persisted behavioral
contracts. A release must not reinterpret an existing `(operation, key)` pair.
Terminal dispatch re-drive deliberately retains the original key so downstream
replay protection can remain effective across recovery.

## Audit and evidence formats

Audit-chain canonicalization and existing settlement evidence manifest fields are
integrity-sensitive persisted contracts. A new format must be introduced with an
explicit version rather than silently changing the meaning of an existing hash.

Settlement evidence declaring `schema_version: 1.0` must remain independently
hash-verifiable after any 1.x upgrade and after supported database restore paths.

## Python and PostgreSQL support

v1.0 gates Python 3.11, 3.12 and 3.13 in the main test matrix. The PostgreSQL
recovery gate exercises PostgreSQL 16 and 17 using the repository's deterministic
migration, privilege and dump/restore checks.

These are repository-tested reference paths, not a promise about every operating
system, managed database service, extension or proxy configuration.

## Release rollback decision

Before deploying a release, operators must choose which rollback class applies:

- application rollback without schema rollback;
- forward-fix on the new schema; or
- database restore from verified pre-change backup.

The decision must be made during release planning, not improvised during an
incident.

## Non-claims

Stable v1 compatibility does not establish OpenADR certification, market
acceptance, tenant isolation, safe physical dispatch, regulatory compliance or an
institution-specific production approval.
