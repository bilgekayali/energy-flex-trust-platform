# Database recovery runbook

This runbook defines the reference recovery sequence for PostgreSQL-backed Energy
Flex Trust deployments. RPO and RTO are deployment-specific objectives and are not
claimed by the repository.

## Preconditions

- a documented backup schedule and retention policy;
- encrypted backup storage outside the primary database failure domain;
- access to the exact application release and Alembic migration set used by the
  backup;
- externally retained audit checkpoint artifacts or digests when tail-truncation
  detection is required;
- a dedicated recovery environment that cannot publish to live dispatch targets.

## Backup

Use a PostgreSQL-native logical or physical backup method appropriate to the
institution. The CI reference gate uses a custom-format `pg_dump` with ownership and
ACL metadata excluded so restoration can occur under a controlled destination
owner.

For each backup, retain at least:

- database/server version;
- application version and Git commit;
- current Alembic revision;
- backup SHA-256;
- last externally retained audit checkpoint identifier/digest;
- creation time and backup operator/job identity.

## Restore validation

1. Restore into a new isolated database. Never test a restore by overwriting the
   only production copy.
2. Start with outbound dispatch egress disabled.
3. Run `alembic current` and verify the revision expected by the application.
4. Run the application's managed-schema startup check.
5. Recalculate the complete audit chain.
6. Recalculate stored settlement evidence hashes.
7. Compare the restored audit head with the last externally retained checkpoint
   that should be present in the backup.
8. Inspect outbox state. Treat `processing` messages with expired leases as replay
   candidates and `dead` messages as manual-reconciliation cases.
9. Verify OIDC trust configuration and runtime DB roles before opening the API.
10. Re-enable outbound publishing only after destination status and idempotency
    controls have been reconciled.

The automated `PostgreSQL Recovery Gate` performs a deterministic subset of these
checks on PostgreSQL 16 and 17: seed a complete workflow, dump, restore into a new
database, then compare settlement amount, evidence hash, audit event count/head and
published outbox state.

## Migration rollback

A database downgrade is not a general incident rollback mechanism. A migration may
remove columns or tables and therefore destroy information required by the newer
release. The CI gate exercises `upgrade -> downgrade base -> upgrade` only on an
empty probe database to test migration mechanics.

For a populated production database, prefer:

1. application rollback that is explicitly compatible with the current schema;
2. forward-fix migration; or
3. restore from a verified pre-change backup when data-loss consequences are
   understood and approved.

## Recovery evidence

Record the incident/change identifier, backup digest, source and restored database
versions, application commit, migration revision, audit verification result,
checkpoint comparison, outbox reconciliation result and accountable approvers.

## Failure boundary

A successful PostgreSQL restore does not prove that external markets/devices saw
the same dispatches. Database recovery and external dispatch reconciliation are
separate procedures and must be closed independently.
