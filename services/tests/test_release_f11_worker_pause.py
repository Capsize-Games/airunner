"""Worker pause/queue hardening for issue #2428.

Covers: pause() engaging the run loop (one flag, one event), resume/
unpause/stop releasing a paused worker, direct ``paused`` assignments
staying in sync with the event, and lock-guarded queue mutation under
concurrent producers.

Hermetic: no threads are left running; no GPU, network, or binds.
"""

from __future__ import annotations

import threading
from typing import Any

from airunner_services.workers.worker import (
    QueueType,
    Worker,
    WorkerState,
)


class _ProbeWorker(Worker):
    """Minimal concrete worker recording handled messages."""

    queue_type = QueueType.GET_NEXT_ITEM

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.handled: list[Any] = []

    def handle_message(self, message: Any) -> None:
        """Record one queued payload."""
        self.handled.append(message)


def test_pause_blocks_run_thread_until_resume() -> None:
    """pause() parks run_thread; resume() lets exactly one item through."""
    worker = _ProbeWorker()
    worker.pause()
    assert worker.paused is True
    assert worker.state == WorkerState.PAUSED
    worker.add_to_queue("hello")

    entered: list[str] = []
    done = threading.Event()

    def _run_once() -> None:
        entered.append("run")
        worker.running = True
        worker.run_thread()
        done.set()

    thread = threading.Thread(target=_run_once, daemon=True)
    thread.start()
    assert not done.wait(timeout=2)
    assert entered == ["run"]
    assert worker.handled == []

    worker.resume()
    assert done.wait(timeout=5)
    thread.join(timeout=5)
    assert worker.handled == ["hello"]
    assert worker.paused is False
    assert worker.state == WorkerState.RUNNING


def test_unpause_releases_and_syncs_state() -> None:
    """unpause() clears the flag and returns the state to RUNNING."""
    worker = _ProbeWorker()
    worker.pause()
    worker.unpause()
    assert worker.paused is False
    assert worker.state == WorkerState.RUNNING


def test_direct_paused_assignment_drives_event() -> None:
    """Subclass-style ``worker.paused = True`` engages the same flag."""
    worker = _ProbeWorker()
    worker.paused = True
    assert worker._resume_event.is_set() is False
    assert worker.paused is True
    worker.paused = False
    assert worker._resume_event.is_set() is True


def test_stop_releases_paused_worker() -> None:
    """stop() wakes a worker parked in pause so join never hangs."""
    worker = _ProbeWorker()
    worker.pause()
    finished: list[str] = []
    worker.finished.connect(lambda: finished.append("done"))
    worker.running = True

    done = threading.Event()

    def _park() -> None:
        worker.run_thread()
        done.set()

    thread = threading.Thread(target=_park, daemon=True)
    thread.start()
    assert not done.wait(timeout=1)
    worker.stop()
    assert done.wait(timeout=5)
    thread.join(timeout=5)
    assert finished == ["done"]


def test_concurrent_producers_keep_every_item() -> None:
    """Parallel add_to_queue calls lose and duplicate nothing."""
    worker = _ProbeWorker()
    producer_count = 8
    per_producer = 50
    barrier = threading.Barrier(producer_count)

    def _produce(offset: int) -> None:
        barrier.wait(timeout=30)
        for index in range(per_producer):
            worker.add_to_queue(f"msg-{offset}-{index}")

    threads = [
        threading.Thread(
            target=_produce, args=(slot,), daemon=True
        )
        for slot in range(producer_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not any(thread.is_alive() for thread in threads)

    assert worker.current_index == producer_count * per_producer
    assert len(worker.items) == producer_count * per_producer
    assert len(set(worker.items)) == producer_count * per_producer

    seen: set[str] = set()
    while True:
        message = worker.get_next_item()
        if message is None:
            break
        seen.add(message)
    expected = {
        f"msg-{slot}-{index}"
        for slot in range(producer_count)
        for index in range(per_producer)
    }
    assert seen == expected


def test_empty_queue_resets_under_lock() -> None:
    """empty_queue drops pending items and restarts the index."""
    worker = _ProbeWorker()
    worker.add_to_queue("a")
    worker.add_to_queue("b")
    worker.empty_queue()
    assert worker.items == {}
    assert worker.current_index == 0
    assert worker.get_next_item() is None
    worker.add_to_queue("c")
    assert worker.get_next_item() == "c"
