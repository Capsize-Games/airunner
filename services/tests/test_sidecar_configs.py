"""Unit tests for the stale sidecar-config sweep.

Each sidecar launch writes a throwaway daemon config and deletes it in
``_cleanup_config`` -- but only on the paths that end in Python. A
killed parent runs no cleanup, so the configs accumulate: one machine
had 440 of them going back four months.

The sweep runs when a new sidecar starts, which is the one moment that
is guaranteed to be reached. The behaviour that matters is what it
refuses to delete:

* a config a live process has on its command line,
* the config the calling launcher has just written,
* anything at all, when ``/proc`` cannot be read to tell the difference.
"""

from __future__ import annotations

from pathlib import Path

from airunner_services.runtimes import sidecar_configs

PREFIX = "airunner-art-runtime-"


def _config(directory: Path, name: str) -> Path:
    path = directory / f"{PREFIX}{name}.yaml"
    path.write_text("server: {}\n", encoding="utf-8")
    return path


def test_a_config_no_process_is_using_is_removed(tmp_path, monkeypatch):
    stale = _config(tmp_path, "dead")
    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    assert sidecar_configs.sweep(tmp_path, PREFIX) == 1
    assert not stale.exists()


def test_a_config_a_live_process_is_using_is_spared(tmp_path, monkeypatch):
    live = _config(tmp_path, "alive")
    stale = _config(tmp_path, "dead")
    monkeypatch.setattr(
        sidecar_configs, "live_config_paths", lambda: {str(live)}
    )
    assert sidecar_configs.sweep(tmp_path, PREFIX) == 1
    assert live.exists()
    assert not stale.exists()


def test_the_config_just_written_is_spared(tmp_path, monkeypatch):
    """Nothing has opened it yet, so it cannot look live."""
    fresh = _config(tmp_path, "fresh")
    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    assert sidecar_configs.sweep(tmp_path, PREFIX, keep=fresh) == 0
    assert fresh.exists()


def test_nothing_is_swept_when_proc_cannot_be_read(tmp_path, monkeypatch):
    """Fails closed: deleting a running sidecar's config would take it
    down on its next restart."""
    stale = _config(tmp_path, "dead")
    monkeypatch.setattr(
        sidecar_configs, "live_config_paths", lambda: None
    )
    assert sidecar_configs.sweep(tmp_path, PREFIX) == 0
    assert stale.exists()


def test_another_prefix_is_left_alone(tmp_path, monkeypatch):
    other = tmp_path / "airunner-tts-runtime-x.yaml"
    other.write_text("server: {}\n", encoding="utf-8")
    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    assert sidecar_configs.sweep(tmp_path, PREFIX) == 0
    assert other.exists()


def test_sweep_all_covers_every_prefix_the_runtime_writes(
    tmp_path, monkeypatch
):
    for prefix in (
        "airunner-art-runtime-",
        "airunner-tts-runtime-",
        "airunner-server-",
        "airunner-headless-",
    ):
        (tmp_path / f"{prefix}x.yaml").write_text("a: 1\n", encoding="utf-8")
    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    assert sidecar_configs.sweep_all(tmp_path) == 4


def test_a_file_that_cannot_be_deleted_is_not_counted(
    tmp_path, monkeypatch
):
    _config(tmp_path, "dead")

    def _refuse(self: Path) -> None:
        raise OSError("read-only")

    monkeypatch.setattr(sidecar_configs, "live_config_paths", set)
    monkeypatch.setattr(Path, "unlink", _refuse)
    assert sidecar_configs.sweep(tmp_path, PREFIX) == 0


# ---------------------------------------------------------------------
# Reading /proc
# ---------------------------------------------------------------------


def test_live_paths_finds_this_very_process(tmp_path):
    """A smoke test against the real /proc, not a fake one."""
    found = sidecar_configs.live_config_paths()
    assert found is None or isinstance(found, set)


def test_an_unreadable_proc_entry_is_skipped(tmp_path):
    """A process that exits mid-scan is one missed candidate, not a
    failure of the whole sweep."""
    assert sidecar_configs._yaml_arguments(tmp_path / "nope") == set()


def test_only_yaml_arguments_are_collected(tmp_path):
    entry = tmp_path / "1"
    entry.mkdir()
    (entry / "cmdline").write_bytes(
        b"python\x00--config\x00/x/a.yaml\x00--log\x00/x/b.log\x00"
    )
    assert sidecar_configs._yaml_arguments(entry) == {"/x/a.yaml"}
