"""Tests for RAGDocumentMixin.

Following red/green/refactor TDD pattern with comprehensive coverage.
"""

import os
import hashlib
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from airunner.components.llm.managers.agent.mixins.rag_document_mixin import (
    RAGDocumentMixin,
)


class TestableRAGDocumentMixin(RAGDocumentMixin):
    """Testable version of RAGDocumentMixin with required dependencies."""

    def __init__(self):
        self.logger = Mock()
        self._doc_metadata_cache = {}
        self._cache_validated = False


class TestGetUnindexedDocuments:
    """Test _get_unindexed_documents method."""

    def test_returns_documents_needing_indexing(self):
        """Should return documents that need indexing."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_doc1 = Mock()
            mock_doc1.path = "/test/doc1.pdf"
            mock_doc1.indexed = False
            mock_db.objects.filter.return_value = [mock_doc1]

            result = mixin._get_unindexed_documents()

            assert len(result) == 1
            assert result[0] == mock_doc1

    def test_checks_file_hash_for_indexed_documents(self):
        """Should check file hash to detect changes in indexed documents."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            with patch.object(mixin, "_calculate_file_hash") as mock_hash:
                mock_doc1 = Mock()
                mock_doc1.path = "/test/doc1.pdf"
                mock_doc1.indexed = True
                mock_doc1.file_hash = "old_hash"
                mock_db.objects.all.return_value = [mock_doc1]
                mock_hash.return_value = "new_hash"

                with patch("os.path.exists", return_value=True):
                    result = mixin._get_unindexed_documents()

                assert len(result) == 1
                assert result[0] == mock_doc1

    def test_skips_nonexistent_files(self):
        """Should skip documents where file no longer exists."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_doc1 = Mock()
            mock_doc1.path = "/test/missing.pdf"
            mock_doc1.indexed = False
            mock_db.objects.filter.return_value = [mock_doc1]

            with patch("os.path.exists", return_value=False):
                result = mixin._get_unindexed_documents()

            assert len(result) == 0

    def test_logs_file_not_found(self):
        """Should log when file is not found."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_doc1 = Mock()
            mock_doc1.path = "/test/missing.pdf"
            mock_doc1.indexed = False
            mock_db.objects.filter.return_value = [mock_doc1]

            with patch("os.path.exists", return_value=False):
                mixin._get_unindexed_documents()

            mixin.logger.warning.assert_called()


class TestGetActiveDocumentIds:
    """Test _get_active_document_ids method."""

    def test_returns_ids_of_active_documents(self):
        """Should return list of IDs for active documents."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_doc1 = Mock()
            mock_doc1.path = "/test/doc1.pdf"
            mock_doc2 = Mock()
            mock_doc2.path = "/test/doc2.pdf"
            mock_db.objects.filter.return_value = [mock_doc1, mock_doc2]

            with patch.object(mixin, "_generate_doc_id") as mock_gen_id:
                mock_gen_id.side_effect = ["id1", "id2"]

                result = mixin._get_active_document_ids()

            assert result == ["id1", "id2"]
            assert mock_gen_id.call_count == 2

    def test_filters_by_active_status(self):
        """Should filter documents by active=True."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_db.objects.filter.return_value = []

            mixin._get_active_document_ids()

            mock_db.objects.filter.assert_called_once_with(active=True)


class TestGetActiveDocumentNames:
    """Test _get_active_document_names method."""

    def test_returns_basenames_of_active_documents(self):
        """Should return list of basenames for active documents."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_doc1 = Mock()
            mock_doc1.path = "/test/path/doc1.pdf"
            mock_doc2 = Mock()
            mock_doc2.path = "/another/path/doc2.txt"
            mock_db.objects.filter.return_value = [mock_doc1, mock_doc2]

            result = mixin._get_active_document_names()

            assert result == ["doc1.pdf", "doc2.txt"]

    def test_returns_empty_list_when_no_active_documents(self):
        """Should return empty list when no active documents."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_db.objects.filter.return_value = []

            result = mixin._get_active_document_names()

            assert result == []


