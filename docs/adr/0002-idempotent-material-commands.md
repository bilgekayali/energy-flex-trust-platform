# ADR 0002: Idempotent financially material commands

- Status: Accepted
- Date: 2026-08-04

## Context

Clients retry requests after timeouts. Repeating a reservation, dispatch, or
settlement can create physical or financial harm even if every individual request is
otherwise valid.

## Decision

Require an `Idempotency-Key` for reservation, dispatch, and settlement. Bind the
operation/key pair to a canonical request hash and resulting resource in the same
transaction. Return the existing resource for an exact replay and reject a changed
payload.

## Consequences

Safe retries become possible and accidental key reuse is visible. Callers must retain
keys, and a production service must define retention, tenant scoping, and concurrent
insert recovery policies.

