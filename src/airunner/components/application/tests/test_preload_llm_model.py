import os
from pathlib import Path

import pytest


def test_preload_creates_llm_row(tmp_path, monkeypatch):
    """If no LLMGeneratorSettings present, and AIRUNNER_DEFAULT_LLM_HF_PATH
    is set, App._preload_llm_model should create one and store the model_path.
    """
    # Setup a temporary DB URL
    db_file = tmp_path / "test_airunner.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("DEV_ENV", "1")

    # Ensure we run in headless mode and don't start the server thread
    monkeypatch.setenv("AIRUNNER_SERVER_RUNNING", "1")
    monkeypatch.setenv("AIRUNNER_LLM_ON", "0")

    # Provide a default model path to be injected into DB when missing
    default_model_path = "/tmp/test-model-path"
    monkeypatch.setenv("AIRUNNER_DEFAULT_LLM_HF_PATH", default_model_path)

    # Create DB schema using alembic migrations
    from airunner.setup_database import setup_database

    setup_database()

    # Instantiate the App (headless)
    from airunner.app import App

    app = App(headless=True)

    # Now check that llm_generator_settings row exists with model_path set
    from airunner.components.data.session_manager import session_scope
    from airunner.components.llm.data.llm_generator_settings import (
        LLMGeneratorSettings,
    )

    with session_scope() as session:
        settings = session.query(LLMGeneratorSettings).first()
        assert settings is not None
        assert settings.model_path == default_model_path

    # Ensure threads are cleaned up to avoid Qt thread warnings and process exit failures
    try:
        app.cleanup()
    except Exception:
        pass


def test_preload_emits_llm_load_signal(tmp_path, monkeypatch):
    """If LLM is enabled and a default model path is provided, App should emit
    a SignalCode.LLM_LOAD_SIGNAL to start loading the model in the background.
    """
    from airunner.enums import SignalCode

    # Setup a temporary DB URL
    db_file = tmp_path / "test_airunner.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    monkeypatch.setenv("DEV_ENV", "1")

    # Ensure we run in headless mode and don't start the server thread
    monkeypatch.setenv("AIRUNNER_SERVER_RUNNING", "1")
    monkeypatch.setenv("AIRUNNER_LLM_ON", "1")

    # Provide a default model path to be injected into DB when missing
    default_model_path = "/tmp/test-model-path"
    monkeypatch.setenv("AIRUNNER_DEFAULT_LLM_HF_PATH", default_model_path)

    # Capture emitted signals
    emitted = []
    from airunner.utils.application.mediator_mixin import (
        MediatorMixin,
    )

    def fake_emit(self, code, data=None):
        emitted.append((code, data))

    monkeypatch.setattr(MediatorMixin, "emit_signal", fake_emit)

    # Create DB schema
    from airunner.setup_database import setup_database

    setup_database()

    # Instantiate the App (headless) - triggers preload
    from airunner.app import App

    app = App(headless=True)

    # Ensure LLM_LOAD_SIGNAL was emitted with expected model_path
    assert any(
        code == SignalCode.LLM_LOAD_SIGNAL
        and data
        and data.get("model_path") == default_model_path
        for code, data in emitted
    )

    # Ensure cleanup stops threads
    try:
        app.cleanup()
    except Exception:
        pass
