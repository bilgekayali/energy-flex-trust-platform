# API workflow

## Actors

The development API receives `X-Actor-ID` and `X-Actor-Role`. Supported roles are:

- `asset_owner`
- `market_operator`
- `settlement_analyst`
- `auditor`
- `system`

These values exercise policy logic but are not trusted authentication. Never expose
this mechanism to a public production network.

## Command sequence

1. An asset owner registers a synthetic asset.
2. The same owner creates an offer within the registered capacity.
3. A market operator reserves some or all of the offer with an idempotency key.
4. A market operator issues one dispatch inside the offer window with another key.
5. The owner or system records one or more interval readings.
6. A separate settlement analyst calculates settlement idempotently.
7. An auditor verifies both the evidence hash and complete audit chain.

## Idempotency contract

The key namespace is scoped by operation. Within an operation:

- same key + same canonical request → same resource;
- same key + different canonical request → `409 Conflict`;
- blank key → `409 Conflict`;
- a database uniqueness constraint protects the operation/key pair.

Clients should generate a stable UUID per business command and retain it across
network retries.

## Failure behavior

| Condition | Result |
|---|---|
| Missing resource | `404 Not Found` |
| Role or ownership violation | `403 Forbidden` |
| Capacity, replay, state, window, or evidence conflict | `409 Conflict` |
| Invalid request shape or timezone | `422 Unprocessable Entity` |

No error path calls a physical asset. The v0.1 adapter returns `noop:<dispatch-id>`.