class TestMarkDocumentIndexed:
    """Test _mark_document_indexed method."""

    def test_updates_document_indexed_status(self):
        """Should update document's indexed flag and file hash."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            with patch.object(mixin, "_calculate_file_hash") as mock_hash:
                mock_hash.return_value = "test_hash"
                mock_doc = Mock()
                mock_db.objects.get.return_value = mock_doc

                mixin._mark_document_indexed("/test/doc.pdf")

                mock_db.objects.update.assert_called_once_with(
                    pk=mock_doc.id, indexed=True, file_hash="test_hash"
                )

    def test_logs_success(self):
        """Should log successful update."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            with patch.object(mixin, "_calculate_file_hash") as mock_hash:
                mock_hash.return_value = "test_hash"
                mock_db.objects.get.return_value = Mock()

                mixin._mark_document_indexed("/test/doc.pdf")

                mixin.logger.debug.assert_called()

    def test_handles_document_not_found(self):
        """Should handle case where document is not found in database."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.DBDocument"
        ) as mock_db:
            mock_db.objects.get.side_effect = Exception("Not found")

            mixin._mark_document_indexed("/test/missing.pdf")

            mixin.logger.error.assert_called()


class TestExtractMetadata:
    """Test _extract_metadata method."""

    def test_returns_cached_metadata_if_valid(self):
        """Should return cached metadata if cache is validated."""
        mixin = TestableRAGDocumentMixin()
        mixin._cache_validated = True
        mixin._doc_metadata_cache["/test/doc.pdf"] = {"cached": "data"}

        result = mixin._extract_metadata("/test/doc.pdf")

        assert result == {"cached": "data"}

    def test_extracts_metadata_for_pdf(self):
        """Should extract metadata from PDF file."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.PdfReader"
        ) as mock_reader:
            mock_pdf = Mock()
            mock_pdf.metadata = {"title": "Test PDF"}
            mock_reader.return_value = mock_pdf

            with patch("builtins.open", create=True):
                result = mixin._extract_metadata("/test/doc.pdf")

            assert "title" in result
            assert result["title"] == "Test PDF"

    def test_extracts_metadata_for_epub(self):
        """Should extract metadata from EPUB file."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.epub.read_epub"
        ) as mock_epub:
            mock_book = Mock()
            mock_book.get_metadata.return_value = [
                ("DC", "title", "Test EPUB")
            ]
            mock_epub.return_value = mock_book

            result = mixin._extract_metadata("/test/doc.epub")

            assert "title" in result

    def test_returns_basic_metadata_for_unsupported_format(self):
        """Should return basic metadata for unsupported file formats."""
        mixin = TestableRAGDocumentMixin()

        with patch("os.path.basename", return_value="doc.txt"):
            result = mixin._extract_metadata("/test/doc.txt")

        assert "file_name" in result
        assert result["file_name"] == "doc.txt"

    def test_caches_extracted_metadata(self):
        """Should cache extracted metadata."""
        mixin = TestableRAGDocumentMixin()

        with patch("os.path.basename", return_value="doc.txt"):
            mixin._extract_metadata("/test/doc.txt")

        assert "/test/doc.txt" in mixin._doc_metadata_cache

    def test_handles_extraction_errors(self):
        """Should handle errors during metadata extraction."""
        mixin = TestableRAGDocumentMixin()

        with patch(
            "airunner.components.llm.managers.agent.mixins.rag_document_mixin.PdfReader"
        ) as mock_reader:
            mock_reader.side_effect = Exception("Read error")

            with patch("builtins.open", create=True):
                result = mixin._extract_metadata("/test/doc.pdf")

            # Should return basic metadata
            assert "file_name" in result
            mixin.logger.debug.assert_called()


class TestCalculateFileHash:
    """Test _calculate_file_hash method."""

    def test_calculates_sha256_hash(self):
        """Should calculate SHA256 hash of file contents."""
        mixin = TestableRAGDocumentMixin()

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = (
                b"test content"
            )
            mock_open.return_value = mock_file

            result = mixin._calculate_file_hash("/test/doc.txt")

            # SHA256 of "test content"
            expected = hashlib.sha256(b"test content").hexdigest()
            assert result == expected

    def test_handles_file_not_found(self):
        """Should return None if file not found."""
        mixin = TestableRAGDocumentMixin()

        with patch("builtins.open", side_effect=FileNotFoundError()):
            result = mixin._calculate_file_hash("/test/missing.txt")

        assert result is None
        mixin.logger.error.assert_called()


class TestGenerateDocId:
    """Test _generate_doc_id method."""

    def test_generates_md5_hash_of_path(self):
        """Should generate MD5 hash of file path."""
        mixin = TestableRAGDocumentMixin()

        result = mixin._generate_doc_id("/test/doc.pdf")

        # MD5 of "/test/doc.pdf"
        expected = hashlib.md5("/test/doc.pdf".encode()).hexdigest()
        assert result == expected

    def test_same_path_produces_same_id(self):
        """Should produce consistent ID for same path."""
        mixin = TestableRAGDocumentMixin()

        id1 = mixin._generate_doc_id("/test/doc.pdf")
        id2 = mixin._generate_doc_id("/test/doc.pdf")

        assert id1 == id2

    def test_different_paths_produce_different_ids(self):
        """Should produce different IDs for different paths."""
        mixin = TestableRAGDocumentMixin()

        id1 = mixin._generate_doc_id("/test/doc1.pdf")
        id2 = mixin._generate_doc_id("/test/doc2.pdf")

        assert id1 != id2
