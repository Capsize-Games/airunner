"""Tests for OpenVoice preferences widget helpers."""

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.tts.gui.widgets.open_voice_preferences_widget import (
    OpenVoicePreferencesWidget,
)
from airunner.enums import TTSModel
from airunner.utils.path_policy import PathPolicyError


def test_import_widget_does_not_touch_pkg_info(tmp_path):
    code = """
import builtins
import sys

orig_open = builtins.open


def traced_open(file, *args, **kwargs):
    if str(file).endswith('PKG-INFO'):
        print(file)
    return orig_open(file, *args, **kwargs)


builtins.open = traced_open
import airunner.components.tts.gui.widgets.open_voice_preferences_widget
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "PKG-INFO" not in result.stdout


def test_store_reference_speaker_path_updates_settings(monkeypatch):
    settings = SimpleNamespace(reference_speaker_path="old.wav")
    update = Mock()
    notify = Mock()
    item = SimpleNamespace(reference_speaker_path="old.wav")
    widget = SimpleNamespace(
        _id=7,
        _item=item,
        _notify_api_or_app=notify,
        logger=Mock(),
    )

    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".OpenVoiceSettings.objects.get",
        lambda _id: settings,
    )
    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".OpenVoiceSettings.objects.update",
        update,
    )
    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".normalize_local_path",
        lambda path, **_kwargs: path,
    )
    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".os.path.isfile",
        lambda _path: True,
    )
    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".resolve_existing_file",
        lambda path, **_kwargs: path,
    )

    OpenVoicePreferencesWidget._store_reference_speaker_path(
        widget,
        "new.wav",
    )

    update.assert_called_once_with(7, reference_speaker_path="new.wav")
    notify.assert_called_once_with(
        "openvoice_settings",
        "reference_speaker_path",
        "new.wav",
    )
    assert item.reference_speaker_path == "new.wav"


def test_store_reference_speaker_path_rejects_remote_uri(monkeypatch):
    settings = SimpleNamespace(reference_speaker_path="old.wav")
    update = Mock()
    notify = Mock()
    logger = Mock()
    item = SimpleNamespace(reference_speaker_path="old.wav")
    widget = SimpleNamespace(
        _id=7,
        _item=item,
        _notify_api_or_app=notify,
        logger=logger,
    )

    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".OpenVoiceSettings.objects.get",
        lambda _id: settings,
    )
    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".OpenVoiceSettings.objects.update",
        update,
    )
    monkeypatch.setattr(
        "airunner.components.tts.gui.widgets.open_voice_preferences_widget"
        ".normalize_local_path",
        lambda _path, **_kwargs: (_ for _ in ()).throw(
            PathPolicyError("Reference speaker path must be local")
        ),
    )

    OpenVoicePreferencesWidget._store_reference_speaker_path(
        widget,
        "https://example.com/voice.wav",
    )

    update.assert_not_called()
    notify.assert_not_called()
    logger.error.assert_called_once()


def test_should_precompute_in_background_when_tts_disabled():
    widget = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=False),
        chatbot_voice_model_type=TTSModel.OPENVOICE,
    )

    assert OpenVoicePreferencesWidget._should_precompute_in_background(
        widget
    ) is True


def test_should_not_precompute_for_active_openvoice_runtime():
    widget = SimpleNamespace(
        application_settings=SimpleNamespace(tts_enabled=True),
        chatbot_voice_model_type=TTSModel.OPENVOICE,
    )

    assert OpenVoicePreferencesWidget._should_precompute_in_background(
        widget
    ) is False