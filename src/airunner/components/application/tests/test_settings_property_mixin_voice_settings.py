"""Tests for active voice-specific TTS settings resolution."""

from types import SimpleNamespace

from airunner.components.application.gui.windows.main.mixins.settings_property_mixin import (
    SettingsPropertyMixin,
)


class _Cache:
    def __init__(self):
        self.values = {}

    def get_cached_setting(self, model_class):
        return self.values.get(model_class)

    def set_cached_setting(self, model_class, instance):
        self.values[model_class] = instance


class _DummySettingsMixin(SettingsPropertyMixin):
    def __init__(self, chatbot, voice_settings, cache):
        self.chatbot = chatbot
        self._voice_settings = voice_settings
        self._cache = cache

    @property
    def chatbot_voice_settings(self):
        return self._voice_settings

    @property
    def settings_mixin_shared_instance(self):
        return self._cache


def test_openvoice_settings_uses_active_voice_settings_id(monkeypatch):
    settings_model = type("OpenVoiceSettings", (), {})
    settings_model.objects = SimpleNamespace(
        get=lambda pk: SimpleNamespace(id=pk, reference_speaker_path="voice.wav"),
        first=lambda: SimpleNamespace(id=1, reference_speaker_path="first.wav"),
        create=lambda: SimpleNamespace(id=2, reference_speaker_path="created.wav"),
    )

    monkeypatch.setattr(
        "airunner.components.application.gui.windows.main.mixins"
        ".settings_property_mixin.get_settings_model",
        lambda name: settings_model,
    )

    mixin = _DummySettingsMixin(
        chatbot=SimpleNamespace(voice_id=9),
        voice_settings=SimpleNamespace(
            model_type="OpenVoice",
            settings_id=42,
        ),
        cache=_Cache(),
    )

    settings = mixin.openvoice_settings

    assert settings.id == 42


def test_openvoice_settings_replaces_stale_cached_row(monkeypatch):
    settings_model = type("OpenVoiceSettings", (), {})
    settings_model.objects = SimpleNamespace(
        get=lambda pk: SimpleNamespace(id=pk),
        first=lambda: SimpleNamespace(id=1),
        create=lambda: SimpleNamespace(id=2),
    )

    monkeypatch.setattr(
        "airunner.components.application.gui.windows.main.mixins"
        ".settings_property_mixin.get_settings_model",
        lambda name: settings_model,
    )

    cache = _Cache()
    cache.set_cached_setting(settings_model, SimpleNamespace(id=5))
    mixin = _DummySettingsMixin(
        chatbot=SimpleNamespace(voice_id=3),
        voice_settings=SimpleNamespace(
            model_type="OpenVoice",
            settings_id=77,
        ),
        cache=cache,
    )

    settings = mixin.openvoice_settings

    assert settings.id == 77


def test_rag_settings_creates_row_without_removed_enabled_field(monkeypatch):
    created = {}
    rows = []

    class _Objects:
        @staticmethod
        def first():
            return rows[0] if rows else None

        @staticmethod
        def create(**kwargs):
            created.update(kwargs)
            row = SimpleNamespace(id=1, **kwargs)
            rows.append(row)
            return row

    settings_model = type("RAGSettings", (), {"objects": _Objects()})

    monkeypatch.setattr(
        "airunner.components.application.gui.windows.main.mixins"
        ".settings_property_mixin.get_settings_model",
        lambda name: settings_model,
    )

    mixin = _DummySettingsMixin(
        chatbot=SimpleNamespace(voice_id=3),
        voice_settings=SimpleNamespace(model_type="OpenVoice", settings_id=77),
        cache=_Cache(),
    )

    settings = mixin.rag_settings

    assert settings.id == 1
    assert created == {
        "model_service": "local",
        "model_path": "",
    }