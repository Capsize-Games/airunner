"""Tests for the service-owned local settings store and privacy policy."""

from airunner_services.config import local_settings_store
from airunner_services.downloads import policy


def test_local_settings_store_round_trips_string_and_bool(
    monkeypatch,
    tmp_path,
) -> None:
    """The service-owned local settings store should persist values."""
    monkeypatch.setattr(
        local_settings_store,
        "AIRUNNER_BASE_PATH",
        str(tmp_path),
    )

    local_settings_store.set_setting("civitai/api_key", "token-123")
    local_settings_store.set_setting("privacy/allow_huggingface", True)

    assert local_settings_store.get_setting("civitai/api_key", "") == (
        "token-123"
    )
    assert local_settings_store.get_bool_setting(
        "privacy/allow_huggingface",
        False,
    )


def test_service_policy_uses_service_owned_settings_store(
    monkeypatch,
    tmp_path,
) -> None:
    """Privacy policy helpers should use the service-owned settings store."""
    monkeypatch.setattr(
        local_settings_store,
        "AIRUNNER_BASE_PATH",
        str(tmp_path),
    )

    policy.set_service_settings(
        {policy.SERVICE_HUGGINGFACE_KEY: False},
        consent_shown=True,
    )

    assert policy.privacy_consent_shown() is True
    assert policy.is_huggingface_allowed() is False
    assert policy.is_openrouter_allowed() is True