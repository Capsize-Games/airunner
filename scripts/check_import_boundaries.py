"""Enforce the intended package dependency order (issue #2193).

The repo-split tracker (#2185) targets six eventual repositories with
a strictly downward dependency graph. Nothing enforced that order
before this script existed, which is exactly how the violations fixed
by #2186 (services importing the desktop app), #2189 (production
importing the benchmark harness) and #2190 (a vendored library
importing the application's database models) reached ``main``
unnoticed. No repository in #2185's Phase 1 onward may be created
before this check is green and wired into CI.

Allowed edges (an importer may depend on anything to its right; an
edge not listed here is a violation -- see import_boundary_rules.py's
``OWNED_ROOTS`` for the literal data this docstring describes)::

    airunner            -> airunner_services, airunner_native
    airunner_services   -> (nothing in this project)
    airunner_native     -> airunner, airunner_services

``airunner_common`` no longer appears here: it was extracted to its
own repository (issue #2197,
https://github.com/Capsize-Games/airunner-common) and is now an
ordinary installed dependency, not a project-internal package this
checker tracks -- there's no cycle risk left once it doesn't live in
this repo's tree. ``services/src/airunner_services/eval`` was
extracted to its own repository (issue #2194,
https://github.com/Capsize-Games/airunner-eval) and no longer exists
here, so the rule that used to govern it ("nothing outside eval may
import eval") was removed rather than left as dead code that could
never fire. ``services/src/airunner_services/vendor`` was likewise
extracted to its own package (issue #2195,
https://github.com/Capsize-Games/airunner-tts-vendor), removing the
vendor-isolation rule the same way.

``airunner_native -> airunner, airunner_services`` was not the
original design (#2185's tracker described native as a leaf that only
depends on ``airunner_common``, extractable early in Phase 1). Writing
this checker found that ``native/src/airunner_native/launcher.py`` --
705 lines, the actual process entry point -- imports ``airunner`` at
15 sites (including ``airunner.main`` itself) and ``airunner_services``
at 2, because its job is to bootstrap and launch the GUI application.
That is structural, not incidental: a launcher inherently imports what
it launches. The tracker's topology diagram and #2196 (X11)'s
"extracted early, nothing depends on it" framing were wrong on this
point; #2196 needs to account for a real dependency on the
not-yet-extracted ``airunner`` package before that extraction can
happen (see the comment left on #2185 and #2196 recording this).

A module- or function-level import both count: a lazy ``import`` deep
inside a function body is the same dependency edge as one at the top
of the file (see the four ``get_qsettings`` sites #2186 found and
fixed, all originally lazy).

Run directly (``python scripts/check_import_boundaries.py``) it exits
non-zero and prints each violation. It is also wired into the CI test
suite via ``services/tests/test_import_boundaries.py``, the same
pattern ``scripts/check_third_party_notices.py`` already uses
(issue #2059).

Known exceptions to the rules above live in
``scripts/import_boundary_allowlist.py``, each individually justified
and named to the issue that removes it -- never a wildcard, never a
count threshold.

Known gap, left out deliberately rather than papered over: a rule
that non-GUI desktop code (``src/airunner/**`` outside a ``gui/``
subdirectory) must not import GUI code was speculative per #2193's
own scope note -- "if the current tree already violates it, report
the violations and leave the rule out rather than granting a blanket
exemption." Measuring it found real violations (``app.py``,
``launcher.py``, ``app_mixins/ui_runtime_mixin.py`` and others import
GUI code from outside ``gui/``, some plausibly legitimate entry-point
wiring and some not yet triaged). That rule is not implemented here;
resolving the desktop's own GUI/non-GUI boundary is a separate,
unscoped piece of work.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the sibling modules importable both when this file is run
# directly (`python scripts/check_import_boundaries.py`, where only
# this file's own directory is on sys.path) and when it is imported
# as `scripts.check_import_boundaries` from the repo root (where
# `scripts/` itself is not separately on sys.path).
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from import_boundary_allowlist import ALLOWLIST  # noqa: E402
from import_boundary_rules import (  # noqa: E402
    OWNED_ROOTS,
    Violation,
    check_owned_root,
    check_pyside6_not_at_module_scope,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _is_allowlisted(violation: Violation) -> bool:
    key = (violation.path.as_posix(), violation.line, violation.imported)
    return key in ALLOWLIST


def run_check(*, repo_root: Path | None = None) -> list[str]:
    """Return every violation as a formatted string; empty means clean."""
    root = (repo_root or _REPO_ROOT).resolve()

    violations: list[Violation] = []
    for root_rel, (owner_name, allowed) in OWNED_ROOTS.items():
        violations.extend(
            check_owned_root(root, root_rel, owner_name, allowed)
        )
    violations.extend(check_pyside6_not_at_module_scope(root))

    return [str(v) for v in violations if not _is_allowlisted(v)]


if __name__ == "__main__":
    problems = run_check()
    if problems:
        print(f"Found {len(problems)} import-boundary violation(s):\n")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    print("No import-boundary violations found.")
