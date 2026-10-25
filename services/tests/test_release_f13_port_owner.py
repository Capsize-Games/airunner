"""Stale-daemon recycle safety for issue #2430.

Covers: only pids whose /proc cmdline carries the daemon marker are
signalled, non-matching/unreadable/own pids are skipped, a pid that
vanishes mid-recycle never raises, and the marker is re-verified
immediately before signalling (pid-reuse TOCTOU).

Hermetic: os.kill, the port scan, and cmdline reads are all doubles.
"""

from __future__ import annotations

import os
import signal

from airunner_services.api import loopback_token
from airunner_services.daemon_client.gui_daemon_client import (
    GuiDaemonClient,
)


def _reset_token_cache() -> None:
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None


def _isolate_token(tmp_path, monkeypatch) -> None:
    """Point the token store at a temp path (no real config writes)."""
    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: tmp_path / "config" / "loopback_token",
    )
    _reset_token_cache()


def _client(tmp_path, monkeypatch) -> GuiDaemonClient:
    """Return a client that never touches the network or disk."""
    _isolate_token(tmp_path, monkeypatch)
    monkeypatch.setattr(
        GuiDaemonClient,
        "_healthcheck_payload",
        lambda self, **kwargs: None,
    )
    return GuiDaemonClient(
        config_path=tmp_path / "daemon.yaml",
        auto_start=False,
    )


def _patch_scan(
    monkeypatch, client: GuiDaemonClient, pids: list[int]
) -> None:
    """Fix the port scan to return the given pids."""
    monkeypatch.setattr(
        client, "_pids_on_port", lambda port: list(pids)
    )


def test_matching_daemon_pid_is_signalled(
    tmp_path, monkeypatch
) -> None:
    """A pid carrying the daemon marker gets exactly one SIGTERM."""
    client = _client(tmp_path, monkeypatch)
    _patch_scan(monkeypatch, client, [4242])
    monkeypatch.setattr(
        client,
        "_read_pid_cmdline",
        staticmethod(
            lambda pid: "python -m airunner_services.daemon "
            "--config x.yaml"
        ),
    )
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    client._terminate_port_owner()
    assert killed == [(4242, signal.SIGTERM)]


def test_non_matching_pid_is_never_signalled(
    tmp_path, monkeypatch
) -> None:
    """An unrelated program on the port is left alone."""
    client = _client(tmp_path, monkeypatch)
    _patch_scan(monkeypatch, client, [1111])
    monkeypatch.setattr(
        client,
        "_read_pid_cmdline",
        staticmethod(lambda pid: "/usr/bin/postgres -D data"),
    )
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    client._terminate_port_owner()
    assert killed == []


def test_unreadable_cmdline_fails_closed(tmp_path, monkeypatch) -> None:
    """A pid whose cmdline cannot be read is skipped, not killed."""
    client = _client(tmp_path, monkeypatch)
    _patch_scan(monkeypatch, client, [2222])
    monkeypatch.setattr(
        client,
        "_read_pid_cmdline",
        staticmethod(lambda pid: None),
    )
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    client._terminate_port_owner()
    assert killed == []


def test_own_pid_is_skipped(tmp_path, monkeypatch) -> None:
    """The supervisor never signals itself even when marked."""
    client = _client(tmp_path, monkeypatch)
    _patch_scan(monkeypatch, client, [os.getpid()])
    monkeypatch.setattr(
        client,
        "_read_pid_cmdline",
        staticmethod(
            lambda pid: "python -m airunner_services.daemon"
        ),
    )
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    client._terminate_port_owner()
    assert killed == []


def test_vanished_pid_does_not_raise(tmp_path, monkeypatch) -> None:
    """A pid exiting mid-recycle surfaces as no kill and no error."""
    client = _client(tmp_path, monkeypatch)
    _patch_scan(monkeypatch, client, [3333])
    monkeypatch.setattr(
        client,
        "_read_pid_cmdline",
        staticmethod(
            lambda pid: "airunner-daemon --config x.yaml"
        ),
    )

    def _gone(pid: int, sig: int) -> None:
        raise ProcessLookupError(pid)

    monkeypatch.setattr(os, "kill", _gone)
    client._terminate_port_owner()


def test_marker_rechecked_before_signalling(
    tmp_path, monkeypatch
) -> None:
    """A pid reused between scan and kill is re-verified, not killed."""
    client = _client(tmp_path, monkeypatch)
    _patch_scan(monkeypatch, client, [4444])
    reads = {"count": 0}

    def _changing_cmdline(pid: int):
        reads["count"] += 1
        if reads["count"] == 1:
            return "python -m airunner_services.daemon"
        return "/usr/bin/python3 -m http.server 8188"

    monkeypatch.setattr(
        client,
        "_read_pid_cmdline",
        staticmethod(_changing_cmdline),
    )
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        os, "kill", lambda pid, sig: killed.append((pid, sig))
    )
    client._terminate_port_owner()
    assert killed == []
    assert reads["count"] == 2


def test_marker_requires_both_words(tmp_path, monkeypatch) -> None:
    """'airunner' alone (or 'daemon' alone) is not the daemon marker."""
    client = _client(tmp_path, monkeypatch)
    for cmdline, expected in [
        ("python -m airunner_services.daemon", True),
        ("/opt/airunner-daemon/bin/daemon", True),
        ("python -m airunner", False),
        ("postgres daemon helper", False),
        ("", False),
    ]:
        monkeypatch.setattr(
            client,
            "_read_pid_cmdline",
            staticmethod(lambda pid, text=cmdline: text or None),
        )
        assert client._pid_is_daemon_owner(9999) is expected
