"""Smoke tests for RAGMixin refactoring.

These tests verify that the refactored RAGMixin works correctly after
extracting into 6 mixins + retriever class.
"""

from unittest.mock import Mock


class TestRAGMixinRefactoring:
    """Smoke tests to verify RAGMixin refactoring."""

    def test_rag_mixin_imports_successfully(self):
        """Should be able to import RAGMixin after refactoring."""
        from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

        assert RAGMixin is not None

    def test_rag_mixin_has_correct_mro(self):
        """Should have all 6 mixins in method resolution order."""
        from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

        mro_names = [cls.__name__ for cls in RAGMixin.__mro__]

        assert "RAGPropertiesMixin" in mro_names
        assert "RAGDocumentMixin" in mro_names
        assert "RAGIndexManagementMixin" in mro_names
        assert "RAGIndexingMixin" in mro_names
        assert "RAGSearchMixin" in mro_names
        assert "RAGLifecycleMixin" in mro_names

    def test_rag_mixin_has_all_public_methods(self):
        """Should have all expected public methods from mixins."""
        from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

        expected_methods = [
            # From RAGPropertiesMixin
            "text_splitter",
            "doc_indexes_dir",
            "registry_path",
            "index_registry",
            "embedding",
            "target_files",
            "rag_system_prompt",
            "storage_persist_dir",
            # From RAGDocumentMixin
            # (all private methods)
            # From RAGSearchMixin
            "search",
            "get_retriever_for_query",
            "retriever",
            # From RAGIndexingMixin
            "document_reader",
            "documents",
            "index_all_documents",
            # From RAGLifecycleMixin
            "reload_rag",
            "clear_rag_documents",
            "unload_rag",
            "load_html_into_rag",
        ]

        for method in expected_methods:
            assert hasattr(RAGMixin, method), f"Missing method: {method}"

    def test_multi_index_retriever_imports_successfully(self):
        """Should be able to import MultiIndexRetriever."""
        from airunner.components.llm.managers.agent.retriever import (
            MultiIndexRetriever,
        )

        assert MultiIndexRetriever is not None

    def test_all_mixins_import_successfully(self):
        """Should be able to import all individual mixins."""
        from airunner.components.llm.managers.agent.mixins import (
            RAGPropertiesMixin,
            RAGDocumentMixin,
            RAGIndexManagementMixin,
            RAGIndexingMixin,
            RAGSearchMixin,
            RAGLifecycleMixin,
        )

        assert RAGPropertiesMixin is not None
        assert RAGDocumentMixin is not None
        assert RAGIndexManagementMixin is not None
        assert RAGIndexingMixin is not None
        assert RAGSearchMixin is not None
        assert RAGLifecycleMixin is not None

    def test_rag_mixin_can_be_instantiated_with_mocks(self):
        """Should be able to create instance with mocked dependencies."""
        from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

        class TestRAG(RAGMixin):
            def __init__(self):
                self.logger = Mock()
                self.path_settings = Mock()
                self.path_settings.base_path = "/tmp/test"
                self.system_prompt = "Test"
                self.botname = "TestBot"
                self._skip_agent_load = True  # Skip embedding setup
                super().__init__()

        # Should not raise
        instance = TestRAG()
        assert instance is not None

    def test_target_files_property_works(self):
        """Should be able to get/set target_files property."""
        from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

        class TestRAG(RAGMixin):
            def __init__(self):
                self.logger = Mock()
                self.path_settings = Mock()
                self.path_settings.base_path = "/tmp/test"
                self.system_prompt = "Test"
                self.botname = "TestBot"
                self._skip_agent_load = True
                super().__init__()

        instance = TestRAG()

        # Should be able to set
        instance.target_files = ["file1.txt", "file2.txt"]
        assert instance.target_files == ["file1.txt", "file2.txt"]

        # Should be able to clear
        instance.target_files = None
        assert instance.target_files is None

    def test_reload_rag_clears_state(self):
        """Should clear all caches when reload_rag is called."""
        from airunner.components.llm.managers.agent.rag_mixin import RAGMixin

        class TestRAG(RAGMixin):
            def __init__(self):
                self.logger = Mock()
                self.path_settings = Mock()
                self.path_settings.base_path = "/tmp/test"
                self.system_prompt = "Test"
                self.botname = "TestBot"
                self._skip_agent_load = True
                super().__init__()

        instance = TestRAG()

        # Set some state
        instance._index = Mock()
        instance._retriever = Mock()
        instance._doc_metadata_cache["test"] = "data"

        # Reload should clear
        instance.reload_rag()

        assert instance._index is None
        assert instance._retriever is None
        assert len(instance._doc_metadata_cache) == 0
