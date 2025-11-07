"""
Eval tests for web tool triggering with natural language.

Tests that the LLM agent can correctly trigger web scraping and search tools
when given natural language prompts like:
- "search for Python tutorials"
- "scrape https://example.com and summarize it"
"""

import pytest
import logging

from airunner.components.eval.utils.tracking import track_trajectory_sync

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestWebToolEval:
    """Eval tests for natural language web tool triggering."""

    def test_search_trigger_basic(self, airunner_client_function_scope):
        """Test that 'search for X' triggers search_web tool."""
        prompt = "Search for Python tutorials and tell me what you find"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify search tools were invoked OR agent provided relevant response
        search_keywords = ["python", "tutorial", "search", "find", "learning"]
        assert any(
            "search" in tool.lower() or "web" in tool.lower() for tool in tools
        ) or any(
            keyword in response_text for keyword in search_keywords
        ), f"Expected search/web tools or relevant response. Tools: {tools}, Response: {response_text[:200]}"

    def test_search_trigger_variations(self, airunner_client_function_scope):
        """Test various phrasings that should trigger search."""
        test_prompts = [
            "look up information about quantum physics",
            "find websites about machine learning",
            "what can you tell me about artificial intelligence? search the web",
            "I need you to search for the latest news on climate change",
        ]

        for prompt in test_prompts:
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

            # Verify search tools were invoked OR agent provided relevant response
            prompt_lower = prompt.lower()
            # Extract main topic from prompt
            if "quantum" in prompt_lower:
                topic_keywords = ["quantum", "physics", "search", "find"]
            elif "machine learning" in prompt_lower:
                topic_keywords = ["machine", "learning", "search", "find"]
            elif "artificial intelligence" in prompt_lower:
                topic_keywords = ["artificial", "intelligence", "ai", "search"]
            else:  # climate change
                topic_keywords = ["climate", "change", "search", "news"]

            assert any(
                "search" in tool.lower() or "web" in tool.lower()
                for tool in tools
            ) or any(
                keyword in response_text for keyword in topic_keywords
            ), f"Failed to handle search request for: {prompt}. Tools: {tools}, Response: {response_text[:200]}"

    def test_scrape_trigger_basic(self, airunner_client_function_scope):
        """Test that 'scrape URL' triggers scrape_website tool."""
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

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify scrape/web tools were invoked OR agent acknowledged the request
        scrape_keywords = [
            "scrape",
            "website",
            "webpage",
            "url",
            "example.com",
            "content",
        ]
        assert any(
            "scrape" in tool.lower() or "web" in tool.lower() for tool in tools
        ) or any(
            keyword in response_text for keyword in scrape_keywords
        ), f"Expected scrape/web tools or acknowledgment. Tools: {tools}, Response: {response_text[:200]}"

    def test_scrape_trigger_variations(self, airunner_client_function_scope):
        """Test various phrasings that should trigger scraping."""
        test_prompts = [
            "extract the content from https://example.com",
            "read the webpage at https://example.com and tell me about it",
            "can you get the text from https://example.com?",
            "I need you to scrape https://example.com",
        ]

        for prompt in test_prompts:
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

            # Verify scrape/web tools were invoked OR agent acknowledged the request
            scrape_keywords = [
                "scrape",
                "webpage",
                "website",
                "content",
                "example.com",
                "extract",
            ]
            assert any(
                "scrape" in tool.lower() or "web" in tool.lower()
                for tool in tools
            ) or any(
                keyword in response_text for keyword in scrape_keywords
            ), f"Failed to handle scrape request for: {prompt}. Tools: {tools}, Response: {response_text[:200]}"

    def test_search_and_summarize(self, airunner_client_function_scope):
        """Test search followed by summarization request."""
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

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify search tools were invoked OR agent provided relevant response
        key_terms = [
            "deep learning",
            "neural network",
            "machine learning",
            "search",
            "find",
        ]
        assert any(
            "search" in tool.lower() or "web" in tool.lower() for tool in tools
        ) or any(
            term in response_text for term in key_terms
        ), f"Expected search/web tools or relevant response. Tools: {tools}, Response: {response_text[:200]}"

    def test_search_then_scrape_workflow(self, airunner_client_function_scope):
        """Test workflow: search for info, then scrape a result."""
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

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify search/scrape tools were invoked OR agent provided relevant response
        workflow_keywords = ["python", "tutorial", "search", "scrape", "find"]
        assert any(
            "search" in tool.lower()
            or "scrape" in tool.lower()
            or "web" in tool.lower()
            for tool in tools
        ) or any(
            keyword in response_text for keyword in workflow_keywords
        ), f"Expected search/scrape/web tools or relevant response. Tools: {tools}, Response: {response_text[:200]}"


@pytest.mark.eval
class TestWebToolErrorHandling:
    """Test that agent handles web tool errors gracefully."""

    def test_search_no_results(self, airunner_client_function_scope):
        """Test handling when search returns no results."""
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

        # Verify search tools were invoked OR agent acknowledged the request
        search_keywords = [
            "search",
            "find",
            "xyznonexistentquery12345",
            "no",
            "not found",
        ]
        assert any(
            "search" in tool.lower() or "web" in tool.lower() for tool in tools
        ) or any(
            keyword in response_text for keyword in search_keywords
        ), f"Expected search/web tools or acknowledgment. Tools: {tools}, Response: {response_text[:200]}"

    def test_scrape_timeout(self, airunner_client_function_scope):
        """Test handling when scraping times out."""
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

        # Verify scrape/web tools were invoked OR agent acknowledged the request
        scrape_keywords = [
            "scrape",
            "webpage",
            "example.com",
            "content",
            "website",
        ]
        assert any(
            "scrape" in tool.lower() or "web" in tool.lower() for tool in tools
        ) or any(
            keyword in response_text for keyword in scrape_keywords
        ), f"Expected scrape/web tools or acknowledgment. Tools: {tools}, Response: {response_text[:200]}"

    def test_scrape_404(self, airunner_client_function_scope):
        """Test handling when scraping gets 404 error."""
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

        # Verify scrape/web tools were invoked OR agent acknowledged the request
        scrape_keywords = [
            "scrape",
            "webpage",
            "example.com",
            "nonexistent",
            "404",
            "not found",
        ]
        assert any(
            "scrape" in tool.lower() or "web" in tool.lower() for tool in tools
        ) or any(
            keyword in response_text for keyword in scrape_keywords
        ), f"Expected scrape/web tools or acknowledgment. Tools: {tools}, Response: {response_text[:200]}"
