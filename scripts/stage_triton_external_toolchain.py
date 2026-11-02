"""Repository CLI wrapper for the installed Triton toolchain installer."""

from __future__ import annotations

import sys
from pathlib import Path

SERVICE_SOURCE = Path(__file__).resolve().parents[1] / "services" / "src"
if str(SERVICE_SOURCE) not in sys.path:
    sys.path.insert(0, str(SERVICE_SOURCE))

from airunner_services.art import triton_toolchain_installer as _installer  # noqa: E402


def __getattr__(name: str):
    """Keep the focused repository tests pointed at the shared implementation."""
    return getattr(_installer, name)


def main(argv: list[str] | None = None) -> int:
    return _installer.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
