import unittest
import time
import os
import tempfile
from unittest.mock import patch, MagicMock

from llama_index.core import Document

from airunner.handlers.llm.agent.rag_mixin import RAGMixin


class TestRAGPerformance(unittest.TestCase):
    """Test suite for measuring and validating RAG performance improvements."""
    
    def setUp(self):
        """Set up test environment with a controlled set of documents."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a mock RAGMixin instance with necessary properties
        self.rag_mixin = MagicMock(spec=RAGMixin)
        
        # Mock basic properties needed for testing
        self.rag_mixin._extract_keywords_from_text = RAGMixin._extract_keywords_from_text
        self.rag_mixin.__keyword_cache = {}
        
        # Create test documents
        self.test_documents = [
            Document(text=f"This is a test document {i} for RAG testing with various keywords like AI, machine learning, and data science.", 
                    doc_id=f"doc_{i}")
            for i in range(10)
        ]

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_keyword_extraction_performance(self):
        """Test the performance of keyword extraction with caching."""
        # First extraction - should be slower
        start_time = time.time()
        for doc in self.test_documents:
            keywords = RAGMixin._extract_keywords_from_text(doc.text)
            self.assertIsInstance(keywords, set)
            self.assertGreater(len(keywords), 0)
        first_run_time = time.time() - start_time
        
        # Second extraction - should be faster due to caching
        start_time = time.time()
        for doc in self.test_documents:
            keywords = RAGMixin._extract_keywords_from_text(doc.text)
            self.assertIsInstance(keywords, set)
            self.assertGreater(len(keywords), 0)
        second_run_time = time.time() - start_time
        
        print(f"First run time: {first_run_time:.4f}s, Second run time: {second_run_time:.4f}s")
        # Second run should be faster due to caching
        self.assertLess(second_run_time, first_run_time)
    
    def test_extract_keywords_correctness(self):
        """Test that keyword extraction returns valid keywords."""
        text = "Artificial intelligence and machine learning are transforming industries."
        keywords = RAGMixin._extract_keywords_from_text(text)
        
        # Just verify we get some keywords back - the exact ones depend on the RAKE algorithm
        self.assertIsInstance(keywords, set)
        self.assertGreater(len(keywords), 0)
        
        # Print the keywords for debugging
        print(f"Extracted keywords: {keywords}")
        
        # Check that at least some meaningful words are extracted
        all_words = " ".join(keywords).lower()
        self.assertTrue(
            "artificial" in all_words or 
            "intelligence" in all_words or 
            "machine" in all_words or 
            "learning" in all_words or
            "transforming" in all_words or
            "industries" in all_words
        )


if __name__ == "__main__":
    unittest.main()