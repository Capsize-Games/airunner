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

``import_isolation_preamble`` returns the script text both steps need so
the two isolation tests share one implementation.
"""

from __future__ import annotations

_EDITABLE_FINDER_PREFIX = "__editable__"


def import_isolation_preamble(paths: tuple[str, ...]) -> str:
    """Return script text blocking imports via *paths* and editable finders.

    The returned snippet, when run first in a subprocess, removes every
    listed entry from ``sys.path`` and every editable-install finder
    from ``sys.meta_path``.
    """
    joined = ", ".join(repr(path) for path in paths)
    finder = repr(_EDITABLE_FINDER_PREFIX)
    return (
        "import sys; "
        f"sys.path[:] = [p for p in sys.path if p not in ({joined})]; "
        "sys.meta_path[:] = [f for f in sys.meta_path "
        f"if not getattr(f, '__module__', '').startswith({finder})]; "
    )
