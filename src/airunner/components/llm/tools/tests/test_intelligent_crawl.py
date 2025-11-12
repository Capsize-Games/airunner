"""
Unit tests for intelligent_crawl tool.

Tests basic functionality of the intelligent web crawler tool,
including parameter validation and error handling.
"""

import unittest
from unittest.mock import Mock, patch

from airunner.components.llm.tools.intelligent_crawl_tool import (
    intelligent_crawl,
)


class TestIntelligentCrawlTool(unittest.TestCase):
    """Test intelligent_crawl tool basic functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_api = Mock()
        self.mock_api.llm = Mock()
        self.mock_api.llm.send_request = Mock()

    def test_no_api_provided(self):
        """Test error handling when API is not provided."""
        result = intelligent_crawl(
            start_url="https://example.com",
            research_goal="Test research goal",
            api=None,
        )

        # Should return error message
        self.assertIn("Error", result)
        self.assertIn("API not available", result)

    def test_parameter_clamping_max_pages(self):
        """Test that max_pages is clamped to valid range."""
        with patch(
            "airunner.components.llm.tools.intelligent_crawl_tool.CrawlerProcess"
        ) as mock_crawler:
            mock_process = Mock()
            mock_crawler.return_value = mock_process

            # Test value too high - should be clamped
            result = intelligent_crawl(
                start_url="https://example.com",
                research_goal="Test",
                max_pages=100,  # Should be clamped to 20
                api=self.mock_api,
            )

            # Should still work (not crash)
            self.assertIsInstance(result, str)

            # Test value too low - should be clamped
            result = intelligent_crawl(
                start_url="https://example.com",
                research_goal="Test",
                max_pages=0,  # Should be clamped to 1
                api=self.mock_api,
            )

            # Should still work (not crash)
            self.assertIsInstance(result, str)

    def test_parameter_clamping_max_depth(self):
        """Test that max_depth is clamped to valid range."""
        with patch(
            "airunner.components.llm.tools.intelligent_crawl_tool.CrawlerProcess"
        ) as mock_crawler:
            mock_process = Mock()
            mock_crawler.return_value = mock_process

            # Test value too high - should be clamped
            result = intelligent_crawl(
                start_url="https://example.com",
                research_goal="Test",
                max_depth=10,  # Should be clamped to 3
                api=self.mock_api,
            )

            # Should still work (not crash)
            self.assertIsInstance(result, str)

            # Test value too low - should be clamped
            result = intelligent_crawl(
                start_url="https://example.com",
                research_goal="Test",
                max_depth=0,  # Should be clamped to 1
                api=self.mock_api,
            )

            # Should still work (not crash)
            self.assertIsInstance(result, str)

    @patch(
        "airunner.components.llm.tools.intelligent_crawl_tool.CrawlerProcess"
    )
    def test_crawler_process_created(self, mock_crawler_process):
        """Test that crawler process is created."""
        mock_process = Mock()
        mock_crawler_process.return_value = mock_process

        result = intelligent_crawl(
            start_url="https://example.com",
            research_goal="Test research",
            max_pages=5,
            max_depth=2,
            api=self.mock_api,
        )

        # Verify CrawlerProcess was created
        mock_crawler_process.assert_called_once()

        # Verify process was started
        mock_process.start.assert_called_once()

        # Result should be a string
        self.assertIsInstance(result, str)

    @patch(
        "airunner.components.llm.tools.intelligent_crawl_tool.CrawlerProcess"
    )
    def test_returns_string_result(self, mock_crawler_process):
        """Test that function returns a string result."""
        mock_process = Mock()
        mock_crawler_process.return_value = mock_process

        result = intelligent_crawl(
            start_url="https://example.com",
            research_goal="Test research",
            api=self.mock_api,
        )

        # Result should be a string
        self.assertIsInstance(result, str)

    @patch(
        "airunner.components.llm.tools.intelligent_crawl_tool.CrawlerProcess"
    )
    def test_crawler_exception_handling(self, mock_crawler_process):
        """Test that exceptions during crawling are handled gracefully."""
        # Make CrawlerProcess raise an exception
        mock_crawler_process.side_effect = Exception("Crawler error")

        result = intelligent_crawl(
            start_url="https://example.com",
            research_goal="Test research",
            api=self.mock_api,
        )

        # Should return error message, not raise exception
        self.assertIsInstance(result, str)
        self.assertIn("Error", result)


if __name__ == "__main__":
    unittest.main()
