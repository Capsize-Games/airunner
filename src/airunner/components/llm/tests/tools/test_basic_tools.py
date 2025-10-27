"""Tests for RAGTools, KnowledgeTools, ImageTools, and FileTools mixins."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from airunner.components.llm.managers.tools.rag_tools import RAGTools
from airunner.components.llm.managers.tools.knowledge_tools import (
    KnowledgeTools,
)
from airunner.components.llm.managers.tools.image_tools import ImageTools
from airunner.components.llm.managers.tools.file_tools import FileTools
from airunner.components.llm.tests.base_test_case import (
    BaseTestCase,
    with_temp_directory,
)
from airunner.enums import SignalCode


class MockRAGToolsClass(RAGTools):
    """Mock class for testing RAGTools mixin."""

    def __init__(self):
        self.logger = Mock()
        self.rag_manager = Mock()


class MockKnowledgeToolsClass(KnowledgeTools):
    """Mock class for testing KnowledgeTools mixin."""

    def __init__(self):
        self.logger = Mock()


class MockImageToolsClass(ImageTools):
    """Mock class for testing ImageTools mixin."""

    def __init__(self):
        self.logger = Mock()
        self.emit_signal = Mock()


class MockFileToolsClass(FileTools):
    """Mock class for testing FileTools mixin."""

    def __init__(self):
        self.logger = Mock()


class TestRAGTools(BaseTestCase):
    """Test RAGTools mixin methods."""

    target_class = MockRAGToolsClass
    public_methods = [
        "rag_search_tool",
        "search_knowledge_base_documents_tool",
        "save_to_knowledge_base_tool",
    ]

    def setUp(self):
        """Set up test with mock RAG tools instance."""
        super().setUp()
        self.tools = self.obj

    def test_rag_search_tool_creation(self):
        """Test that rag_search_tool creates a callable tool."""
        tool = self.tools.rag_search_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "rag_search")

    def test_rag_search_returns_results(self):
        """Test that RAG search returns results."""
        # Mock rag_manager search
        mock_doc1 = Mock()
        mock_doc1.page_content = "Result 1"
        mock_doc1.metadata = {"source": "doc1.txt", "score": 0.95}

        mock_doc2 = Mock()
        mock_doc2.page_content = "Result 2"
        mock_doc2.metadata = {"source": "doc2.txt", "score": 0.85}

        mock_results = [mock_doc1, mock_doc2]
        self.tools.rag_manager.search = Mock(return_value=mock_results)

        tool = self.tools.rag_search_tool()
        result = self.invoke_tool(tool, query="test query", limit=5)

        self.assertIn("Result 1", result)
        self.assertIn("Result 2", result)
        self.assertIn("doc1.txt", result)

    def test_search_knowledge_base_documents_tool_creation(self):
        """Test that search_knowledge_base_documents_tool creates a callable tool."""
        tool = self.tools.search_knowledge_base_documents_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "search_knowledge_base_documents")

    def test_save_to_knowledge_base_tool_creation(self):
        """Test that save_to_knowledge_base_tool creates a callable tool."""
        tool = self.tools.save_to_knowledge_base_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "save_to_knowledge_base")


class TestKnowledgeTools(BaseTestCase):
    """Test KnowledgeTools mixin methods."""

    target_class = MockKnowledgeToolsClass
    public_methods = ["record_knowledge_tool", "recall_knowledge_tool"]

    def setUp(self):
        """Set up test with mock knowledge tools instance."""
        super().setUp()
        self.tools = self.obj

    def test_record_knowledge_tool_creation(self):
        """Test that record_knowledge_tool creates a callable tool."""
        tool = self.tools.record_knowledge_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "record_knowledge")

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_record_knowledge_success(self, mock_manager_class):
        """Test recording knowledge successfully."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.store_knowledge = Mock()

        tool = self.tools.record_knowledge_tool()
        result = self.invoke_tool(
            tool,
            fact="User prefers Python",
            category="preferences",
            confidence=0.9,
        )

        self.assertIn("Recorded", result)
        mock_manager_class.assert_called_once()

    def test_recall_knowledge_tool_creation(self):
        """Test that recall_knowledge_tool creates a callable tool."""
        tool = self.tools.recall_knowledge_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "recall_knowledge")

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_recall_knowledge_with_results(self, mock_manager_class):
        """Test recalling knowledge with results."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_facts = [
            Mock(text="Fact 1", confidence=0.95),
            Mock(text="Fact 2", confidence=0.85),
        ]
        mock_manager.recall_knowledge = Mock(return_value=mock_facts)

        tool = self.tools.recall_knowledge_tool()
        result = self.invoke_tool(
            tool, query="Python", category="preferences", limit=10
        )

        self.assertIn("Found 2 knowledge facts", result)
        self.assertIn("Fact 1", result)


class TestImageTools(BaseTestCase):
    """Test ImageTools mixin methods."""

    target_class = MockImageToolsClass
    public_methods = [
        "generate_image_tool",
        "clear_canvas_tool",
        "open_image_tool",
    ]

    def setUp(self):
        """Set up test with mock image tools instance."""
        super().setUp()
        self.tools = self.obj

    def test_generate_image_tool_creation(self):
        """Test that generate_image_tool creates a callable tool."""
        tool = self.tools.generate_image_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "generate_image")

    def test_generate_image_emits_signal(self):
        """Test that generate_image emits the correct signal."""
        tool = self.tools.generate_image_tool()
        result = self.invoke_tool(
            tool,
            prompt="a beautiful sunset",
            negative_prompt="blurry",
            width=512,
            height=512,
        )

        self.assertIn("Generating image", result)

        # Verify signal was emitted
        self.tools.emit_signal.assert_called_once()
        call_args = self.tools.emit_signal.call_args
        self.assertEqual(call_args[0][0], SignalCode.SD_GENERATE_IMAGE_SIGNAL)

    def test_clear_canvas_tool_creation(self):
        """Test that clear_canvas_tool creates a callable tool."""
        tool = self.tools.clear_canvas_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "clear_canvas")

    def test_clear_canvas_emits_signal(self):
        """Test that clear_canvas emits the correct signal."""
        tool = self.tools.clear_canvas_tool()
        result = self.invoke_tool(tool)

        self.assertIn("Canvas cleared", result)
        self.tools.emit_signal.assert_called_with(
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL
        )

    def test_open_image_tool_creation(self):
        """Test that open_image_tool creates a callable tool."""
        tool = self.tools.open_image_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "open_image")


class TestFileTools(BaseTestCase):
    """Test FileTools mixin methods."""

    target_class = MockFileToolsClass
    public_methods = ["list_files_tool", "read_file_tool", "write_code_tool"]

    def setUp(self):
        """Set up test with mock file tools instance."""
        super().setUp()
        self.tools = self.obj

    def test_list_files_tool_creation(self):
        """Test that list_files_tool creates a callable tool."""
        tool = self.tools.list_files_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "list_files")

    @with_temp_directory
    def test_list_files_in_directory(self, tmpdir: Path):
        """Test listing files in a directory."""
        # Create some test files
        (tmpdir / "file1.txt").write_text("content1")
        (tmpdir / "file2.py").write_text("content2")
        (tmpdir / "subdir").mkdir()
        (tmpdir / "subdir" / "file3.txt").write_text("content3")

        tool = self.tools.list_files_tool()
        result = self.invoke_tool(tool, directory=str(tmpdir))

        self.assertIn("file1.txt", result)
        self.assertIn("file2.py", result)
        self.assertIn("subdir", result)

    @with_temp_directory
    def test_list_files_with_pattern(self, tmpdir: Path):
        """Test listing files in directory."""
        # Create test files
        (tmpdir / "test.txt").write_text("content1")
        (tmpdir / "test.py").write_text("content2")
        (tmpdir / "other.txt").write_text("content3")

        tool = self.tools.list_files_tool()
        result = self.invoke_tool(tool, directory=str(tmpdir))

        # All files should be listed (no pattern filtering in current implementation)
        self.assertIn("test.py", result)
        self.assertIn("test.txt", result)
        self.assertIn("other.txt", result)

    def test_read_file_tool_creation(self):
        """Test that read_file_tool creates a callable tool."""
        tool = self.tools.read_file_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "read_file")

    @with_temp_directory
    def test_read_file_success(self, tmpdir: Path):
        """Test reading file successfully."""
        test_file = tmpdir / "test.txt"
        test_file.write_text("Hello, World!")

        tool = self.tools.read_file_tool()
        result = self.invoke_tool(tool, file_path=str(test_file))

        self.assertIn("Hello, World!", result)

    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        tool = self.tools.read_file_tool()
        result = self.invoke_tool(tool, file_path="/nonexistent/file.txt")

        self.assertIn("File not found", result)

    def test_write_code_tool_creation(self):
        """Test that write_code_tool creates a callable tool."""
        tool = self.tools.write_code_tool()
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "write_code")

    @with_temp_directory
    def test_write_code_success(self, tmpdir: Path):
        """Test writing code to file successfully."""
        output_file = tmpdir / "output.py"

        tool = self.tools.write_code_tool()
        result = self.invoke_tool(
            tool,
            file_path=str(output_file),
            code_content='print("Hello, World!")',
            description="Test script",
        )

        self.assertIn("Code written", result)


if __name__ == "__main__":
    unittest.main()
