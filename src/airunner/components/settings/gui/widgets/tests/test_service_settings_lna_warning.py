"""Tests for the LNA warning in the service settings widget (issue #2034).

Proves:
- Toggling the LNA checkbox shows/hides a persistent inline warning label
  (not just a tooltip).
- Loading settings with ``lna_enabled=True`` shows the warning on startup.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from airunner.components.settings.gui.widgets.service_settings_widget import (  # noqa: E402
    ServiceSettingsWidget,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_lna_warning_hidden_by_default(qapp) -> None:
    widget = ServiceSettingsWidget()
    widget.show()
    assert widget.lna_warning_label.isHidden() is True


def test_lna_warning_shows_on_toggle(qapp) -> None:
    widget = ServiceSettingsWidget()
    widget.show()
    widget.lna_enabled_cb.setChecked(True)
    assert widget.lna_warning_label.isHidden() is False
    widget.lna_enabled_cb.setChecked(False)
    assert widget.lna_warning_label.isHidden() is True


def test_lna_warning_shows_on_load_when_enabled(qapp) -> None:
    widget = ServiceSettingsWidget()
    widget.show()
    widget.set_settings({"lna_enabled": True})
    assert widget.lna_warning_label.isHidden() is False
    widget.set_settings({"lna_enabled": False})
    assert widget.lna_warning_label.isHidden() is True


def test_lna_warning_label_text_warns(qapp) -> None:
    widget = ServiceSettingsWidget()
    text = widget.lna_warning_label.text()
    assert "Local Network Access is enabled" in text
    assert "trusted networks" in text
