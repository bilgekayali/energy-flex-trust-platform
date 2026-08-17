# Terminal dispatch re-drive runbook

A `dead` outbox message is a terminal operational exception, not an invitation to
retry blindly. Re-drive can cause a financially or physically material action and
therefore requires destination reconciliation first.

## Preconditions

Before authorizing a re-drive, confirm all of the following:

1. The outbox message is `dead`.
2. The linked dispatch is `rejected` and reservation is `cancelled` because of the
   terminal delivery failure path.
3. The destination incident has been investigated.
4. The original destination supports a reliable deduplication control using the
   original idempotency key, or the operator has otherwise proved that replay is
   safe.
5. The change/incident record contains the message ID, dispatch ID, failure summary,
   destination evidence, accountable approver and recovery operator.
6. The operator uses the dedicated recovery database identity, not API, worker or
   migrator credentials.

## Authorization

The recovery command changes only database state. It does not publish a dispatch.

```bash
export DATABASE_URL='postgresql+psycopg://<recovery-role>@<db>/<database>'
python -m energy_flex_trust.recovery_cli \
  --message-id '<outbox-id>' \
  --dispatch-id '<dispatch-id>' \
  --actor-id '<authenticated-operator-id>' \
  --reason '<incident/change reference and decision>' \
  --acknowledge-replay-risk
```

The state transition is:

```text
outbox:       dead       -> pending
 dispatch:   rejected   -> queued
 reservation: cancelled -> dispatch_pending
```

The original outbox row and **original idempotency key are retained**. Attempts are
reset for the new delivery cycle, previous error text is cleared, and an audit event
`dispatch.redrive_authorized` records the reason, prior attempt count and SHA-256 of
the prior error text.

## Delivery after authorization

1. Confirm the new `dispatch.redrive_authorized` event is present and the audit
   chain verifies.
2. Re-enable or invoke the institution-owned production publisher through the
   normal worker path.
3. Confirm the destination's deduplication/idempotency record.
4. Confirm local outbox state becomes `published`, dispatch becomes `issued` and
   reservation becomes `dispatched`.
5. If delivery fails again, stop at the normal terminal failure threshold and open
   a new reconciliation cycle. Do not script an infinite re-drive loop.

## Prohibited shortcuts

- Do not modify the idempotency key to force the destination to accept a replay.
- Do not update outbox status directly with ad-hoc SQL.
- Do not bypass `dead/rejected/cancelled` state checks.
- Do not use the recovery identity for routine worker polling.
- Do not infer external delivery merely from local database state.

## Irreversibility warning

Once a production publisher attempts the re-driven dispatch, any external physical
or market action may be irreversible through this database. Cancellation and safety
procedures must use the destination/operator's authoritative control path.
