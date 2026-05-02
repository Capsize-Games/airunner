"""Focused tests for FastAPI legacy compatibility routes."""

from airunner.api.routes import legacy


def test_legacy_admin_shutdown_schedules_process_exit(monkeypatch):
    scheduled = []

    monkeypatch.setattr(
        legacy,
        "_schedule_process_shutdown",
        lambda delay_seconds=0.1: scheduled.append(delay_seconds),
    )

    response = legacy.legacy_admin_shutdown()

    assert response == {"status": "ok", "shutting_down": True}
    assert scheduled == [0.1]