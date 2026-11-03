"""The E5 worker shares the manager lock with model transitions."""

from __future__ import annotations

import threading
import time

import pytest

from airunner_services.llm.managers.agent.mixins.rag_lifecycle_mixin import (
    RAGLifecycleMixin,
)
from airunner_services.model_management.llm_model_manager import LLMModelManager


def _assert_rlock_owned(lock: threading.RLock) -> None:
    """Assert the manager's reentrant activity lock is held by this call."""
    assert lock._is_owned()


def test_llm_load_and_unload_hold_the_runtime_activity_lock() -> None:
    manager = object.__new__(LLMModelManager)
    manager._request_state_lock = threading.RLock()
    manager._runtime_activity_lock = threading.RLock()
    called = []

    def load_locked():
        _assert_rlock_owned(manager._runtime_activity_lock)
        assert not manager._request_state_lock._is_owned()
        called.append("load")

    def unload_locked():
        _assert_rlock_owned(manager._runtime_activity_lock)
        assert not manager._request_state_lock._is_owned()
        called.append("unload")

    manager._load_model_locked = load_locked
    manager._unload_model_locked = unload_locked

    manager.load()
    manager.unload()

    assert called == ["load", "unload"]


@pytest.mark.parametrize("operation", ["load", "unload"])
def test_embedding_waits_for_physical_model_transition(operation: str) -> None:
    manager = object.__new__(LLMModelManager)
    manager._request_state_lock = threading.RLock()
    manager._runtime_activity_lock = threading.RLock()
    transition_started = threading.Event()
    allow_transition = threading.Event()
    embedding_started = threading.Event()

    def transition_body():
        _assert_rlock_owned(manager.runtime_activity_lock)
        assert not manager._request_state_lock._is_owned()
        transition_started.set()
        assert allow_transition.wait(timeout=3)

    if operation == "load":
        manager._load_model_locked = transition_body
    else:
        manager._unload_model_locked = transition_body

    transition = threading.Thread(target=getattr(manager, operation))
    transition.start()
    assert transition_started.wait(timeout=2)

    def embedding_activity():
        with manager.runtime_activity_lock:
            embedding_started.set()

    embedding = threading.Thread(target=embedding_activity)
    embedding.start()
    time.sleep(0.05)
    assert not embedding_started.is_set()

    allow_transition.set()
    transition.join(timeout=2)
    embedding.join(timeout=2)
    assert not transition.is_alive()
    assert not embedding.is_alive()
    assert embedding_started.is_set()


def test_unload_rag_uses_the_same_manager_activity_lock() -> None:
    lock = threading.RLock()

    class _Manager(RAGLifecycleMixin):
        runtime_activity_lock = lock

        def _unload_rag_locked(self):
            _assert_rlock_owned(lock)
            self.unload_called = True

    manager = _Manager()
    manager.unload_rag()
    assert manager.unload_called
