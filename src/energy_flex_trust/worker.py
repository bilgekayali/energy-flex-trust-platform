"""Credential-free outbox worker entry point for local/reference operation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .config import Settings
from .database import build_engine, build_session_factory, initialize_database
from .outbox import OutboxRunResult, OutboxWorker
from .ports import NoopDispatchPublisher


def run_once(
    settings: Settings | None = None,
    *,
    limit: int = 10,
) -> OutboxRunResult:
    """Process one bounded batch with the safe no-op publisher."""

    settings = settings or Settings.from_environment()
    settings.validate_runtime()
    engine = build_engine(settings.database_url)
    initialize_database(
        engine,
        managed=settings.environment not in {"development", "test"},
    )
    factory = build_session_factory(engine)
    try:
        return OutboxWorker(
            factory,
            NoopDispatchPublisher(),
        ).run_once(limit=limit)
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process one bounded Energy Flex Trust outbox batch."
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    result = run_once(limit=args.limit)
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == "__main__":
    main()
