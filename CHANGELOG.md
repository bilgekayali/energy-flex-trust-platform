# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- FastAPI coordination workflow for assets, offers, reservations, dispatches,
  meter evidence, settlements, and audit verification.
- PostgreSQL-compatible SQLAlchemy persistence with a safe SQLite default.
- Idempotency controls for financially material commands.
- Role policy, ownership checks, and settlement separation of duties.
- Hash-linked audit events and content-hashed settlement evidence manifests.
- Safe no-op dispatch adapter and a protocol boundary for future OpenADR 3 work.
- Docker Compose environment, CI, architecture records, and threat model.

