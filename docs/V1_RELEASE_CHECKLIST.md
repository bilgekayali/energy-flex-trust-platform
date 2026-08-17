# v1.0 production-reference release checklist

A `v1.0.0` tag is permitted only after this checklist is reviewed against the exact
release commit. The term **production reference** describes the engineering quality
of the repository; it does not approve any particular institution, market, device or
regulatory deployment.

## A. Exact release identity

- [ ] Release candidate commit SHA is recorded in the release notes.
- [ ] Package version, FastAPI/OpenAPI version and OCI image version resolve to
      `1.0.0` on that exact commit.
- [ ] Release artifact SHA-256, SPDX SBOM and GitHub artifact attestation are
      retained for the exact wheel/image build.
- [ ] No release artifact is rebuilt from a different commit after approval.

## B. Supported runtime gates

- [ ] Main CI is green on Python 3.11, 3.12 and 3.13.
- [ ] Ruff and bytecode compilation are green.
- [ ] Full pytest suite meets the configured coverage floor.
- [ ] OIDC/OpenADR trust-boundary no-network checks are green.
- [ ] PostgreSQL recovery gate is green on PostgreSQL 16 and 17.
- [ ] Hardened container starts as UID/GID 10001 with a read-only filesystem,
      dropped capabilities and `no-new-privileges` in the release-evidence gate.

## C. Database and recovery

- [ ] Alembic upgrade to the expected head succeeds from every supported prior
      release schema in the documented upgrade path.
- [ ] Empty-database `upgrade -> downgrade -> upgrade` mechanics are green.
- [ ] PostgreSQL dump/restore drill preserves settlement amount, evidence hash,
      audit head/count and published outbox state.
- [ ] Production backup encryption, retention, restore cadence, RPO and RTO have
      accountable institution-specific owners; repository CI does not claim them.
- [ ] Deployment plan chooses in advance between application rollback,
      forward-fix and database restore for each data-changing migration.

## D. Identity and authorization

- [ ] Non-development API runtime fails closed unless OIDC mode is configured.
- [ ] OIDC issuer, audience, time claims, approved algorithm and exactly one
      application role are verified against institution-controlled pinned JWKS.
- [ ] JWKS/key rotation procedure is reviewed and tested by the deploying
      institution.
- [ ] Migrator, API, worker, recovery and auditor database identities are separate.
- [ ] PostgreSQL role matrix CI proves required grants and prohibited grants on both
      supported PostgreSQL versions.
- [ ] Production recovery tooling derives accountable operator identity from an
      authenticated/PAM-controlled session; CLI `--actor-id` alone is not accepted
      as proof of human identity.

## E. Dispatch reliability and safety boundary

- [ ] Dispatch API success means durably queued, not externally delivered.
- [ ] Outbox delivery remains at-least-once and preserves the durable downstream
      idempotency key across retries and authorized re-drive.
- [ ] Retry, lease expiry and terminal dead-state behavior are tested.
- [ ] Settlement remains blocked until successful publication acknowledgement is
      durably finalized.
- [ ] Built-in Noop publisher cannot run as a production worker.
- [ ] Any institution-owned live publisher has documented destination
      authentication, TLS policy, egress allow-listing, schema validation and
      downstream deduplication evidence before use.
- [ ] Terminal re-drive follows `OUTBOX_REDRIVE.md`; no automated infinite re-drive
      loop exists.

## F. Audit and evidence integrity

- [ ] Full audit-chain verification detects mutation/reordering/broken links.
- [ ] Settlement evidence hashes remain reproducible after upgrade and restore.
- [ ] Signed checkpoint verification is green.
- [ ] Production checkpoint signing uses institution-owned KMS/HSM or segregated
      signing service rather than the reference software signer.
- [ ] Checkpoint artifacts/digests required for tail-truncation detection are
      retained outside the primary database compromise domain.

## G. Compatibility contracts

- [ ] Public `/v1` route snapshot matches the approved v1 contract.
- [ ] Generated OpenAPI schemas are reviewed for semantic compatibility, not merely
      route presence.
- [ ] Existing idempotency records are not reinterpreted by the release.
- [ ] Historical settlement evidence remains hash-verifiable.
- [ ] Pending outbox messages from every supported upgrade source can be parsed and
      safely drained, or the deployment plan proves the queue is empty before
      upgrade.
- [ ] Any removal of legacy v0.3 outbox-payload support has explicit upgrade-path
      evidence.

## H. Supply-chain security

- [ ] CodeQL security-extended analysis is green on the exact release commit.
- [ ] Runtime dependency audit and `pip check` are green.
- [ ] Dependabot is configured for Python, Docker and GitHub Actions ecosystems.
- [ ] SBOM describes the installed release environment and is retained with the
      release artifact.
- [ ] Build/deploy process records immutable artifact digests.
- [ ] GitHub Action reference policy is dispositioned: commit-SHA pinning is either
      implemented or explicitly accepted as residual risk with an owner.
- [ ] Container base-image digest/pinning policy is dispositioned before an
      institution treats the reference image as deployable production material.

## I. Operations and incident readiness

- [ ] Database recovery runbook reviewed.
- [ ] Outbox terminal re-drive runbook reviewed.
- [ ] OIDC/checkpoint/database/external-dispatch key rotation runbook reviewed.
- [ ] Incident-response runbook reviewed.
- [ ] Monitoring/alert ownership exists for outbox backlog/dead state, auth failures,
      database privilege anomalies, backup failure and audit/checkpoint failures.
- [ ] Rate limiting, gateway/WAF, abuse protection and service SLOs are supplied by
      the deployment environment where required.

## J. Residual-risk disposition

Every entry in `RESIDUAL_RISK.md` must have an explicit release disposition:

- `closed` — engineering evidence removes the stated risk;
- `accepted` — accountable owner accepts it for the stated use;
- `transferred` — another authoritative control/system owns it; or
- `out_of_scope` — excluded from the reference release with rationale.

A blank/unreviewed risk is a release blocker.

## K. Explicit non-claims

The release notes and README must continue to state that repository evidence alone
does **not** establish:

- OpenADR certification or conformance;
- electricity-market participation/settlement acceptance;
- safe control of a physical energy asset;
- DORA, NIS2, ISO or grid-code compliance/certification;
- tenant isolation where it has not been implemented;
- legal admissibility or absolute non-repudiation;
- institution-specific production approval.

## Release decision

The final release record should identify the exact commit, evidence workflow runs,
artifact digests, residual-risk dispositions and accountable reviewer(s). A green
CI badge by itself is not authorization to create `v1.0.0`.
