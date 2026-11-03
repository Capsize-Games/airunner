"""The E5 worker shares the manager lock with model transitions."""

from __future__ import annotations

import threading
import time

import pytest

from airunner_services.llm.managers.agent.mixins.rag_lifecycle_mixin import (
    RAGLifecycleMixin,
)
from airunner_services.llm.managers.agent.mixins.rag_properties_mixin import (
    RAGPropertiesMixin,
)
from airunner_services.llm.managers.agent.mixins.rag_search_mixin import (
    RAGSearchMixin,
)
from airunner_services.model_management.llm_model_manager import LLMModelManager


def _assert_rlock_owned(lock: threading.RLock) -> None:
    """Assert the manager's reentrant activity lock is held by this call."""
    assert lock._is_owned()


def _physical_model_transition(
    lock: threading.RLock,
    blocked: threading.Event,
    started: threading.Event,
) -> None:
    """Try the lifecycle lock once, then wait for the active operation."""
    acquired = lock.acquire(blocking=False)
    if not acquired:
        blocked.set()
        lock.acquire()
    try:
        started.set()
    finally:
        lock.release()


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


def test_rag_query_inference_blocks_physical_model_transition() -> None:
    lock = threading.RLock()
    inference_started = threading.Event()
    allow_inference = threading.Event()
    transition_blocked = threading.Event()
    transition_started = threading.Event()

    class _Manager(RAGSearchMixin):
        runtime_activity_lock = lock

        class _Logger:
            @staticmethod
            def info(*_args, **_kwargs):
                pass

            @staticmethod
            def warning(*_args, **_kwargs):
                pass

            @staticmethod
            def error(*_args, **_kwargs):
                pass

        logger = _Logger()

        @property
        def retriever(self):
            class _Retriever:
                @staticmethod
                def retrieve(_query):
                    _assert_rlock_owned(lock)
                    inference_started.set()
                    assert allow_inference.wait(timeout=3)
                    return []

            return _Retriever()

    manager = _Manager()
    query = threading.Thread(target=manager.search, args=("query",))
    query.start()
    assert inference_started.wait(timeout=2)

    transition = threading.Thread(
        target=_physical_model_transition,
        args=(lock, transition_blocked, transition_started),
    )
    transition.start()
    assert transition_blocked.wait(timeout=2)
    assert not transition_started.is_set()

    allow_inference.set()
    query.join(timeout=2)
    transition.join(timeout=2)
    assert not query.is_alive()
    assert not transition.is_alive()
    assert transition_started.is_set()


def test_lazy_embedding_construction_blocks_physical_model_transition(
    monkeypatch, tmp_path
) -> None:
    from types import SimpleNamespace

    from airunner_services.llm.managers.agent.mixins import rag_properties_mixin
    from airunner_services.runtimes import e5_model_identity

    lock = threading.RLock()
    construction_started = threading.Event()
    allow_construction = threading.Event()
    transition_blocked = threading.Event()
    transition_started = threading.Event()
    inference_started = threading.Event()
    allow_inference = threading.Event()
    inference_transition_started = threading.Event()
    identity = SimpleNamespace(
        to_embedding_model_identity=lambda: SimpleNamespace(model_id="e5-test")
    )

    class _Embedder:
        @staticmethod
        def _block_for_inference():
            _assert_rlock_owned(lock)
            inference_started.set()
            assert allow_inference.wait(timeout=3)

        def embed_query(self, _text):
            self._block_for_inference()
            return []

        def embed_documents(self, texts):
            self._block_for_inference()
            return [[] for _text in texts]

    def verify(_model_path):
        _assert_rlock_owned(lock)
        construction_started.set()
        assert allow_construction.wait(timeout=3)
        return identity

    class _Manager(RAGPropertiesMixin):
        runtime_activity_lock = lock
        _embedding = None
        path_settings = SimpleNamespace(base_path=str(tmp_path))
        logger = SimpleNamespace(
            info=lambda *_args, **_kwargs: None,
            warning=lambda *_args, **_kwargs: None,
        )

    monkeypatch.setenv("AIRUNNER_EMBED_ENDPOINT", "")
    monkeypatch.setattr(
        e5_model_identity, "verify_e5_model_directory", verify
    )
    monkeypatch.setattr(
        rag_properties_mixin, "HuggingFaceEmbeddings", lambda **_kwargs: _Embedder()
    )
    manager = _Manager()
    constructed = []
    constructor = threading.Thread(target=lambda: constructed.append(manager.embedding))
    constructor.start()
    assert construction_started.wait(timeout=2)

    transition = threading.Thread(
        target=_physical_model_transition,
        args=(lock, transition_blocked, transition_started),
    )
    transition.start()
    assert transition_blocked.wait(timeout=2)
    assert not transition_started.is_set()

    allow_construction.set()
    constructor.join(timeout=2)
    transition.join(timeout=2)
    assert not constructor.is_alive()
    assert not transition.is_alive()
    assert transition_started.is_set()
    assert len(constructed) == 1
    assert manager._embedding is constructed[0]

    for infer in (
        lambda: manager.embedding.embed_query("query"),
        lambda: manager.embedding.embed_documents(["document"]),
    ):
        inference_started.clear()
        allow_inference.clear()
        inference_transition_started.clear()
        inference = threading.Thread(target=infer)
        inference.start()
        assert inference_started.wait(timeout=2)

        inference_transition_blocked = threading.Event()
        next_transition = threading.Thread(
            target=_physical_model_transition,
            args=(lock, inference_transition_blocked, inference_transition_started),
        )
        next_transition.start()
        assert inference_transition_blocked.wait(timeout=2)
        assert not inference_transition_started.is_set()

        allow_inference.set()
        inference.join(timeout=2)
        next_transition.join(timeout=2)
        assert not inference.is_alive()
        assert not next_transition.is_alive()
        assert inference_transition_started.is_set()
