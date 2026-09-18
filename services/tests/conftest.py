"""Shared pytest bootstrap for service-owned daemon tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# nltk >= 3.10 installs an import-security finder that blocks any
# nltk-initiated import resolving under the process CWD. In this dev
# layout the venv sits inside the project root, so site-packages is
# under the CWD and the finder misfires on ``regex``/``locale``, leaving
# a partially-initialised ``nltk`` in ``sys.modules`` that breaks every
# later ``import nltk`` (via langchain/nltk consumers). The daemon uses
# nltk's official escape hatch for the exact same false positive (see
# ``airunner_services/daemon.py``); mirror it here so the suite imports
# the real LLM stack rather than a corrupted one.
os.environ.setdefault("NLTK_DISABLE_IMPORT_SECURITY", "1")

_TEST_ROOT = Path(__file__).resolve().parent
_SERVICES_ROOT = _TEST_ROOT.parent
_PROJECT_ROOT = _SERVICES_ROOT.parent

for _path in (
    _TEST_ROOT,
    # "eval" (services/tests/eval) moved to its own repository
    # (issue #2194, https://github.com/Capsize-Games/airunner-eval).
    _PROJECT_ROOT / "services" / "src",
    # airunner_common moved to its own repository (issue #2197,
    # https://github.com/Capsize-Games/airunner-common); it's a normal
    # installed dependency of services/setup.py now, not a raw local
    # path. The old "<repo>/model/src" entry was a phantom path and is
    # removed.
    _PROJECT_ROOT / "native" / "src",
    _PROJECT_ROOT / "src",
):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.append(_path_str)