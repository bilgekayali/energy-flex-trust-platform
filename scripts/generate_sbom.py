"""Generate an SPDX 2.3 JSON SBOM for the active Python environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

PROJECT_NAME = "energy-flex-trust-platform"
SPDX_VERSION = "SPDX-2.3"


def _spdx_id(name: str, version: str) -> str:
    value = re.sub(r"[^A-Za-z0-9.-]+", "-", f"{name}-{version}").strip("-")
    return f"SPDXRef-Package-{value}"


def _created_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        value = datetime.fromtimestamp(int(epoch), tz=UTC)
    else:
        value = datetime.now(UTC)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_document() -> dict[str, object]:
    distributions: list[tuple[str, str, str]] = []
    for distribution in metadata.distributions():
        name = (distribution.metadata.get("Name") or "").strip()
        version = distribution.version.strip()
        if not name or not version:
            continue
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        distributions.append((normalized, name, version))
    distributions.sort()

    digest_input = "\n".join(
        f"{normalized}=={version}" for normalized, _name, version in distributions
    ).encode("utf-8")
    environment_digest = hashlib.sha256(digest_input).hexdigest()

    packages: list[dict[str, object]] = []
    project_spdx_id = ""
    for normalized, name, version in distributions:
        spdx_id = _spdx_id(normalized, version)
        if normalized == PROJECT_NAME:
            project_spdx_id = spdx_id
        packages.append(
            {
                "SPDXID": spdx_id,
                "name": name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "supplier": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{normalized}@{version}",
                    }
                ],
            }
        )

    if not project_spdx_id:
        raise RuntimeError(
            "The active environment does not contain energy-flex-trust-platform."
        )

    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": project_spdx_id,
        }
    ]
    relationships.extend(
        {
            "spdxElementId": project_spdx_id,
            "relationshipType": "DEPENDS_ON",
            "relatedSpdxElement": package["SPDXID"],
        }
        for package in packages
        if package["SPDXID"] != project_spdx_id
    )

    project_version = next(
        version
        for normalized, _name, version in distributions
        if normalized == PROJECT_NAME
    )
    return {
        "spdxVersion": SPDX_VERSION,
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{PROJECT_NAME}-{project_version}-runtime",
        "documentNamespace": (
            "https://spdx.org/spdxdocs/"
            f"{PROJECT_NAME}-{project_version}-{environment_digest}"
        ),
        "creationInfo": {
            "created": _created_at(),
            "creators": ["Tool: energy-flex-trust scripts/generate_sbom.py"],
        },
        "packages": packages,
        "relationships": relationships,
    }


def validate_document(document: dict[str, object]) -> None:
    if document.get("spdxVersion") != SPDX_VERSION:
        raise ValueError("Unexpected SPDX version.")
    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("SBOM contains no packages.")
    if not any(
        isinstance(package, dict)
        and str(package.get("name", "")).lower() == PROJECT_NAME
        for package in packages
    ):
        raise ValueError("SBOM does not describe the Energy Flex Trust package.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = build_document()
    validate_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
