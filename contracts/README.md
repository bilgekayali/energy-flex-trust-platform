# Versioned contract artifacts

This directory contains reviewable compatibility fixtures for public or persisted
interfaces that must not change silently.

- `api-surface-v0.9.json` preserves the pre-v1 release-candidate HTTP route fixture.
- `api-surface-v1.json` is the stable v1 public HTTP route contract used by CI.

The route fixture is intentionally not treated as a complete semantic OpenAPI diff.
Release review must also consider generated OpenAPI schemas, behavior tests,
idempotency semantics, persisted evidence and the compatibility policy in
`docs/COMPATIBILITY.md`.
