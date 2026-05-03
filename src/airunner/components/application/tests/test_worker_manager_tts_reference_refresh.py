"""Tests for daemon-backed TTS refresh on reference speaker changes."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.application.gui.windows.main.worker_manager import (
    WorkerManager,
)
from airunner.enums import ModelType, TTSModel


def test_reference_speaker_change_restarts_daemon_tts():
    control = Mock(return_value=True)
    manager = SimpleNamespace(
        _daemon_client=lambda: object(),
        application_settings=SimpleNamespace(tts_enabled=True),
        chatbot_voice_model_type=TTSModel.OPENVOICE,
        _stop_tts_activity_immediately=Mock(),
        _tts_runtime_route_metadata=Mock(
            return_value={"model_type": "OpenVoice"}
        ),
        _control_daemon_runtime_async=control,
    )

    WorkerManager._refresh_daemon_tts_for_reference_speaker_change(
        manager,
        {
            "setting_name": "openvoice_settings",
            "column_name": "reference_speaker_path",
        },
    )

    unload_call = control.call_args_list[0]
    assert unload_call.args[:3] == ("tts", "unload", ModelType.TTS)
    unload_call.kwargs["before_request"]()
    manager._stop_tts_activity_immediately.assert_called_once_with()

    unload_call.kwargs["after_success"]()
    load_call = control.call_args_list[1]
    assert load_call.args[:3] == ("tts", "load", ModelType.TTS)
    assert load_call.kwargs["route_metadata"] == {
        "model_type": "OpenVoice"
    }


def test_reference_speaker_change_ignores_disabled_tts():
    control = Mock()
    manager = SimpleNamespace(
        _daemon_client=lambda: object(),
        application_settings=SimpleNamespace(tts_enabled=False),
        chatbot_voice_model_type=TTSModel.OPENVOICE,
        _control_daemon_runtime_async=control,
    )

    WorkerManager._refresh_daemon_tts_for_reference_speaker_change(
        manager,
        {
            "setting_name": "openvoice_settings",
            "column_name": "reference_speaker_path",
        },
    )

    control.assert_not_called()