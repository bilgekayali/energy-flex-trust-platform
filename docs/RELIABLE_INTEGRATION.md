# Reliable integration — v0.3

v0.3 separates a committed dispatch decision from outbound publication. The API
transaction records domain state, audit evidence, idempotency state and a durable
outbox message together. A separate worker later publishes that message through an
explicit adapter boundary.

## Delivery model

The outbox provides **at-least-once** delivery, not exactly-once delivery.

1. A market operator requests a dispatch with an `Idempotency-Key`.
2. The application validates capacity, time window, state and authorization.
3. One database transaction creates the dispatch as `queued`, moves the
   reservation to `dispatch_pending`, records `dispatch.queued`, stores the command
   idempotency record and inserts the outbound message.
4. The API transaction commits without making a network call.
5. A worker leases a due message and publishes outside the database transaction.
6. On acknowledgement, a second database transaction marks the message
   `published`, the dispatch `issued` and the reservation `dispatched`, then records
   `dispatch.published`.
7. Settlement remains fail-closed until publication is acknowledged.

A worker can crash after the external system accepts a message but before the
local success transaction commits. The lease will eventually expire and the
message can be replayed. Every publisher therefore receives the original durable
idempotency key; a production transport must propagate or map that key to a
reliable downstream deduplication mechanism.

## Retry and terminal failure

Workers use bounded exponential backoff. Retry delay grows from the configured
base and is capped at the configured maximum. A message is never retried beyond
`max_attempts`.

When the retry budget is exhausted:

- the outbox message becomes `dead`;
- the dispatch becomes `rejected`;
- the reservation becomes `cancelled`;
- `dispatch.delivery_failed` is appended to the audit chain;
- settlement cannot proceed.

This is intentionally fail-closed. v0.3 does not silently convert a delivery
failure into a successful dispatch state.

## Lease and crash recovery

A claimed message records a unique worker claim token and lease expiry. Another
worker can reclaim a `processing` message only after its lease expires. PostgreSQL
workers use row-level claim semantics with `SKIP LOCKED`; SQLite remains a safe
single-process development/test path rather than a production concurrency claim.

## Operational visibility

`GET /v1/operations/outbox` is restricted to `auditor` and `market_operator` and
returns only low-cardinality operational values:

- pending;
- processing;
- published;
- dead;
- currently due;
- oldest pending age in seconds.

The endpoint does not return payloads, asset identifiers, participant data,
idempotency keys or error text.

## Worker boundary

`python -m energy_flex_trust.worker --limit 10` processes one bounded batch with
the credential-free no-op publisher. It is a local/reference runner, not a daemon
or production market connector. A real deployment should provide explicit process
supervision, workload identity, bounded resource configuration, alerting and an
adapter subject to separate security and interoperability review.

## OpenADR 3 boundary

`OpenAdr3ContractPublisher` deliberately separates three responsibilities:

1. domain-to-event mapping;
2. schema validation;
3. transport.

The repository does not copy or approximate normative OpenADR schema assets. An
operator must supply a reviewed, version-pinned mapper/validator based on the
normative materials applicable to that integration. Schema validation must succeed
before transport is called. The outbox idempotency key is preserved across this
boundary.

The included recording transport and synthetic mapper used in tests are contract
fixtures only. They do not establish OpenADR conformance, certification, market
acceptance or safe physical-device control.

## Evidence and limitations

v0.3 tests exercise queued-to-published state transitions, settlement blocking,
transient retry, bounded terminal failure, expired-lease recovery, low-cardinality
health reporting and schema-before-transport behavior. These tests support the
reference architecture but do not replace production load, failover, penetration,
market interoperability or certification testing.
