# Least-privilege deployment model

v0.9 separates schema ownership and runtime data access. The objective is to make a
single credential compromise insufficient to perform unrelated platform actions.
This is a reference boundary, not an institution-specific IAM design.

## Database identities

| Identity | Intended capability | Explicitly excluded |
|---|---|---|
| `flextrust_migrator` | Own/apply Alembic DDL during controlled change windows | API traffic, worker polling, day-to-day application use |
| `flextrust_api` | Coordination DML, audit append, idempotency, outbox enqueue | DDL, DELETE, terminal re-drive authority |
| `flextrust_worker` | Claim/finalize outbox, update dispatch/reservation state, append audit | Asset/offer creation, meter submission, settlement, DDL |
| `flextrust_recovery` | Re-arm one terminal dispatch and append recovery audit evidence | Normal coordination DML, DDL, DELETE |
| `flextrust_auditor` | Read-only verification of data, audit and migration state | Any mutation |

`deploy/postgres/least_privilege.sql` contains the reference grants. Login roles,
passwords, certificates and role assumption are deliberately not created by the
repository; those credentials belong in the institution's secret/IAM boundary.

## Operational requirements

1. Bootstrap the database with an administrative identity that is not used by the
   application.
2. Apply migrations while assuming the migrator role.
3. Review and re-apply the runtime grants after every migration that adds or changes
   database objects.
4. Configure separate connection strings for API, worker, recovery tooling and
   audit verification.
5. Do not grant runtime roles membership in the migrator or database-owner roles.
6. Alert on DDL attempted by runtime identities and on use of the recovery identity
   outside an approved incident/change window.

## Application identity boundary

OIDC application roles and PostgreSQL roles solve different problems. OIDC binds a
verified caller to application policy. Database identities restrict what a process
can do after it has crossed the application boundary. One must not be treated as a
substitute for the other.

The `recovery_operator` application role exists only for controlled terminal
re-drive authorization. The reference CLI's `--actor-id` is audit metadata, not
proof of human identity. A production wrapper must derive that identity from an
institution-controlled authenticated operator session and use a dedicated
`flextrust_recovery` database credential.

## Container boundary

`deploy/compose.reference.yml` demonstrates a non-root, read-only API runtime with
all Linux capabilities dropped and `no-new-privileges` enabled. It intentionally
does not start a production outbox worker because this repository does not ship a
credentialed live dispatch transport.

## Non-claims

These grants do not establish tenant isolation, database row-level security,
privileged-access-management approval, regulatory compliance or production
suitability. Those controls depend on the deployment topology and institutional
policy.
