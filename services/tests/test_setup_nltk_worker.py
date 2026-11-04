"""Exercise owned-process installation deadlines without downloading data."""

import asyncio
import sys
from pathlib import Path

import pytest
import anyio

from airunner_services import setup_nltk_worker as worker
from airunner_services.api.routes import setup_nltk


async def _sleeping_child() -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        sys.executable, "-c", "import time; time.sleep(60)",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )


def test_install_deadline_terminates_and_reaps_child() -> None:
    async def scenario() -> None:
        process = await _sleeping_child()
        with pytest.raises(asyncio.TimeoutError):
            await setup_nltk._wait_for_worker(process, 0.03)
        assert process.returncode is not None

    asyncio.run(scenario())


def test_cancelled_install_terminates_and_reaps_child() -> None:
    async def scenario() -> None:
        process = await _sleeping_child()
        task = asyncio.create_task(setup_nltk._wait_for_worker(process, 60))
        await asyncio.sleep(0.03)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert process.returncode is not None

    asyncio.run(scenario())


def test_response_cancellation_scope_reaps_child_before_exit() -> None:
    async def scenario() -> None:
        process = await _sleeping_child()
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(setup_nltk._wait_for_worker, process, 60)
            await anyio.sleep(0.03)
            tasks.cancel_scope.cancel()
        assert process.returncode is not None

    anyio.run(scenario)


def test_language_data_stays_under_application_root(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "AIRUNNER_BASE_PATH", str(tmp_path / "data"))
    monkeypatch.setattr(worker, "is_offline_mode", lambda: False)
    rejected = tmp_path / "other" / "nltk_data"
    with pytest.raises(ValueError, match="outside the data root"):
        worker.download_nltk_data(rejected)
    assert not rejected.exists()


def test_offline_install_cannot_create_resource_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "AIRUNNER_BASE_PATH", str(tmp_path))
    monkeypatch.setattr(worker, "is_offline_mode", lambda: True)
    with pytest.raises(RuntimeError, match="requires online mode"):
        worker.download_nltk_data(tmp_path / "nltk_data")
    assert not (tmp_path / "nltk_data").exists()


def test_daemon_worker_mode_does_not_start_service(monkeypatch, tmp_path):
    from airunner_services import daemon

    installed: list[Path] = []
    monkeypatch.setattr(worker, "download_nltk_data", installed.append)
    monkeypatch.setattr(sys, "argv", [
        "airunner-daemon", "--install-nltk-data", str(tmp_path),
    ])

    def reject_start(*args, **kwargs):
        raise AssertionError("the installation child must not start a daemon")

    monkeypatch.setattr(daemon, "AIRunnerDaemon", reject_start)
    daemon.main()
    assert installed == [tmp_path]


def test_frozen_bundle_uses_its_daemon_worker_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert setup_nltk._worker_command(tmp_path) == [
        sys.executable, "--install-nltk-data", str(tmp_path),
    ]
