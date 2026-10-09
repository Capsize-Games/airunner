"""Helpers for spawning import-isolation subprocesses.

Isolation tests assert that a package is genuinely *unimportable*, not
merely absent from ``PYTHONPATH``. The desktop ``airunner`` distribution
is editable-installed via a ``.pth`` file that runs
``__editable___airunner_6_0_0_finder.install()``, registering a
``_EditableFinder`` on ``sys.meta_path`` (not as a path entry). That
finder maps ``airunner`` straight to the checkout's ``src`` directory
from site-packages, so removing the ``src`` entry from ``sys.path`` is
not enough to make the package unimportable -- the finder has to be
dropped from ``sys.meta_path`` as well.

In a worktree reusing another checkout's venv (issue #2246), that
venv's editable install can additionally provide the blocked package
from the foreign checkout, which no path entry of the checkout under
test covers. ``blocked`` therefore also installs a meta-path blocker
that refuses the named top-level packages outright, wherever they
would resolve from.

``import_isolation_preamble`` returns the script text all three steps
need so the isolation tests share one implementation.
"""

from __future__ import annotations

_EDITABLE_FINDER_PREFIX = "__editable__"


def _blocker_snippet(blocked: tuple[str, ...]) -> str:
    """Return script text refusing the *blocked* top-level packages."""
    names = repr(blocked)
    prefixes = repr(tuple(f"{name}." for name in blocked))
    return (
        # Leading newline: the preamble's first chunk is one line of
        # semicolon-joined simple statements, which a ``class`` header
        # cannot follow on the same line.
        "\nclass _IsolationBlocker:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        f"        if name in {names} or name.startswith({prefixes}):\n"
        "            raise ImportError('blocked: ' + name)\n"
        "sys.meta_path.insert(0, _IsolationBlocker())\n"
    )


def _removal_snippet(paths: tuple[str, ...]) -> str:
    """Return script text dropping *paths* and editable finders."""
    joined = ", ".join(repr(path) for path in paths)
    finder = repr(_EDITABLE_FINDER_PREFIX)
    return (
        "import sys; "
        f"sys.path[:] = [p for p in sys.path if p not in ({joined})]; "
        "sys.meta_path[:] = [f for f in sys.meta_path "
        f"if not getattr(f, '__module__', '').startswith({finder})]; "
    )


def import_isolation_preamble(
    paths: tuple[str, ...],
    blocked: tuple[str, ...] = (),
) -> str:
    """Return script text blocking imports via *paths* and *blocked*.

    The returned snippet, when run first in a subprocess, removes every
    listed entry from ``sys.path``, every editable-install finder from
    ``sys.meta_path``, and refuses every *blocked* top-level package
    (plus its submodules) no matter which entry would provide it.
    """
    snippet = _removal_snippet(paths)
    if blocked:
        snippet += _blocker_snippet(blocked)
    return snippet
