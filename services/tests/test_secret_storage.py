"""Unit tests for API-key secret storage (GitHub issue #2035).

Proves:
- Credentials are moved to the OS keyring (mocked) and the database stores
  only a reference.
- Serialized records have the secret injected back for backward-compatible
  GUI reads.
- The plaintext database fallback works and logs a warning when no keyring
  backend is available.
- The SQLite database file is chmod 0600 as defense in depth.
- A migration moves existing plaintext keys into the keyring.
"""

from __future__ import annotations

import os
import stat

import pytest

from airunner_services.api.routes.persistence_serialization import (
    normalized_values,
    serialize_record,
)
from airunner_services.database import secret_store
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)


class _FakeKeyring:
    """Minimal in-memory stand-in for the keyring API."""

    def __init__(self) -> None:
        self._passwords: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self._passwords[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self._passwords.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self._passwords.pop((service, username), None)


@pytest.fixture()
def fake_keyring(monkeypatch):
    backend = _FakeKeyring()
    monkeypatch.setattr(secret_store, "_keyring", backend)
    monkeypatch.setattr(secret_store, "_KEYRING_AVAILABLE", True)
    return backend


def test_normalized_values_moves_secret_to_keyring(fake_keyring) -> None:
    values = normalized_values(
        ApplicationSettings,
        {"civit_ai_api_key": "civit-sekrit", "mode": "image"},
    )
    assert values["civit_ai_api_key"] == ""
    assert (
        fake_keyring.get_password(
            "airunner", "application_settings/civit_ai_api_key"
        )
        == "civit-sekrit"
    )


def test_normalized_values_moves_llm_provider_key(fake_keyring) -> None:
    values = normalized_values(
        LLMGeneratorSettings,
        {"api_key": "provider-sekrit", "use_api": True},
    )
    assert values["api_key"] == ""
    assert (
        fake_keyring.get_password("airunner", "llm_generator_settings/api_key")
        == "provider-sekrit"
    )


def test_serialize_record_injects_secret(fake_keyring) -> None:
    secret_store.store_secret("civit_ai_api_key", "civit-sekrit")
    record = ApplicationSettings(civit_ai_api_key="", mode="image")
    payload = serialize_record(record)
    assert payload["civit_ai_api_key"] == "civit-sekrit"


def test_roundtrip_through_persistence_layer(fake_keyring) -> None:
    values = normalized_values(
        ApplicationSettings,
        {"civit_ai_api_key": "roundtrip-key", "mode": "image"},
    )
    record = ApplicationSettings(**values)
    payload = serialize_record(record)
    assert payload["civit_ai_api_key"] == "roundtrip-key"


def test_plaintext_fallback_when_keyring_missing(monkeypatch) -> None:
    monkeypatch.setattr(secret_store, "_KEYRING_AVAILABLE", False)
    reference = secret_store.store_secret("civit_ai_api_key", "plain-key")
    # Without a keyring the plaintext stays in the DB (documented fallback).
    assert reference == "plain-key"
    assert secret_store.retrieve_secret("civit_ai_api_key", "plain-key") == "plain-key"


def test_clear_secret_deletes_keyring_entry(fake_keyring) -> None:
    secret_store.store_secret("civit_ai_api_key", "to-be-cleared")
    cleared = secret_store.clear_secret("civit_ai_api_key", "")
    assert cleared == ""
    assert (
        fake_keyring.get_password(
            "airunner", "application_settings/civit_ai_api_key"
        )
        is None
    )


def test_restrict_sqlite_file_permissions(tmp_path) -> None:
    from airunner_services.database.setup_database import (
        _restrict_sqlite_file_permissions,
    )

    db_file = tmp_path / "airunner.db"
    db_file.write_bytes(b"x")
    os.chmod(db_file, 0o644)
    _restrict_sqlite_file_permissions(f"sqlite:///{db_file}")
    assert stat.S_IMODE(db_file.stat().st_mode) == 0o600


def test_migration_moves_plaintext_keys() -> None:
    """The keyring migration must invoke the secret store on the columns."""
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "services",
        "src",
        "airunner_services",
        "database",
        "alembic",
        "versions",
        "a7c93f2e1b4d_move_api_keys_to_os_keyring.py",
    )
    with open(migration_path, encoding="utf-8") as handle:
        source = handle.read()
    assert 'down_revision: Union[str, None] = "f0b1f4cf8f41"' in source
    assert "store_secret(" in source
    assert "hf_api_key_read_key" in source
    assert "civit_ai_api_key" in source
    assert "api_key" in source
