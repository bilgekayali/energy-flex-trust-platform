"""Outbox worker entry point with an explicit production publisher boundary."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .config import Settings
from .database import build_engine, build_session_factory, initialize_database
from .outbox import OutboxRunResult, OutboxWorker
from .ports import DispatchPublisher, NoopDispatchPublisher

SAFE_NOOP_ENVIRONMENTS = frozenset({"development", "test"})


def _resolve_publisher(
    settings: Settings,
    publisher: DispatchPublisher | None,
) -> DispatchPublisher:
    if publisher is not None:
        return publisher
    if settings.environment not in SAFE_NOOP_ENVIRONMENTS:
        raise RuntimeError(
            "The credential-free NoopDispatchPublisher is disabled outside "
            "development/test. A production worker must inject an "
            "institution-owned, authenticated DispatchPublisher."
        )
    return NoopDispatchPublisher()


def run_once(
    settings: Settings | None = None,
    *,
    limit: int = 10,
    publisher: DispatchPublisher | None = None,
) -> OutboxRunResult:
    """Process one bounded outbox batch.

    The CLI/default publisher is deliberately unavailable in production-like
    environments. Production orchestration must construct this function with an
    institution-owned publisher whose destination authentication, egress policy,
    schema validation and downstream idempotency controls have been reviewed.
    """

    settings = settings or Settings.from_environment()
    settings.validate_runtime()
    selected_publisher = _resolve_publisher(settings, publisher)
    engine = build_engine(settings.database_url)
    initialize_database(
        engine,
        managed=settings.environment not in SAFE_NOOP_ENVIRONMENTS,
    )
    factory = build_session_factory(engine)
    try:
        return OutboxWorker(
            factory,
            selected_publisher,
        ).run_once(limit=limit)
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Process one bounded Energy Flex Trust outbox batch. The built-in "
            "publisher is development/test only."
        )
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    result = run_once(limit=args.limit)
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == "__main__":
    main()
