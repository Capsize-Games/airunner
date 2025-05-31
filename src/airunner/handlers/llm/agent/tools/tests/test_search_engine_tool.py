"""
Functional test for SearchEngineTool with web content extraction pipeline.
"""

import pytest
from unittest.mock import MagicMock
from airunner.handlers.llm.agent.tools.search_engine_tool import (
    SearchEngineTool,
)
from llama_index.core.tools.types import ToolMetadata


class DummyLLM:
    def __init__(self):
        self.llm_request = None

        class Meta:
            context_window = 2048
            system_role = "system"

        self.metadata = Meta()

    def stream_chat(self, prompt, chat_history=None):
        class DummyMsg:
            def __init__(self, text):
                self.message = self
                self.text = text
                self.additional_kwargs = {}
                self.delta = None

            def __str__(self):
                return self.text

            def __add__(self, other):
                return self.text + (str(other) if other is not None else "")

        class Resp:
            def __iter__(self):
                return iter([DummyMsg("Test response.")])

            @property
            def response_gen(self):
                # Simulate streaming by yielding one token at a time
                for token in ["Test ", "response."]:
                    yield DummyMsg(token)

        return Resp()


def test_search_engine_tool_web_content(monkeypatch):
    # Patch AggregatedSearchTool to return fake search results
    from airunner.tools import search_tool

    monkeypatch.setattr(
        search_tool.AggregatedSearchTool,
        "aggregated_search_sync",
        lambda query, category="all": {
            "web": [
                {
                    "title": "Example",
                    "link": "https://www.example.com/",
                    "snippet": "Example snippet.",
                },
                {
                    "title": "Wikipedia",
                    "link": "https://www.wikipedia.org/",
                    "snippet": "Wiki snippet.",
                },
            ]
        },
    )
    tool = SearchEngineTool(
        agent=MagicMock(),
        llm=DummyLLM(),
        metadata=ToolMetadata(
            name="search_engine_tool", description="", return_direct=True
        ),
    )
    result = tool.call(input="test query", top_n=2)
    assert "Test response." in result.content
