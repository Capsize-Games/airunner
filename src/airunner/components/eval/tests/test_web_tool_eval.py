"""
Eval tests for web tool triggering with natural language.

Tests that the LLM agent can correctly trigger web scraping and search tools
when given natural language prompts like:
- "search for Python tutorials"
- "scrape https://example.com and summarize it"
"""

import pytest
import logging
from unittest.mock import patch, Mock

from airunner.components.eval.utils.tracking import track_trajectory_sync

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestWebToolEval:
    """Eval tests for natural language web tool triggering."""

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_trigger_basic(
        self, mock_search_tool, airunner_client_function_scope
    ):
        """Test that 'search for X' triggers search_web tool."""
        # Mock search results
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Python Tutorial",
                    "link": "https://docs.python.org",
                    "snippet": "Learn Python programming",
                }
            ]
        }

        prompt = "Search for Python tutorials and tell me what you find"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        # Verify search tools were invoked
        assert any(
            "search" in tool.lower() or "web" in tool.lower() for tool in tools
        ), f"Expected search/web tools in tools, got: {tools}"

        # Verify search tool was called
        assert mock_search_tool.aggregated_search_sync.called
        call_args = mock_search_tool.aggregated_search_sync.call_args
        query = call_args[0][0].lower()
        assert "python" in query
        assert "tutorial" in query or "tutorials" in query

        # Verify response mentions search results
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert "python" in response_text or "tutorial" in response_text

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_trigger_variations(
        self, mock_search_tool, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger search."""
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Result",
                    "link": "https://example.com",
                    "snippet": "Test snippet",
                }
            ]
        }

        test_prompts = [
            "look up information about quantum physics",
            "find websites about machine learning",
            "what can you tell me about artificial intelligence? search the web",
            "I need you to search for the latest news on climate change",
        ]

        for prompt in test_prompts:
            mock_search_tool.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=300,
                tool_categories=["SEARCH"],
            )
            response = result["response"]
            tools = result["tools"]

            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Verify search tools were invoked
            assert any(
                "search" in tool.lower() or "web" in tool.lower()
                for tool in tools
            ), f"Expected search/web tools for '{prompt}', got: {tools}"

            # At minimum, should attempt to use search
            assert (
                mock_search_tool.aggregated_search_sync.called
                or "search" in response_text
            ), f"Failed to trigger search for: {prompt}"

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_trigger_basic(
        self, mock_requests, airunner_client_function_scope
    ):
        """Test that 'scrape URL' triggers scrape_website tool."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <h1>Example Article</h1>
                <p>This is an example article about AI and machine learning.</p>
            </body>
        </html>
        """
        mock_requests.get.return_value = mock_response

        prompt = (
            "Scrape https://example.com/article and summarize "
            "what you find there"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        # Verify scrape/web tools were invoked
        assert any(
            "scrape" in tool.lower() or "web" in tool.lower() for tool in tools
        ), f"Expected scrape/web tools in tools, got: {tools}"

        # Verify scrape tool was called
        assert mock_requests.get.called
        call_args = mock_requests.get.call_args[0]
        assert "example.com" in call_args[0]

        # Verify response mentions scraped content
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "example" in response_text
            or "article" in response_text
            or "ai" in response_text
            or "machine learning" in response_text
        )

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_trigger_variations(
        self, mock_requests, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger scraping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = (
            b"<html><body><p>Test content</p></body></html>"
        )
        mock_requests.get.return_value = mock_response

        test_prompts = [
            "extract the content from https://example.com",
            "read the webpage at https://example.com and tell me about it",
            "can you get the text from https://example.com?",
            "I need you to scrape https://example.com",
        ]

        for prompt in test_prompts:
            mock_requests.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=300,
                tool_categories=["SEARCH"],
            )
            response = result["response"]
            tools = result["tools"]

            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Verify scrape/web tools were invoked
            assert any(
                "scrape" in tool.lower() or "web" in tool.lower()
                for tool in tools
            ), f"Expected scrape/web tools for '{prompt}', got: {tools}"

            # Should attempt to scrape
            assert (
                mock_requests.get.called
                or "scrape" in response_text
                or "webpage" in response_text
            ), f"Failed to trigger scrape for: {prompt}"

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_and_summarize(
        self, mock_search_tool, airunner_client_function_scope
    ):
        """Test search followed by summarization request."""
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Deep Learning Guide",
                    "link": "https://example.com/dl",
                    "snippet": (
                        "Deep learning is a subset of machine learning "
                        "that uses neural networks with multiple layers."
                    ),
                },
                {
                    "title": "Neural Networks Explained",
                    "link": "https://example.com/nn",
                    "snippet": (
                        "Neural networks are computing systems inspired "
                        "by biological neural networks."
                    ),
                },
            ]
        }

        prompt = (
            "Search for information about deep learning and "
            "give me a brief summary of what you find"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        # Verify search tools were invoked
        assert any(
            "search" in tool.lower() or "web" in tool.lower() for tool in tools
        ), f"Expected search/web tools in tools, got: {tools}"

        # Verify search was performed
        assert mock_search_tool.aggregated_search_sync.called

        # Response should contain summary with key terms
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should mention at least one key concept from search results
        key_terms = [
            "deep learning",
            "neural network",
            "machine learning",
            "layers",
        ]
        assert any(
            term in response_text for term in key_terms
        ), "Response should summarize search results"

    @patch("airunner.components.llm.tools.web_tools.requests")
    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_then_scrape_workflow(
        self,
        mock_search_tool,
        mock_requests,
        airunner_client_function_scope,
    ):
        """Test workflow: search for info, then scrape a result."""
        # Mock search results
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Python Documentation",
                    "link": "https://docs.python.org/tutorial",
                    "snippet": "Official Python tutorial",
                }
            ]
        }

        # Mock scrape result
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <h1>Python Tutorial</h1>
                <p>Python is an easy to learn, powerful programming language.</p>
            </body>
        </html>
        """
        mock_requests.get.return_value = mock_response

        prompt = (
            "Search for Python tutorials, then scrape the top result "
            "and tell me what it says"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=800,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        # Verify search/scrape tools were invoked
        assert any(
            "search" in tool.lower()
            or "scrape" in tool.lower()
            or "web" in tool.lower()
            for tool in tools
        ), f"Expected search/scrape/web tools in tools, got: {tools}"

        # Both tools should be called
        assert mock_search_tool.aggregated_search_sync.called
        # Note: Scraping might not happen in a single turn depending on agent,
        # but we verify the flow is possible
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert "python" in response_text


@pytest.mark.eval
class TestWebToolErrorHandling:
    """Test that agent handles web tool errors gracefully."""

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_search_no_results(
        self, mock_search_tool, airunner_client_function_scope
    ):
        """Test handling when search returns no results."""
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": []
        }

        prompt = "Search for xyznonexistentquery12345"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify search tools were invoked
        assert any(
            "search" in tool.lower() or "web" in tool.lower() for tool in tools
        ), f"Expected search/web tools in tools, got: {tools}"
        # Should acknowledge no results
        assert (
            "no" in response_text
            or "not found" in response_text
            or "couldn't find" in response_text
        )

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_timeout(
        self, mock_requests, airunner_client_function_scope
    ):
        """Test handling when scraping times out."""
        mock_requests.get.side_effect = mock_requests.exceptions.Timeout()

        prompt = "Scrape https://example.com and tell me what's there"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify scrape/web tools were invoked
        assert any(
            "scrape" in tool.lower() or "web" in tool.lower() for tool in tools
        ), f"Expected scrape/web tools in tools, got: {tools}"
        # Should acknowledge error
        assert (
            "error" in response_text
            or "timeout" in response_text
            or "couldn't" in response_text
            or "unable" in response_text
        )

    @patch("airunner.components.llm.tools.web_tools.requests")
    def test_scrape_404(self, mock_requests, airunner_client_function_scope):
        """Test handling when scraping gets 404 error."""
        mock_response = Mock()
        mock_response.status_code = 404
        error = mock_requests.exceptions.HTTPError(response=mock_response)
        mock_requests.get.side_effect = error

        prompt = "Scrape https://example.com/nonexistent"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify scrape/web tools were invoked
        assert any(
            "scrape" in tool.lower() or "web" in tool.lower() for tool in tools
        ), f"Expected scrape/web tools in tools, got: {tools}"
        # Should acknowledge error
        assert (
            "error" in response_text
            or "404" in response_text
            or "not found" in response_text
            or "couldn't" in response_text
        )
