"""Dead code scanner for the airunner services codebase.

Scans the services codebase with vulture. Services code uses SignalCode
enum dispatch and FastAPI patterns that vulture cannot trace statically.
A small whitelist handles the remaining edge cases.
"""

import os
import re
from vulture import Vulture
from vulture.core import Item as VultureItem

SERVICES_SRC = "server/src/airunner_services"
WHITELIST_PATH = "services_vulture_whitelist.py"

_LINES_CACHE: dict[str, list[str]] = {}


def _lines(p: str) -> list[str]:
    if p not in _LINES_CACHE:
        try:
            with open(p, encoding="utf-8") as f:
                _LINES_CACHE[p] = f.readlines()
        except Exception:
            _LINES_CACHE[p] = []
    return _LINES_CACHE[p]


def _in_enum(ls: list[str], lineno: int) -> bool:
    """Check if line is inside a class inheriting from Enum."""
    for i in range(lineno - 2, max(lineno - 300, -1), -1):
        if i < 0:
            break
        s = ls[i].strip()
        if re.match(r"^class \w+.*\((str,\s*)?[Ee]num", s):
            return True
        if s.startswith("class ") or s.startswith("def "):
            break
    return False


def _load_whitelist() -> dict[str, set[str]]:
    """Load filepath:{name1, name2} whitelist."""
    out: dict[str, set[str]] = {}
    if not os.path.exists(WHITELIST_PATH):
        return out
    with open(WHITELIST_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith('"""'):
                continue
            if ':' not in line:
                continue
            fp, namespart = line.split(':', 1)
            fp = fp.strip()
            namespart = namespart.strip()
            if namespart.startswith('{') and namespart.endswith('}'):
                out[fp] = {
                    n.strip()
                    for n in namespart[1:-1].split(',')
                    if n.strip()
                }
    return out


def _auto_skip(item: VultureItem, filepath: str) -> bool:
    """Return True to auto-skip this item as a false positive."""
    name = item.name
    typ = getattr(item, "typ", "")
    ls = _lines(filepath)
    fn = os.path.basename(filepath)

    # ALL_CAPS constants in settings.py
    if "settings.py" in filepath and name.isupper() and "_" in name:
        return True

    # ALL_CAPS in enum files
    if (fn in ("contract_enums.py", "enums.py") and
            name.isupper() and "_" in name):
        return True

    # __getattr__ lazy loader in __init__.py
    if fn == "__init__.py" and name in ("__getattr__", "__dir__"):
        return True

    # Pytest hooks
    if fn in ("conftest.py",) or filepath.endswith("_test.py"):
        if name.startswith("pytest_") or name in (
            "anyio_backend", "pytestmark",
        ):
            return True

    # Values inside Enum classes
    if typ in ("variable", "attribute") and _in_enum(
        ls, item.first_lineno
    ):
        return True

    return False


def scan_for_dead_code(target_directory: str) -> None:
    if not os.path.exists(target_directory):
        print(f"Error: '{target_directory}' does not exist.")
        return

    srcs: list[str] = []
    for root, _, files in os.walk(target_directory):
        for fn in files:
            if fn.endswith(".py") and not fn.endswith("_rc.py"):
                srcs.append(os.path.join(root, fn))

    if not srcs:
        print("No Python files found.")
        return

    v = Vulture(verbose=False)
    v.scavenge(srcs)
    items = v.get_unused_code()
    if not items:
        print("No obsolete code detected.")
        return

    wl = _load_whitelist()
    by_file: dict[str, list[VultureItem]] = {}

    for item in items:
        fp = os.path.realpath(item.filename)
        if _auto_skip(item, fp):
            continue
        rel = os.path.relpath(fp)
        if rel in wl and item.name in wl[rel]:
            continue
        # Exclude alembic migrations from output (framework-managed code)
        if "/alembic/versions/" in rel:
            continue
        # Exclude vendor third-party code
        if "/vendor/" in rel:
            continue
        # Exclude test files
        if "/tests/" in rel:
            continue
        by_file.setdefault(fp, []).append(item)

    if not by_file:
        print("No obsolete code detected.")
        return

    print("=== OBSOLETE CODE REPORT ===")
    print(f"Scanned {len(srcs)} source files\n")
    for fp in sorted(by_file):
        print(f"File: {fp}")
        for item in sorted(by_file[fp], key=lambda x: x.first_lineno):
            print(
                f"  - Line {item.first_lineno:3d}: Unused {item.typ}"
                f" '{item.name}' ({item.confidence}% confidence)"
            )
        print("-" * 60)


if __name__ == "__main__":
    scan_for_dead_code(SERVICES_SRC)
