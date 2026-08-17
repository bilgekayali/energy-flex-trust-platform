"""Validate bounded security-advisory exceptions against source usage."""

from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime
from pathlib import Path

EXCEPTIONS_PATH = Path("security/advisory-exceptions.json")
SOURCE_ROOT = Path("src")


def _source_symbols() -> set[str]:
    symbols: set[str] = set()
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                symbols.add(node.id)
            elif isinstance(node, ast.Attribute):
                symbols.add(node.attr)
            elif isinstance(node, ast.alias):
                symbols.add(node.asname or node.name.rsplit(".", 1)[-1])
    return symbols


def _today() -> date:
    return datetime.now(UTC).date()


def validate() -> None:
    document = json.loads(EXCEPTIONS_PATH.read_text(encoding="utf-8"))
    exceptions = document.get("exceptions")
    if not isinstance(exceptions, list):
        raise RuntimeError("Security exception document must contain an exceptions list.")

    symbols = _source_symbols()
    seen_ids: set[str] = set()
    failures: list[str] = []
    for item in exceptions:
        if not isinstance(item, dict):
            failures.append("exception entry is not an object")
            continue
        advisory_id = str(item.get("id", "")).strip()
        if not advisory_id or advisory_id in seen_ids:
            failures.append(f"invalid or duplicate advisory id: {advisory_id!r}")
            continue
        seen_ids.add(advisory_id)

        expires_on = date.fromisoformat(str(item.get("expires_on", "")))
        if _today() > expires_on:
            failures.append(
                f"{advisory_id} exception expired on {expires_on.isoformat()}"
            )

        affected_api = item.get("affected_api")
        if not isinstance(affected_api, list) or not affected_api:
            failures.append(f"{advisory_id} has no affected_api scope")
            continue
        forbidden = sorted({str(name) for name in affected_api} & symbols)
        if forbidden:
            failures.append(
                f"{advisory_id} affected APIs are now used by source: {forbidden}"
            )

        if not str(item.get("upstream_fix", "")).strip():
            failures.append(f"{advisory_id} has no upstream_fix")
        if len(str(item.get("reason", "")).strip()) < 40:
            failures.append(f"{advisory_id} exception reason is insufficient")

    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    validate()
