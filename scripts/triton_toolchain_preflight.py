"""Repository CLI shim for the packaged services Triton preflight."""

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    services_src = Path(__file__).resolve().parents[1] / "services" / "src"
    sys.path.insert(0, str(services_src))
    from airunner_services.art.triton_runtime import ensure_available

    available, message = ensure_available()
    print(
        f"Triton external toolchain preflight: {message}",
        file=sys.stdout if available else sys.stderr,
    )
    return 0 if available else 1


if __name__ == "__main__":
    raise SystemExit(main())
