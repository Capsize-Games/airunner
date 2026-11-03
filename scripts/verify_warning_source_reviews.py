"""Bind optional freeze-warning dispositions to installed source bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sysconfig


def verify_warning_source_reviews(
    evidence: Path,
    *,
    site_packages: Path | None = None,
    stdlib: Path | None = None,
) -> list[str]:
    """Reject missing or changed reviewed callers before a full freeze."""
    site_packages = site_packages or Path(sysconfig.get_path("purelib"))
    stdlib = stdlib or Path(sysconfig.get_path("stdlib"))
    try:
        with evidence.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return ["warning source evidence exceeds its size limit"]
        data = json.loads(raw)
        if data.get("schema_version") != 1:
            return ["unsupported warning source evidence schema"]
        rows = data["dispositions"]
        if not isinstance(rows, list):
            return ["warning source dispositions must be an array"]
        expected: dict[str, str] = {}
        for row in rows:
            for importer in row["importers"]:
                source, digest = importer["source"], importer["source_sha256"]
                path = PurePosixPath(source)
                if (
                    path.is_absolute() or not path.parts or ".." in path.parts
                    or "\\" in source or path.as_posix() != source
                    or not re.fullmatch(r"[0-9a-f]{64}", digest)
                ):
                    return ["unsafe source identity in warning evidence"]
                if source in expected and expected[source] != digest:
                    return ["conflicting source hashes in warning evidence"]
                expected[source] = digest
        if not expected:
            return ["warning evidence contains no reviewed source files"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return ["warning source evidence is missing or malformed"]

    problems = []
    for source, digest in sorted(expected.items()):
        base = stdlib if source.startswith("stdlib/") else site_packages
        path = base / source.removeprefix("stdlib/")
        try:
            if not path.resolve(strict=True).is_relative_to(base.resolve()):
                raise ValueError("source escapes its installation root")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != digest:
                problems.append(f"reviewed warning source changed: {source}")
        except (OSError, ValueError):
            problems.append(f"reviewed warning source unavailable: {source}")
    return problems
