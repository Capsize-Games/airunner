"""Dead code scanner for the airunner GUI codebase.

Scans the GUI codebase with vulture. Includes _ui.py template files for
import tracking. Auto-filters known Qt/PySide6 false positives.

Whitelist is kept in a minimal vulture-compatible format:
    vulture_whitelist.py   (one name per line)

Regenerate the whitelist after changes:
    venv/bin/python scripts/gui_dead_code_scanner.py | sed -n 's/.*Unused .* \x27\(.*\)\x27.*/\1/p' | sort -u > vulture_whitelist.py.new
"""

import os
import re
from vulture import Vulture
from vulture.core import Item as VultureItem

AIRUNNER_SRC = "src/airunner"
WHITELIST_PATH = "gui_vulture_whitelist.py"

# Qt methods called by C++ framework or connected via .ui connectSlotsByName
QT_AUTO = frozenset({
    "paintEvent", "mousePressEvent", "mouseMoveEvent", "mouseReleaseEvent",
    "keyPressEvent", "keyReleaseEvent", "wheelEvent", "resizeEvent",
    "showEvent", "hideEvent", "closeEvent", "focusInEvent", "focusOutEvent",
    "enterEvent", "leaveEvent", "dragEnterEvent", "dragLeaveEvent",
    "dragMoveEvent", "dropEvent", "contextMenuEvent", "changeEvent",
    "timerEvent", "event", "eventFilter", "supportedDragActions",
    "mimeTypes", "mimeData",
})

_LINES_CACHE: dict[str, list[str]] = {}


def _lines(p: str) -> list[str]:
    if p not in _LINES_CACHE:
        try:
            with open(p, encoding="utf-8") as f:
                _LINES_CACHE[p] = f.readlines()
        except Exception:
            _LINES_CACHE[p] = []
    return _LINES_CACHE[p]


def _has_slot(ls: list[str], lineno: int) -> bool:
    for i in range(lineno - 2, max(lineno - 8, -1), -1):
        if i < 0:
            break
        s = ls[i].strip()
        if s.startswith(("@Slot", "@pyqtSlot")):
            return True
        if s.startswith("def ") or (s.startswith("@") and "Slot" not in s):
            break
    return False


def _in_enum(ls: list[str], lineno: int) -> bool:
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
                out[fp] = {n.strip() for n in namespart[1:-1].split(',') if n.strip()}
    return out


def _auto_skip(item: VultureItem, filepath: str) -> bool:
    name = item.name
    typ = getattr(item, "typ", "")
    ls = _lines(filepath)
    fn = os.path.basename(filepath)

    if name in QT_AUTO:
        return True
    if fn == "conftest.py" or filepath.endswith("_test.py"):
        if name in ("pytest_configure", "pytest_ignore_collect",
                     "pytest_collection_modifyitems", "anyio_backend",
                     "pytestmark", "mock_scene_with_settings", "grid_size"):
            return True
    if fn == "__init__.py" and name in ("__getattr__", "__dir__"):
        return True
    if "settings.py" in filepath and name.isupper() and "_" in name:
        return True
    if typ == "method" and _has_slot(ls, item.first_lineno):
        return True
    if typ == "method" and re.match(
        r"^(on_|action_)[a-zA-Z]+_[a-zA-Z_]+$", name,
    ):
        return True
    if typ in ("variable", "attribute") and _in_enum(ls, item.first_lineno):
        return True
    return False


def scan_for_dead_code(target_directory: str) -> None:
    if not os.path.exists(target_directory):
        print(f"Error: '{target_directory}' does not exist.")
        return

    srcs: list[str] = []
    uis: list[str] = []
    for root, _, files in os.walk(target_directory):
        for fn in files:
            if not fn.endswith(".py") or fn.endswith("_rc.py"):
                continue
            f = os.path.join(root, fn)
            if fn.endswith("_ui.py"):
                uis.append(f)
            else:
                srcs.append(f)

    all_f = srcs + uis
    if not all_f:
        print("No Python files found.")
        return

    v = Vulture(verbose=False)
    v.scavenge(all_f)
    items = v.get_unused_code()
    if not items:
        print("No obsolete code detected.")
        return

    ui_set = {os.path.realpath(p) for p in uis}
    wl = _load_whitelist()
    by_file: dict[str, list[VultureItem]] = {}

    for item in items:
        fp = os.path.realpath(item.filename)
        if fp in ui_set:
            continue
        if _auto_skip(item, fp):
            continue
        rel = os.path.relpath(fp)
        if rel in wl and item.name in wl[rel]:
            continue
        by_file.setdefault(fp, []).append(item)

    if not by_file:
        print("No obsolete code detected.")
        return

    print("=== OBSOLETE CODE REPORT ===")
    print(f"Scanned {len(srcs)} source files (+{len(uis)} _ui.py)\n")
    for fp in sorted(by_file):
        print(f"File: {fp}")
        for item in sorted(by_file[fp], key=lambda x: x.first_lineno):
            print(f"  - Line {item.first_lineno:3d}: Unused {item.typ}"
                  f" '{item.name}' ({item.confidence}% confidence)")
        print("-" * 60)


if __name__ == "__main__":
    scan_for_dead_code(AIRUNNER_SRC)
