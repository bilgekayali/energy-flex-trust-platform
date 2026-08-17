# v0.2 Trust Boundaries

Energy Flex Trust Platform v0.2 separates three controls that were deliberately
simplified in v0.1: authenticated actor identity, managed schema lifecycle and
externally verifiable audit checkpoints.

## Authenticated identity

Local development and tests may continue to use `X-Actor-ID` and
`X-Actor-Role`. Those headers are policy fixtures, not authentication.

Any environment other than `development` or `test` fails at startup unless:

```text
AUTH_MODE=oidc
OIDC_ISSUER=<exact issuer>
OIDC_AUDIENCE=<exact API audience>
OIDC_JWKS_JSON=<institution-controlled JWKS document>
```

The verifier:

- accepts only RS256 or ES256;
- selects a key by `kid` from the configured local JWKS;
- performs no OIDC discovery, JWKS download or other network access;
- requires issuer, audience, expiry, issued-at, subject and role claims;
- resolves exactly one Energy Flex role;
- fails closed for unknown keys, algorithms, roles or ambiguous role claims.

The default role claim is `energy_flex_role` and the default subject claim is
`sub`. A production deployment is responsible for securely distributing and
rotating the pinned JWKS material and for ensuring the upstream identity provider
issues the intended claims.

## Managed database lifecycle

Development and tests retain `Base.metadata.create_all()` for low-friction local
use. A non-development application process does not create or mutate its schema.
It verifies that:

1. the `alembic_version` table exists;
2. the revision equals the package's expected revision;
3. every required application table exists.

Operators apply the schema before starting the service:

```bash
export DATABASE_URL='postgresql+psycopg://...'
alembic upgrade head
```

A rollback can be rehearsed with:

```bash
alembic downgrade base
```

The initial migration represents the complete v0.1 persistence schema so existing
installations can establish an explicit version baseline before later migrations
change persisted contracts. Production rollback must be paired with an approved
backup/restore plan; a destructive downgrade is not a substitute for recovery.

## Signed audit checkpoints

The database audit stream remains hash-linked and tamper-evident. A signed
checkpoint binds:

- checkpoint contract version;
- signing key identifier;
- audit event count;
- exact chain-head SHA-256 hash;
- UTC issue timestamp.

The checkpoint is signed with Ed25519. Verification uses an explicit map of trusted
key IDs to raw public keys.

`Ed25519SoftwareSigner` exists for tests and controlled reference deployments.
Production key custody should implement the `CheckpointSigner` protocol behind an
institution-owned KMS, HSM or signing service. The platform does not require or
encourage storing production private signing keys in the application repository or
database.

A checkpoint does not make the database immutable. To detect later tail truncation,
checkpoint artifacts or their digests must be retained in an independently
controlled system or external anchor.

## Remaining v1.0 gaps

v0.2 does not yet provide the transactional outbound publication path, OpenADR 3
contract adapter, production observability/recovery gates, SBOM/provenance release
evidence, or independent security review required by the v1.0 roadmap. See
[ROADMAP.md](ROADMAP.md).
