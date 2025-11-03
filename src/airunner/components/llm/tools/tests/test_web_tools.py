"""Unit tests for web tools (search_web and scrape_website)."""

from unittest.mock import Mock, patch
from airunner.components.llm.tools.web_tools import search_web, scrape_website


class TestSearchWeb:
    """Tests for search_web tool."""

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
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

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_web_no_results(self, mock_search_tool):
        """Test web search with no results."""
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": []
        }

        result = search_web("nonexistent query")

        assert "No search results available" in result

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_web_missing_duckduckgo_key(self, mock_search_tool):
        """Test web search with missing duckduckgo key in results."""
        mock_search_tool.aggregated_search_sync.return_value = {"other": []}

        result = search_web("test query")

        assert "No search results available" in result

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_web_exception(self, mock_search_tool):
        """Test web search with exception."""
        mock_search_tool.aggregated_search_sync.side_effect = Exception(
            "API Error"
        )

        result = search_web("test query")

        assert "Error searching web" in result
        assert "API Error" in result

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
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

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
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

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_success(self, mock_requests):
        """Test successful website scraping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <h1>Test Page</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """
        mock_requests.get.return_value = mock_response

        result = scrape_website("https://example.com")

        assert "Test Page" in result
        assert "This is test content" in result
        mock_requests.get.assert_called_once()

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_with_selector(self, mock_requests):
        """Test scraping with CSS selector."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <div class="content">Target content</div>
                <div class="other">Other content</div>
            </body>
        </html>
        """
        mock_requests.get.return_value = mock_response

        result = scrape_website("https://example.com", selector=".content")

        assert "Target content" in result
        assert "Other content" not in result

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_removes_scripts(self, mock_requests):
        """Test that scripts and styles are removed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <head>
                <script>console.log('test');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <p>Actual content</p>
            </body>
        </html>
        """
        mock_requests.get.return_value = mock_response

        result = scrape_website("https://example.com")

        assert "Actual content" in result
        assert "console.log" not in result
        assert "color: red" not in result

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_timeout(self, mock_requests):
        """Test handling of request timeout."""
        mock_requests.get.side_effect = mock_requests.exceptions.Timeout()

        result = scrape_website("https://example.com")

        assert "Error: Request timed out" in result

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_connection_error(self, mock_requests):
        """Test handling of connection error."""
        mock_requests.get.side_effect = (
            mock_requests.exceptions.ConnectionError()
        )

        result = scrape_website("https://example.com")

        assert "Error: Could not connect" in result

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_http_error(self, mock_requests):
        """Test handling of HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        error = mock_requests.exceptions.HTTPError(response=mock_response)
        mock_requests.get.side_effect = error

        result = scrape_website("https://example.com")

        assert "Error: HTTP 404" in result

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_invalid_selector(self, mock_requests):
        """Test handling of non-matching CSS selector."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html><body><p>Content</p></body></html>
        """
        mock_requests.get.return_value = mock_response

        result = scrape_website("https://example.com", selector=".nonexistent")

        assert "No elements found matching selector" in result

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_truncates_long_content(self, mock_requests):
        """Test that very long content is truncated."""
        long_content = "A" * 10000
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = f"""
        <html><body><p>{long_content}</p></body></html>
        """.encode()
        mock_requests.get.return_value = mock_response

        result = scrape_website("https://example.com")

        assert "[Content truncated...]" in result
        assert len(result) < 6000  # Should be around 5000 + message

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_uses_browser_headers(self, mock_requests):
        """Test that browser-like headers are sent."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Test</body></html>"
        mock_requests.get.return_value = mock_response

        scrape_website("https://example.com")

        call_kwargs = mock_requests.get.call_args[1]
        assert "User-Agent" in call_kwargs["headers"]
        assert "Mozilla" in call_kwargs["headers"]["User-Agent"]

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_website_has_timeout(self, mock_requests):
        """Test that requests have a timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Test</body></html>"
        mock_requests.get.return_value = mock_response

        scrape_website("https://example.com")

        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["timeout"] == 10
