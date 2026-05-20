from unittest.mock import Mock

from airunner.components.llm.workers.mixins.rag_indexing_mixin import (
    RAGIndexingMixin,
)
from airunner.components.llm.managers.agent.mixins.rag_indexing_mixin import (
    EmbeddingModelDownloadPendingError,
)
from airunner.utils.path_policy import PathPolicyError
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
    monkeypatch.setattr(
        "airunner.components.llm.workers.mixins.rag_indexing_mixin"
        ".resolve_existing_file",
        lambda path, **_kwargs: path,
    )

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
    monkeypatch.setattr(
        "airunner.components.llm.workers.mixins.rag_indexing_mixin"
        ".resolve_existing_file",
        lambda path, **_kwargs: path,
    )

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


def test_rag_mixin_rejects_invalid_document_paths(monkeypatch):
    class DummyWorker(RAGIndexingMixin):
        def __init__(self):
            self.logger = Mock()
            self._signals = []

        def emit_signal(self, code, data=None):
            self._signals.append((code, data))

    worker = DummyWorker()
    monkeypatch.setattr(
        "airunner.components.llm.workers.mixins.rag_indexing_mixin"
        ".resolve_existing_file",
        lambda _path, **_kwargs: (_ for _ in ()).throw(
            PathPolicyError("Document path must be inside an approved directory")
        ),
    )

    result = worker._validate_document_path("/tmp/outside.txt")

    assert result is None
    assert worker._signals[-1][1]["error"] == (
        "Document path must be inside an approved directory"
    )


def test_rag_mixin_defers_index_while_embedding_downloads():
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

    class StubAgent:
        def _index_single_document(self, _db_doc):
            raise EmbeddingModelDownloadPendingError()

    class StubManagerWithAgent:
        def __init__(self, agent):
            self.agent = agent

    worker = DummyWorker()
    worker._model_manager = StubManagerWithAgent(StubAgent())

    fake_db_doc = Mock()
    fake_db_doc.path = "/tmp/test3.txt"
    fake_db_doc.id = 3
    worker._get_document_from_db = lambda _path: fake_db_doc

    result = worker._index_single_file(fake_db_doc.path, 0, 1)

    assert result is None
    assert worker._pending_document_index_paths == ["/tmp/test3.txt"]
    assert worker._signals[-1][1]["error"] == (
        "Embedding model download in progress. AIRunner will retry "
        "indexing automatically when the download finishes."
    )


def test_rag_mixin_queues_remaining_paths_when_retry_is_pending():
    class DummyWorker(RAGIndexingMixin):
        def __init__(self):
            self.logger = Mock()
            self._signals = []

        def emit_signal(self, code, data=None):
            self._signals.append((code, data))

        def _emit_indexing_progress(self, _idx, _total):
            return None

        def _validate_document_path(self, path):
            return path

        def _index_single_file(self, _file_path, _idx, _total):
            return None

    worker = DummyWorker()

    worker._index_documents(["/tmp/a.pdf", "/tmp/b.pdf", "/tmp/c.pdf"])

    assert worker._pending_document_index_paths == [
        "/tmp/b.pdf",
        "/tmp/c.pdf",
    ]
    assert worker._signals[-1][1] == {
        "success": False,
        "message": (
            "Embedding model download in progress. AIRunner will retry "
            "indexing automatically when the download finishes."
        ),
    }
