"""Functional tests for the path widget."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

from airunner.components.application.gui.widgets.paths.path_widget import (
    PathWidget,
)
from airunner.test_support.gui_harness import (
    FakePathSettings,
    clear_fake_api,
    click_button,
    install_fake_api,
    pump_events,
    wait_until,
)


pytestmark = [
    pytest.mark.gui,
    pytest.mark.gui_functional,
    pytest.mark.timeout(5),
]


class PathWidgetHarness(PathWidget):
    """Path widget with injectable settings for GUI functional tests."""

    def __init__(self, path_settings: FakePathSettings):
        self._test_path_settings = path_settings
        self.path_updates: list[dict[str, str]] = []
        super().__init__()

    @property
    def path_settings(self) -> FakePathSettings:
        """Return injected path settings instead of database-backed settings."""
        return self._test_path_settings

    def update_path_settings(self, **settings_dict: str) -> None:
        """Capture path-setting updates for assertions."""
        self.path_updates.append(settings_dict)
        for name, value in settings_dict.items():
            setattr(self._test_path_settings, name, value)


@pytest.fixture
def path_settings(tmp_path: Path) -> FakePathSettings:
    """Create one deterministic path-settings object for the widget."""
    base_path = tmp_path / "base"
    model_base_path = tmp_path / "models-root"
    models_path = tmp_path / "models"
    base_path.mkdir()
    model_base_path.mkdir()
    models_path.mkdir()
    return FakePathSettings(
        base_path=str(base_path),
        model_base_path=str(model_base_path),
        models_path=str(models_path),
    )


@pytest.fixture
def widget(qapp, path_settings: FakePathSettings) -> PathWidgetHarness:
    """Create one visible widget bound to the fake QApplication API."""
    install_fake_api(qapp)
    path_widget = PathWidgetHarness(path_settings)
    path_widget.setProperty("title", "Models")
    path_widget.setProperty("description", "Choose the model folder")
    path_widget.setProperty("path_name", "models_path")
    path_widget.show()
    wait_until(lambda: path_widget.isVisible(), message="Widget did not show")
    yield path_widget
    path_widget.close()
    pump_events(0)
    clear_fake_api(qapp)


def test_widget_uses_qapplication_api(widget: PathWidgetHarness, qapp) -> None:
    """The widget should resolve its API from QApplication."""
    assert widget.api is qapp.api


def test_browse_button_updates_selected_path(
    widget: PathWidgetHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Clicking browse should update the visible path and stored setting."""
    selected_path = tmp_path / "selected-models"
    selected_path.mkdir()

    def fake_dialog(_parent, _title, _directory):
        return str(selected_path)

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake_dialog)
    click_button(widget.ui.browse_button)
    wait_until(
        lambda: widget.ui.path.text() == str(selected_path),
        message="Browse click did not update the line edit",
    )
    assert widget.path_settings.models_path == str(selected_path)
    assert widget.path_updates[-1] == {"models_path": str(selected_path)}


def test_browse_button_stays_responsive_during_rapid_updates(
    widget: PathWidgetHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Rapid browse clicks should keep the widget responsive."""
    selections = []
    for index in range(3):
        path = tmp_path / f"selection-{index}"
        path.mkdir()
        selections.append(str(path))

    state = {"index": 0}

    def fake_dialog(_parent, _title, _directory):
        current = selections[state["index"]]
        state["index"] += 1
        return current

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake_dialog)

    for expected in selections:
        click_button(widget.ui.browse_button)
        wait_until(
            lambda expected_path=expected: widget.ui.path.text()
            == expected_path,
            message="Rapid browse click left the widget stale",
        )

    assert widget.path_settings.models_path == selections[-1]
    assert len(widget.path_updates) >= len(selections)