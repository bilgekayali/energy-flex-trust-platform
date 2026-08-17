# Compatibility and upgrade policy

v0.9 makes the compatibility boundary explicit before the v1.0 public contract is
frozen. This document describes what the reference implementation guarantees and
what it deliberately does not.

## Public HTTP API

The current `/v1` route set is recorded in
`contracts/api-surface-v0.9.json` and enforced by CI.

For v1.0 and later, the intended policy is:

- additive fields/endpoints may be introduced in compatible minor releases when
  existing clients can ignore them safely;
- removing or renaming endpoints, changing required request fields, changing field
  meaning/types, or weakening authorization semantics requires an explicit major
  compatibility decision;
- error codes and idempotency semantics are part of the behavioral contract even
  when their exact human-readable message text is not;
- administrative recovery capability is intentionally **not** exposed as a public
  `/v1` HTTP endpoint.

The route snapshot is not a complete OpenAPI semantic-diff engine. v1.0 release
review must also inspect generated OpenAPI schemas and behavior tests.

## Database schema

Managed application startup requires the **exact expected Alembic head revision**.
The current reference implementation does not claim mixed-version application
instances can safely operate against one database during a rolling schema change.

Reference deployment choreography:

1. stop or drain writers according to the deployment plan;
2. take and verify the required backup/checkpoint evidence;
3. apply Alembic migrations with the dedicated migrator identity;
4. re-apply/review least-privilege grants for any new objects;
5. start the new application release;
6. verify managed-schema startup, audit chain and operations health;
7. enable the institution-owned dispatch worker last.

A downgrade on populated production data is not automatically safe merely because
Alembic implements a `downgrade()` function. See the recovery runbook.

## Outbox payloads

v0.9 introduces `energy-flex-dispatch.v1` in newly queued dispatch payloads.

To preserve upgrade safety, the v0.9 worker also accepts the exact legacy v0.3
payload shape, which had no `schema_version`. This compatibility exists so work that
was committed immediately before an upgrade can drain normally. Unknown versions or
extra/missing fields fail closed.

The v1.0 release review must decide and document how long legacy v0.3 payload
reading remains supported. Removing it requires proof that no supported upgrade path
can leave those messages pending.

## Idempotency

Reservation, dispatch and settlement idempotency keys are persisted data. A release
must not silently reinterpret an existing `(operation, key)` pair. Terminal dispatch
re-drive deliberately retains the original key so downstream replay protection can
remain effective.

## Audit and evidence formats

The audit hash-chain canonicalization and existing settlement evidence manifest
fields are integrity-sensitive persisted contracts. A new format should be
introduced with an explicit version rather than silently changing the meaning of an
existing hash.

Settlement evidence currently declares `schema_version: 1.0`. Historical manifests
must remain independently hash-verifiable after an application upgrade.

## Python and PostgreSQL support

v0.9 CI gates Python 3.11, 3.12 and 3.13 for the unit/reference test suite. The
PostgreSQL recovery gate exercises PostgreSQL 16 and 17 using Python 3.12.

These are repository-tested reference paths, not a promise about every OS,
extension, managed database service or proxy configuration.

## Release rollback decision

Before deploying a release, operators must know whether rollback means:

- application rollback without schema rollback;
- forward-fix on the new schema; or
- database restore from a pre-change backup.

The choice must be based on the actual migration/data change, not selected during an
incident by assumption.
