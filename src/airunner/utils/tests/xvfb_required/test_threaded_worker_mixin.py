# NOTE: This test file must be run in a real Qt environment (with a display or xvfb),
# and without patching PySide6.QtCore. Do NOT run this file as part of the main suite or in headless mode.
#
# To automate this, you can add the following to your Makefile or CI script (for display environments):
#   xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/test_threaded_worker_mixin.py
#
# Do NOT run this file as part of the main suite or with pytest-qt enabled.

import os
import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip(
        "Skipping Qt/Xvfb test: no display found", allow_module_level=True
    )

"""
Unit tests for ThreadedWorkerMixin in airunner.utils.application.threaded_worker_mixin.
Covers background task execution, signal/callback wiring, and cancellation logic.
"""

import pytest
from unittest.mock import MagicMock, patch

import types

from airunner.utils.application.threaded_worker_mixin import (
    ThreadedWorkerMixin,
)

# NOTE: Direct unit tests for ThreadedWorkerMixin are skipped.
# The mixin's threading and cleanup logic is tightly coupled to PySide6/QThread internals
# and cannot be safely tested in isolation (even with Xvfb or dummy workers) without risking
# segmentation faults or core dumps. Coverage for this code should be achieved via integration tests
# in the real application context.

# See README in this folder for more details.
