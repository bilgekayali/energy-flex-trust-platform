# API workflow

## Actors and authentication

Development/test can receive `X-Actor-ID` and `X-Actor-Role` only as policy
fixtures. Supported roles are:

- `asset_owner`
- `market_operator`
- `settlement_analyst`
- `auditor`
- `system`

These headers are not authentication and non-development startup rejects that mode.
A managed runtime uses the offline pinned-JWKS OIDC boundary described in
[Trust boundaries](TRUST_BOUNDARIES.md).

## Command sequence

1. An asset owner registers a reference asset.
2. The same owner creates an offer within registered capacity.
3. A market operator reserves some or all of the offer with an idempotency key.
4. A market operator queues one dispatch inside the offer window with another key.
5. The dispatch API transaction commits the dispatch as `queued`, reservation as
   `dispatch_pending`, an audit event and a transactional outbox message. It makes
   no external network call.
6. A separate worker leases the outbox message and invokes a publisher using the
   same durable idempotency key.
7. Successful publication moves the dispatch to `issued`, the reservation to
   `dispatched`, the outbox message to `published`, and appends
   `dispatch.published`.
8. The owner or system records one or more interval readings.
9. A separate settlement analyst calculates settlement idempotently. Settlement is
   rejected unless the dispatch has been acknowledged as issued.
10. An auditor verifies both the evidence hash and complete audit chain.

## Command idempotency contract

The API key namespace is scoped by operation. Within an operation:

- same key + same canonical request → same resource;
- same key + different canonical request → `409 Conflict`;
- blank key → `409 Conflict`;
- a database uniqueness constraint protects the operation/key pair.

Clients should generate a stable business-command key and retain it across network
retries.

## Outbound idempotency contract

The dispatch command key also becomes the durable outbox idempotency key. The
worker passes it to `DispatchPublisher` on every attempt.

Delivery is at least once. A production destination must deduplicate equivalent
replays because a worker can publish successfully and crash before local
finalization. The reference no-op publisher is deterministic but does not prove a
real destination's deduplication behavior.

## Retry and recovery

Transient publisher exceptions return the outbox message to `pending` with bounded
exponential backoff. A claimed message is recoverable after lease expiry. When the
configured attempt budget is exhausted:

- outbox → `dead`;
- dispatch → `rejected`;
- reservation → `cancelled`;
- audit → `dispatch.delivery_failed`;
- settlement remains blocked.

There is no unaudited automatic re-drive of dead messages in v0.3.

## Operations visibility

`GET /v1/operations/outbox` is available to `auditor` and `market_operator` and
returns only aggregate counts plus oldest pending age. It does not expose payloads,
asset IDs, participant IDs, idempotency keys, adapter references or error text.

## Failure behavior

| Condition | Result |
|---|---|
| Missing identity | `401 Unauthorized` |
| Missing resource | `404 Not Found` |
| Role or ownership violation | `403 Forbidden` |
| Capacity, replay, state, window, evidence or delivery-state conflict | `409 Conflict` |
| Invalid request shape or timezone | `422 Unprocessable Entity` |
| Publisher transient failure | Bounded retry; API command remains durably queued |
| Publisher retry budget exhausted | Audited dead/rejected/cancelled state; no settlement |

No reference error path calls a physical asset. `python -m energy_flex_trust.worker`
uses the safe no-op publisher unless a separately reviewed integration is wired by
an operator outside the bundled default path.
