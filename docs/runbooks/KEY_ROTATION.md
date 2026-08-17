# Key and credential rotation runbook

Energy Flex Trust has several independent trust materials. Rotate them separately so
a failure in one trust domain does not silently invalidate another.

## 1. OIDC verification keys

The API consumes an institution-controlled pinned JWKS document and performs no
network discovery or key retrieval.

Recommended rotation sequence:

1. Add the new public JWK with a new `kid` while retaining the currently active key.
2. Deploy the overlapping JWKS to all application instances.
3. Verify tokens signed by both old and new keys against the exact issuer and
   audience.
4. Switch the identity provider to sign new tokens with the new key.
5. Wait at least the maximum accepted token lifetime plus operational safety margin.
6. Remove the retired public JWK from the pinned trust document.
7. Record old/new `kid`, deployment commit, validation evidence and approver.

Never reuse a `kid` for different key material.

## 2. Audit checkpoint signing keys

Production checkpoint private keys belong behind an institution-owned KMS/HSM or
segregated signing service implementing the `CheckpointSigner` protocol.

Rotation sequence:

1. Provision a new signing key and unique `key_id` in the external key system.
2. Add the new public key to the independent checkpoint-verification trust store.
3. Produce and externally retain a test checkpoint with the new key.
4. Switch new checkpoint creation to the new signer.
5. Retain old public verification keys for at least the evidence-retention period of
   checkpoints signed by those keys.
6. Disable/destroy old private signing capability according to institutional key
   policy.

Do **not** re-sign historical checkpoints with a new key. Historical signatures are
part of the evidence chain and should remain verifiable with the original public
keys.

## 3. PostgreSQL credentials

Rotate migrator, API, worker, recovery and auditor credentials independently.

For a runtime identity:

1. Create a new credential/version in the secret manager.
2. Confirm it assumes only the intended database role.
3. Roll application instances to the new credential.
4. Verify normal operation and absence of unexpected privilege failures.
5. Revoke the old credential.
6. Verify the old credential can no longer connect.

The recovery credential should normally remain disabled or inaccessible outside an
approved incident/change window.

## 4. External dispatch credentials

This repository intentionally does not implement a live credentialed dispatch
transport. Any production OpenADR/market/device credential is therefore an
institution-owned integration secret. Its rotation must also validate destination
identity, TLS policy, egress allow-listing and downstream idempotency behavior.

## Emergency rotation

If compromise is suspected, prioritize containment over overlap convenience:
revoke/disable compromised private credentials, stop outbound dispatch if its trust
boundary is uncertain, preserve audit/checkpoint evidence, then restore service
with newly provisioned trust material under the incident-response process.
