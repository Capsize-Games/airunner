from sqlalchemy import create_engine, inspect


def _configure_test_database(monkeypatch, db_url: str) -> None:
    import airunner.components.data.session_manager as session_manager
    import services.src.airunner_services.setup_database as setup_database_module

    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    session_manager.reset_engine()
    setup_database_module._COMPLETED_SETUP_URLS.clear()


def test_setup_database_bootstraps_core_startup_settings(
    tmp_path,
    monkeypatch,
):
    """Fresh databases should include startup settings tables and rows."""
    db_url = f"sqlite:///{tmp_path / 'fresh-airunner.db'}"
    _configure_test_database(monkeypatch, db_url)

    from airunner_model.session import session_scope
    from airunner_model.models.application_settings import (
        ApplicationSettings,
    )
    from airunner_model.models.path_settings import PathSettings
    from services.src.airunner_services.setup_database import setup_database

    setup_database()

    engine = create_engine(db_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert "application_settings" in tables
    assert "path_settings" in tables

    with session_scope() as session:
        assert session.query(ApplicationSettings).first() is not None
        assert session.query(PathSettings).first() is not None
