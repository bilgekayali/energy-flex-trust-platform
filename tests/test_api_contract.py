"""Public HTTP surface compatibility gate."""

from __future__ import annotations

import json
from pathlib import Path

from energy_flex_trust.api import create_app
from energy_flex_trust.config import Settings

CONTRACT_PATH = Path("contracts/api-surface-v0.9.json")


def test_public_api_surface_matches_release_contract() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = {
        (entry["method"], entry["path"])
        for entry in contract["routes"]
    }

    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            environment="test",
        )
    )
    observed: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path != "/health" and not path.startswith("/v1/"):
            continue
        for method in getattr(route, "methods", set()):
            if method not in {"HEAD", "OPTIONS"}:
                observed.add((method, path))

    assert observed == expected
    assert app.openapi()["info"]["version"] == contract["release"]
    assert not any(path.startswith("/v1/recovery") for _method, path in observed)
