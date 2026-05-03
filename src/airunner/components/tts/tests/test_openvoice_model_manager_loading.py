"""Tests for OpenVoice model-manager warmup behavior."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.tts.managers.openvoice_model_manager import (
    OpenVoiceModelManager,
)
from airunner.enums import AvailableLanguage, ModelStatus, ModelType


def test_load_warms_model_components(monkeypatch):
    fake_tts = SimpleNamespace(unload=Mock())
    manager = SimpleNamespace(
        _model_status={ModelType.TTS: ModelStatus.UNLOADED},
        logger=SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        ),
        _skip_download_check=False,
        _check_and_trigger_download=Mock(return_value=(False, {})),
        change_model_status=Mock(),
        model=None,
        _initialize=Mock(),
        _warm_model_components=Mock(),
        language=AvailableLanguage.EN,
    )

    monkeypatch.setattr(
        "airunner.components.tts.managers.openvoice_model_manager.TTS",
        lambda language: fake_tts,
    )

    loaded = OpenVoiceModelManager.load(manager)

    assert loaded is True
    manager._initialize.assert_called_once_with()
    manager._warm_model_components.assert_called_once_with()
    assert manager.model is fake_tts
    assert manager.change_model_status.call_args_list[0].args == (
        ModelType.TTS,
        ModelStatus.LOADING,
    )
    assert manager.change_model_status.call_args_list[-1].args == (
        ModelType.TTS,
        ModelStatus.LOADED,
    )


def test_warm_model_components_runs_full_inference_warmup(monkeypatch):
    warm_melo = Mock()
    monkeypatch.setattr(
        "airunner.components.tts.managers.openvoice_model_manager.warm_melo_tts",
        warm_melo,
    )

    manager = SimpleNamespace(
        model=SimpleNamespace(),
        language=AvailableLanguage.EN,
        chatbot=SimpleNamespace(gender="Female"),
        generate=Mock(return_value=object()),
        logger=SimpleNamespace(info=Mock()),
        _warm_inference_path=lambda: OpenVoiceModelManager._warm_inference_path(
            manager
        ),
    )

    OpenVoiceModelManager._warm_model_components(manager)

    warm_melo.assert_called_once_with(manager.model, AvailableLanguage.EN)
    manager.generate.assert_called_once()
    warmup_request = manager.generate.call_args.args[0]
    assert warmup_request.message == "Warm up."
    assert warmup_request.gender == "Female"