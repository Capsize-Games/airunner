import pytest
from PySide6.QtWidgets import QLineEdit
from airunner.gui.widgets.civitai_preferences.civitai_preferences_widget import (
    CivitAIPreferencesWidget,
)


class DummyLineEdit:
    def __init__(self):
        self._text = ""
        self._echo_mode = None
        self._signals_blocked = False

    def blockSignals(self, val):
        self._signals_blocked = val

    def setEchoMode(self, mode):
        self._echo_mode = mode

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text


class DummyUI:
    def __init__(self):
        self.api_key = DummyLineEdit()

    def setupUi(self, parent):
        pass


class DummyAppSettings:
    civit_ai_api_key = "testkey"
    dark_mode_enabled = False


class DummyBaseWidget(CivitAIPreferencesWidget):
    widget_class_ = DummyUI

    def __init__(self, *args, **kwargs):
        self._app_settings = DummyAppSettings()
        super().__init__(*args, **kwargs)

    @property
    def application_settings(self):
        return self._app_settings

    @application_settings.setter
    def application_settings(self, value):
        self._app_settings = value

    def update_application_settings(self, key, value):
        self._updated = (key, value)


@pytest.fixture
def civitai_widget(qtbot):
    widget = DummyBaseWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_civitai_preferences_happy_path(civitai_widget):
    ui = civitai_widget.ui
    assert ui.api_key._echo_mode == QLineEdit.EchoMode.Password
    assert ui.api_key.text() == "testkey"
    assert not ui.api_key._signals_blocked


def test_civitai_preferences_sad_path(civitai_widget):
    # Sad path: set to same value
    civitai_widget.on_text_changed("testkey")
    assert civitai_widget._updated == ("civitai_api_key", "testkey")


def test_civitai_preferences_bad_path(civitai_widget):
    # Bad path: set to None
    civitai_widget.on_text_changed(None)
    assert civitai_widget._updated == ("civitai_api_key", None)
