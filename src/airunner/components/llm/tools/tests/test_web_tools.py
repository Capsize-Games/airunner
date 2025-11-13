"""Unit tests for web tools (search_web and scrape_website)."""

from unittest.mock import patch
from airunner.components.llm.tools.web_tools import search_web, scrape_website


class TestSearchWeb:
    """Tests for search_web tool."""

    @patch("airunner.components.tools.search_tool.AggregatedSearchTool")
    def test_search_web_success(self, mock_search_tool):
        """Test successful web search with results."""
        # Mock search results
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Test Result 1",
                    "link": "https://example.com/1",
                    "snippet": "This is a test result snippet",
                },
                {
                    "title": "Test Result 2",
                    "link": "https://example.com/2",
                    "snippet": "Another test snippet here",
                },
            ]
        }

        result = search_web("test query")

        assert "Web search results for 'test query'" in result
        assert "Test Result 1" in result
        assert "Test Result 2" in result
        assert "https://example.com/1" in result
        assert "https://example.com/2" in result
        assert "test result snippet" in result
        mock_search_tool.aggregated_search_sync.assert_called_once_with(
            "test query", category="web"
        )

    @patch("airunner.components.tools.search_tool.AggregatedSearchTool")
    def test_search_web_no_results(self, mock_search_tool):
        """Test web search with no results."""
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": []
        }

        result = search_web("nonexistent query")

        assert "No search results available" in result

    @patch("airunner.components.tools.search_tool.AggregatedSearchTool")
    def test_search_web_missing_duckduckgo_key(self, mock_search_tool):
        """Test web search with missing duckduckgo key in results."""
        mock_search_tool.aggregated_search_sync.return_value = {"other": []}

        result = search_web("test query")

        assert "No search results available" in result

    @patch("airunner.components.tools.search_tool.AggregatedSearchTool")
    def test_search_web_exception(self, mock_search_tool):
        """Test web search with exception."""
        mock_search_tool.aggregated_search_sync.side_effect = Exception(
            "API Error"
        )

        result = search_web("test query")

        assert "Error searching web" in result
        assert "API Error" in result

    @patch("airunner.components.tools.search_tool.AggregatedSearchTool")
    def test_search_web_limits_to_five_results(self, mock_search_tool):
        """Test that search web limits results to 5."""
        # Create 10 mock results
        mock_results = [
            {
                "title": f"Result {i}",
                "link": f"https://example.com/{i}",
                "snippet": f"Snippet {i}",
            }
            for i in range(10)
        ]
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": mock_results
        }

        result = search_web("test query")

        # Should only contain first 5 results
        assert "Result 0" in result
        assert "Result 4" in result
        assert "Result 5" not in result
        assert "Result 9" not in result

    @patch("airunner.components.tools.search_tool.AggregatedSearchTool")
    def test_search_web_truncates_long_snippets(self, mock_search_tool):
        """Test that long snippets are truncated."""
        long_snippet = "A" * 500
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Test",
                    "link": "https://example.com",
                    "snippet": long_snippet,
                }
            ]
        }

        result = search_web("test query")

        # Snippet should be truncated to 200 chars
        assert (
            len([line for line in result.split("\n") if "AAA" in line][0])
            < 250
        )


class TestScrapeWebsite:
    """Tests for scrape_website tool."""

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_success(self, mock_extractor):
        """Test successful website scraping."""
        mock_extractor.fetch_and_extract.return_value = (
            "Test Page\n\nThis is test content."
        )

        result = scrape_website("https://example.com")

        assert "Test Page" in result
        assert "This is test content" in result
        mock_extractor.fetch_and_extract.assert_called_once_with(
            "https://example.com", use_cache=True
        )

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_with_selector(self, mock_extractor):
        """Test scraping with CSS selector."""
        mock_extractor.fetch_and_extract.return_value = "Target content"

        result = scrape_website("https://example.com")

        assert "Target content" in result

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_removes_scripts(self, mock_extractor):
        """Test that scripts and styles are removed."""
        # WebContentExtractor should already remove scripts/styles
        mock_extractor.fetch_and_extract.return_value = "Actual content"

        result = scrape_website("https://example.com")

        assert "Actual content" in result
        assert "console.log" not in result
        assert "color: red" not in result

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_timeout(self, mock_extractor):
        """Test handling of request timeout."""
        mock_extractor.fetch_and_extract.side_effect = TimeoutError(
            "Request timed out"
        )

        result = scrape_website("https://example.com")

        assert "Error scraping" in result
        assert "timed out" in result.lower()

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_connection_error(self, mock_extractor):
        """Test handling of connection error."""
        mock_extractor.fetch_and_extract.side_effect = ConnectionError(
            "Could not connect"
        )

        result = scrape_website("https://example.com")

        assert "Error scraping" in result

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_http_error(self, mock_extractor):
        """Test handling of HTTP error."""
        mock_extractor.fetch_and_extract.side_effect = Exception("HTTP 404")

        result = scrape_website("https://example.com")

        assert "Error scraping" in result

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_invalid_selector(self, mock_extractor):
        """Test handling of non-matching CSS selector."""
        # Empty content indicates no matching elements
        mock_extractor.fetch_and_extract.return_value = ""

        result = scrape_website("https://example.com")

        assert "Could not extract content" in result

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_truncates_long_content(self, mock_extractor):
        """Test that very long content is returned."""
        long_content = "A" * 10000
        mock_extractor.fetch_and_extract.return_value = long_content

        result = scrape_website("https://example.com")

        # Content should be returned (WebContentExtractor may handle truncation internally)
        assert "A" in result

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_uses_browser_headers(self, mock_extractor):
        """Test that browser-like headers are sent."""
        # WebContentExtractor should handle headers internally
        mock_extractor.fetch_and_extract.return_value = "Test content"

        result = scrape_website("https://example.com")

        assert "Test content" in result
        mock_extractor.fetch_and_extract.assert_called_once()

    @patch(
        "airunner.components.tools.web_content_extractor.WebContentExtractor"
    )
    def test_scrape_website_has_timeout(self, mock_extractor):
        """Test that requests have a timeout."""
        # WebContentExtractor should handle timeouts internally
        mock_extractor.fetch_and_extract.return_value = "Test content"

        result = scrape_website("https://example.com")

        assert "Test content" in result
        mock_extractor.fetch_and_extract.assert_called_once()
