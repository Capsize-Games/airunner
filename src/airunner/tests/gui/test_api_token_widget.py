import pytest
from PySide6.QtWidgets import QLineEdit
from airunner.gui.widgets.api_token.api_token_widget import APITokenWidget


class DummyAppSettings:
    hf_api_key_read_key = "test-token"
    dark_mode_enabled = False


@pytest.fixture
def api_token_widget(qtbot, monkeypatch):
    monkeypatch.setattr(APITokenWidget, "application_settings", DummyAppSettings())
    widget = APITokenWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_api_token_happy_path(api_token_widget):
    """
    Happy path: Test initial state and password echo mode.
    """
    ui = api_token_widget.ui
    assert ui.hf_api_key_text_generation.echoMode() == QLineEdit.EchoMode.Password
    assert ui.hf_api_key_writetoken.echoMode() == QLineEdit.EchoMode.Password
    assert ui.hf_api_key_text_generation.text() == "test-token"
    assert ui.hf_api_key_writetoken.text() == "test-token"


def test_api_token_sad_path_edit_token(api_token_widget):
    """
    Sad path: Simulate editing the API key and check update method is called.
    """
    called = {}

    def fake_update_application_settings(key, value):
        called["read"] = (key, value)

    api_token_widget.update_application_settings = fake_update_application_settings
    api_token_widget.action_text_edited_api_key("new-token")
    assert called["read"] == ("hf_api_key_read_key", "new-token")


def test_api_token_bad_path_invalid_type(api_token_widget, monkeypatch):
    """
    Bad path: Pass a non-string value to the edit action and ensure no crash.
    """
    # Patch update_settings to avoid AttributeError
    api_token_widget.update_settings = lambda *a, **kw: None
    try:
        api_token_widget.action_text_edited_api_key(12345)
        api_token_widget.action_text_edited_writekey(None)
    except Exception as e:
        pytest.fail(f"Widget should not crash on bad input: {e}")
