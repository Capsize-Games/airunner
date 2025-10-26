"""Compatibility wrapper for legacy resource imports.

This module exists so older imports of ``airunner.feather_rc`` continue to
work after the resource compiler started emitting assets into
``airunner.gui.resources.feather_rc``.  The generated file under
``airunner/gui/resources`` is the canonical output produced by
``airunner-build-ui``; here we simply re-export everything so Qt's resource
registration stays consistent for callers that still import the legacy
module path.
"""

from airunner.gui.resources.feather_rc import *  # noqa: F401,F403
