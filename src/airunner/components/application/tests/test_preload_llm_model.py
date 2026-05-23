class FakeLogger:
    def info(self, *args, **kwargs):
        return None


class FakeSignalSource:
    def __init__(self):
        self.logger = FakeLogger()
        self.emitted = []

    def emit_signal(self, code, data=None):
        self.emitted.append((code, data or {}))


def _configure_test_database(monkeypatch, db_url: str) -> None:
    import airunner.components.data.session_manager as session_manager

    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    session_manager.reset_engine()


def test_preload_creates_llm_row(tmp_path, monkeypatch):
    """Preload should create default LLM settings without launching App."""
    default_model_path = "/tmp/test-model-path"
    db_file = tmp_path / "test_airunner.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DEV_ENV", "1")
    monkeypatch.setenv("AIRUNNER_LLM_ON", "0")
    monkeypatch.setenv("AIRUNNER_DEFAULT_LLM_HF_PATH", default_model_path)
    _configure_test_database(monkeypatch, db_url)

    from services.src.airunner_services.setup_database import setup_database

    setup_database()

    import airunner.services.lifecycle_service as lifecycle_service_module

    signal_source = FakeSignalSource()
    service = lifecycle_service_module.CoreLifecycleService(
        signal_source=signal_source,
        logger=signal_source.logger,
    )
    service.preload_llm_model()

    from airunner_model.session import session_scope
    from airunner_model.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )

    with session_scope() as session:
        settings = session.query(LLMGeneratorSettings).first()
        assert settings is not None
        assert settings.model_path == default_model_path


def test_preload_emits_llm_load_signal(tmp_path, monkeypatch):
    """Preload should emit LLM_LOAD_SIGNAL without launching App."""
    from airunner.enums import SignalCode

    default_model_path = "/tmp/test-model-path"
    db_file = tmp_path / "test_airunner.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DEV_ENV", "1")
    monkeypatch.setenv("AIRUNNER_LLM_ON", "1")
    monkeypatch.setenv("AIRUNNER_DEFAULT_LLM_HF_PATH", default_model_path)
    _configure_test_database(monkeypatch, db_url)

    from services.src.airunner_services.setup_database import setup_database

    setup_database()

    import airunner.services.lifecycle_service as lifecycle_service_module

    signal_source = FakeSignalSource()
    service = lifecycle_service_module.CoreLifecycleService(
        signal_source=signal_source,
        logger=signal_source.logger,
    )
    service.preload_llm_model()

    assert any(
        code == SignalCode.LLM_LOAD_SIGNAL
        and payload.get("model_path") == default_model_path
        for code, payload in signal_source.emitted
    )
