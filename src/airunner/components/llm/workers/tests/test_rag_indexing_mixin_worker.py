from unittest.mock import Mock

from airunner.components.llm.workers.mixins.rag_indexing_mixin import (
    RAGIndexingMixin,
)
from unittest.mock import Mock


class StubModelManager:
    def __init__(self):
        self.index_all_called = False
        self.indexed_paths = []
        self.do_interrupt = False

    def load(self):
        # no-op for tests
        return None

    def index_all_documents(self):
        self.index_all_called = True

    def _index_single_document(self, db_doc):
        self.indexed_paths.append(db_doc.path)
        return True


def test_rag_mixin_uses_manager_when_agent_missing(monkeypatch):
    """If model_manager.agent is missing but the manager itself supports indexing,
    the mixin should use the manager's methods to perform indexing."""

    class DummyWorker(RAGIndexingMixin):
        def __init__(self):
            self.logger = Mock()
            self._model_manager = None
            self._signals = []

        @property
        def model_manager(self):
            return self._model_manager

        def emit_signal(self, code, data=None):
            self._signals.append((code, data))

        def load(self):
            # Simulate load which won't set an agent
            return None

    worker = DummyWorker()
    stub = StubModelManager()
    worker._model_manager = stub

    # Replace DB document lookup with a stub object that has a path
    fake_db_doc = Mock()
    fake_db_doc.path = "/tmp/test.txt"
    fake_db_doc.id = 1
    worker._get_document_from_db = lambda p: fake_db_doc
    assert worker._get_document_from_db(fake_db_doc.path) is fake_db_doc

    # Call single-file indexing function directly and ensure manager was used
    worker._index_single_file(fake_db_doc.path, 0, 1)
    assert stub.indexed_paths == ["/tmp/test.txt"]

    # Call full index
    worker._perform_all_documents_indexing()
    assert stub.index_all_called


def test_rag_mixin_prefers_agent_over_manager(monkeypatch):
    """If model_manager.agent is present, the mixin should prefer calling agent methods."""

    class DummyWorker(RAGIndexingMixin):
        def __init__(self):
            self.logger = Mock()
            self._model_manager = None
            self._signals = []

        @property
        def model_manager(self):
            return self._model_manager

        def emit_signal(self, code, data=None):
            self._signals.append((code, data))

        def load(self):
            return None

    worker = DummyWorker()

    class StubAgent:
        def __init__(self):
            self.index_all_called = False
            self.indexed_paths = []

        def index_all_documents(self):
            self.index_all_called = True

        def _index_single_document(self, db_doc):
            self.indexed_paths.append(db_doc.path)
            return True

    class StubManagerWithAgent:
        def __init__(self, agent):
            self.agent = agent

        def load(self):
            return None

    agent = StubAgent()
    mgr = StubManagerWithAgent(agent)
    worker._model_manager = mgr

    fake_db_doc = Mock()
    fake_db_doc.path = "/tmp/test2.txt"
    fake_db_doc.id = 2
    worker._get_document_from_db = lambda p: fake_db_doc

    worker._index_single_file(fake_db_doc.path, 0, 1)
    assert agent.indexed_paths == ["/tmp/test2.txt"]

    worker._perform_all_documents_indexing()
    assert agent.index_all_called
