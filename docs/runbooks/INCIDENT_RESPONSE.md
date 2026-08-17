# Incident-response runbook

This runbook covers platform trust-boundary incidents. It supplements, rather than
replaces, the institution's incident-management, safety, legal and regulatory
procedures.

## Incident classes

- identity or entitlement compromise;
- suspected database mutation or unauthorized DDL;
- dispatch destination compromise, unexpected delivery or retry storm;
- audit-chain/checkpoint verification failure;
- settlement evidence mismatch;
- signing/JWKS/database credential exposure;
- vulnerable or tampered build/dependency/container artifact;
- backup/restore failure or data-loss event.

## Immediate containment

Choose controls according to the affected boundary:

- **Dispatch uncertainty:** stop the production outbox publisher/egress first. The
  API may remain read-only or partially available only if institutional policy
  allows it.
- **Identity compromise:** revoke affected IdP sessions/credentials and remove
  compromised trust keys or entitlements.
- **Database compromise:** isolate the database, preserve storage/log snapshots and
  disable mutation credentials. Do not run repair SQL before evidence capture.
- **Signing-key compromise:** disable the compromised signer, preserve public keys
  and historical checkpoints, and begin emergency rotation.
- **Supply-chain compromise:** stop deployment of the affected artifact and retain
  its digest, SBOM and GitHub attestation evidence.

## Evidence preservation

Preserve, with hashes and timestamps where applicable:

- application and database logs;
- deployment commit/image/package digest;
- current and prior migration revision;
- audit-chain verification output;
- externally retained audit checkpoints;
- relevant outbox rows, attempts and destination acknowledgements;
- OIDC `kid`/issuer/audience configuration without copying private secrets;
- SBOM, SHA-256 files and build attestations;
- backup identifiers and recovery-test results.

Do not treat the database audit chain as the sole evidence source when the database
itself is suspected of compromise.

## Investigation questions

1. Which trust boundary failed first?
2. Was any dispatch externally delivered, duplicated or missed?
3. Does the full local audit chain verify?
4. Does its head agree with the latest independently retained checkpoint expected to
   be present?
5. Are settlement evidence hashes still reproducible?
6. Which identities and credentials had access during the affected window?
7. Which release artifact and dependencies were running?
8. Is the restored/rebuilt environment derived from evidence predating the
   compromise?

## Recovery

- Recover PostgreSQL using `RECOVERY.md` when data integrity/availability is in
  question.
- Rotate affected trust material using `KEY_ROTATION.md`.
- Use `OUTBOX_REDRIVE.md` only after external destination reconciliation.
- Validate the exact migration revision, OIDC trust boundary, audit chain, evidence
  hashes and runtime DB privileges before resuming normal service.
- Resume outbound dispatch last when the incident involved uncertain destination or
  delivery state.

## Closure evidence

Record root cause, affected interval, material actions, external dispatch outcome,
data/evidence integrity result, credential rotations, recovery artifact digests,
control changes, residual risk, accountable approvers and follow-up owners.

## Non-claims

The repository does not determine whether an event is legally reportable, a major
DORA/NIS2 incident, a grid safety event or a market breach. Those classifications
require the institution's authoritative legal, regulatory and operational process.
