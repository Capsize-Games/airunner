"""
Unit tests for set_widget_state in set_widget_state.py.
Covers all branches.
"""

from unittest.mock import MagicMock
from airunner.utils.application.set_widget_state import set_widget_state


def test_set_widget_state_blocks_and_sets():
    widget = MagicMock()
    set_widget_state(widget, True, block_signals=True)
    widget.blockSignals.assert_any_call(True)
    widget.setChecked.assert_called_once_with(True)
    widget.blockSignals.assert_called_with(False)


def test_set_widget_state_no_block_signals():
    widget = MagicMock()
    set_widget_state(widget, False, block_signals=False)
    widget.blockSignals.assert_any_call(False)
    widget.setChecked.assert_called_once_with(False)
    widget.blockSignals.assert_called_with(False)
