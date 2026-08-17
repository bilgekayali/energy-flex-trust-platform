"""Guarded CLI for authorizing one terminal dispatch re-drive."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

from .database import build_engine, build_session_factory, initialize_database
from .domain import Actor, ActorRole
from .redrive import authorize_dead_dispatch_redrive


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value.startswith("postgresql+"):
        raise RuntimeError(
            "Recovery CLI requires an explicit PostgreSQL DATABASE_URL using the "
            "dedicated recovery database identity."
        )
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message-id", required=True)
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--acknowledge-replay-risk",
        action="store_true",
        help=(
            "Confirm that destination status and downstream idempotency were "
            "reviewed before re-arming this dispatch."
        ),
    )
    args = parser.parse_args()
    if not args.acknowledge_replay_risk:
        parser.error("--acknowledge-replay-risk is required")

    engine = build_engine(_database_url())
    initialize_database(engine, managed=True)
    factory = build_session_factory(engine)
    try:
        with factory() as session:
            result = authorize_dead_dispatch_redrive(
                session,
                actor=Actor(args.actor_id, ActorRole.RECOVERY_OPERATOR),
                message_id=args.message_id,
                dispatch_id=args.dispatch_id,
                reason=args.reason,
            )
        print(json.dumps(asdict(result), sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
