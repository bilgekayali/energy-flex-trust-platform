# ADR 0001: Hash-linked audit events

- Status: Accepted
- Date: 2026-08-04

## Context

Operational and settlement disputes require evidence of the sequence of decisions,
not only the final database state. Ordinary mutable logs do not expose silent edits.

## Decision

Store every material state transition in the same transaction as its aggregate
change. Canonicalize the event and link it to the previous event using SHA-256.
Provide a full-chain verification endpoint restricted to the auditor role.

## Consequences

Mutation, deletion, and reordering become detectable. The chain remains dependent on
the integrity of the verifier and primary database; signed off-system checkpoints are
required for stronger non-repudiation.

