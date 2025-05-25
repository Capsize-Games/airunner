import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.api.api import API
from airunner.enums import (
    SignalCode,
    ModelType,
    ModelStatus,
    EngineResponseCode,
)


@pytest.fixture
def api():
    # Patch App.__init__ to avoid side effects
    with patch("airunner.api.api.App.__init__", return_value=None):
        # Patch the property at the class level
        original_property = API.emit_signal
        mock_emit_signal = MagicMock()
        API.emit_signal = property(lambda self: mock_emit_signal)

        try:
            api = API(initialize_app=False, initialize_gui=False)
            api.mediator = MagicMock()
            # Store the mock for easy access in tests
            api._test_mock_emit_signal = mock_emit_signal
            yield api
        finally:
            # Restore original property
            API.emit_signal = original_property


def test_change_model_status_happy(api):
    api.change_model_status(ModelType.SD, ModelStatus.LOADED)
    api.emit_signal.assert_called_once_with(
        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
        {"model": ModelType.SD, "status": ModelStatus.LOADED},
    )


def test_change_model_status_bad(api):
    # Bad path: Test with None values (no validation in method, so just verify it passes through)
    api.change_model_status(None, None)
    api.emit_signal.assert_called_once_with(
        SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
        {"model": None, "status": None},
    )


def test_worker_response_happy(api):
    api.worker_response(EngineResponseCode.IMAGE_GENERATED, {"msg": "ok"})
    api.emit_signal.assert_called_once_with(
        SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
        {"code": EngineResponseCode.IMAGE_GENERATED, "message": {"msg": "ok"}},
    )


def test_worker_response_bad(api):
    # Bad path: Test with None message (no validation in method, so just verify it passes through)
    api.worker_response(EngineResponseCode.IMAGE_GENERATED, None)
    api.emit_signal.assert_called_once_with(
        SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
        {"code": EngineResponseCode.IMAGE_GENERATED, "message": None},
    )


def test_quit_application(api):
    api.quit_application()
    api.emit_signal.assert_called_once_with(SignalCode.QUIT_APPLICATION, {})


def test_application_error(api):
    api.application_error("fail")
    api.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_STATUS_ERROR_SIGNAL, {"message": "fail"}
    )


def test_application_status(api):
    api.application_status("ok")
    api.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_STATUS_INFO_SIGNAL, {"message": "ok"}
    )


def test_update_download_log(api):
    api.update_download_log("log")
    api.emit_signal.assert_called_once_with(
        SignalCode.UPDATE_DOWNLOAD_LOG, {"message": "log"}
    )


def test_set_download_progress(api):
    api.set_download_progress(1, 2)
    api.emit_signal.assert_called_once_with(
        SignalCode.DOWNLOAD_PROGRESS, {"current": 1, "total": 2}
    )


def test_clear_download_status(api):
    api.clear_download_status()
    api.emit_signal.assert_called_once_with(
        SignalCode.CLEAR_DOWNLOAD_STATUS_BAR
    )


def test_set_download_status(api):
    api.set_download_status("msg")
    api.emit_signal.assert_called_once_with(
        SignalCode.SET_DOWNLOAD_STATUS_LABEL, {"message": "msg"}
    )


def test_download_complete(api):
    api.download_complete("file.txt")
    api.emit_signal.assert_called_once_with(
        SignalCode.DOWNLOAD_COMPLETE, {"file_name": "file.txt"}
    )


def test_clear_status_message(api):
    api.clear_status_message()
    api.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL
    )


def test_main_window_loaded(api):
    api.main_window_loaded("mainwin")
    api.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL,
        {"main_window": "mainwin"},
    )


def test_clear_prompts(api):
    api.clear_prompts()
    api.emit_signal.assert_called_once_with(SignalCode.CLEAR_PROMPTS)


def test_keyboard_shortcuts_updated(api):
    api.keyboard_shortcuts_updated()
    api.emit_signal.assert_called_once_with(
        SignalCode.KEYBOARD_SHORTCUTS_UPDATED
    )


def test_reset_paths(api):
    api.reset_paths()
    api.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_RESET_PATHS_SIGNAL
    )


def test_application_settings_changed(api):
    api.application_settings_changed("foo", "bar", 123)
    api.emit_signal.assert_called_once_with(
        SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
        {"setting_name": "foo", "column_name": "bar", "value": 123},
    )


def test_widget_element_changed(api):
    api.widget_element_changed("el", "valname", 42)
    api.emit_signal.assert_called_once_with(
        SignalCode.WIDGET_ELEMENT_CHANGED_SIGNAL,
        {"element": "el", "valname": 42},
    )


def test_delete_prompt(api):
    api.delete_prompt(99)
    api.emit_signal.assert_called_once_with(
        SignalCode.SD_ADDITIONAL_PROMPT_DELETE_SIGNAL, {"prompt_id": 99}
    )


def test_refresh_stylesheet(api):
    api.refresh_stylesheet(True, False)
    api.emit_signal.assert_called_once_with(
        SignalCode.REFRESH_STYLESHEET_SIGNAL,
        {"dark_mode": True, "override_system_theme": False},
    )


def test_retranslate_ui_signal(api):
    api.retranslate_ui_signal()
    api.emit_signal.assert_called_once_with(SignalCode.RETRANSLATE_UI_SIGNAL)


def test_update_locale(api):
    api.update_locale({"lang": "en"})
    api.emit_signal.assert_called_once_with(
        SignalCode.UPATE_LOCALE, {"lang": "en"}
    )


def test_llm_model_download_progress(api):
    api.llm_model_download_progress(77)
    api.emit_signal.assert_called_once_with(
        SignalCode.LLM_MODEL_DOWNLOAD_PROGRESS, {"percent": 77}
    )


def test_connect_signal(api):
    handler = MagicMock()
    with patch.object(api, "register_signal_handler") as reg:
        api.connect_signal(SignalCode.CLEAR_PROMPTS, handler)
        reg.assert_called_once_with(SignalCode.CLEAR_PROMPTS, handler)


def test_register_signal_handler(api):
    handler = MagicMock()
    with patch.object(api, "register") as reg:
        api.register_signal_handler(SignalCode.CLEAR_PROMPTS, handler)
        reg.assert_called_once_with(SignalCode.CLEAR_PROMPTS, handler)


def test_send_image_request(api):
    req = MagicMock()
    api.send_image_request(req)
    api.emit_signal.assert_called_once_with(
        SignalCode.DO_GENERATE_SIGNAL, {"image_request": req}
    )
