"""Keep the Linux release profile on the reviewed trust and image pins."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "package" / "constraints-linux-nvidia-cu129.txt"


def _locked_block(package: str) -> str:
    lines = LOCK.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(f"{package}==")]
    assert len(starts) == 1, f"expected one {package} lock entry"
    start = starts[0]
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if re.match(r"^[A-Za-z0-9_.-]+==", lines[i])
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_security_package_versions_are_hash_pinned() -> None:
    certifi = _locked_block("certifi")
    pillow = _locked_block("pillow")

    assert certifi.startswith("certifi==2026.10.23 ")
    assert pillow.startswith("pillow==13.0.0 ")
    assert re.search(r"(?m)^\s+--hash=sha256:[0-9a-f]{64}", certifi)
    assert re.search(r"(?m)^\s+--hash=sha256:[0-9a-f]{64}", pillow)


def test_services_runtime_direct_pin_matches_release_lock() -> None:
    setup = (ROOT / "services" / "setup.py").read_text(encoding="utf-8")
    assert '"pillow==13.0.0"' in setup
    assert '"certifi>=2026.10.23"' in setup
