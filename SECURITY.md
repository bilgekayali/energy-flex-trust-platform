# Security policy

## Supported version

Only the latest commit on `main` is supported during the v0.x reference phase.

## Reporting a vulnerability

Please do not publish exploit details in a public issue. Use GitHub's private
vulnerability reporting feature for this repository. Include the affected version,
reproduction steps, expected impact, and any suggested mitigation.

## Scope boundary

This project is a reference implementation for synthetic workflows. Its default
dispatch publisher is a no-op and must not be connected to a live energy asset.
Before real deployment, add authenticated identities, managed secrets, migrations,
signed evidence, rate limits, monitoring, backup recovery, and an independent
security review.

