"""Unit tests for NodeFunctionsMixin RAG/search routing."""

from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)


class _DummyNodeFunctions(NodeFunctionsMixin):
    def __init__(self):
        self.logger = Mock()

    def _should_return_tool_direct(self, tool_name: str) -> bool:
        return False


class _CapturingNodeFunctions(_DummyNodeFunctions):
    def __init__(self):
        super().__init__()
        self._chat_model = SimpleNamespace(tool_calling_mode="json")
        self.captured = None

    def _generate_forced_response_message(
        self,
        tool_content,
        tool_name,
        user_question,
        generation_kwargs=None,
        message_history=None,
    ):
        self.captured = (tool_content, tool_name, user_question)
        return AIMessage(content="forced response", tool_calls=[])


class _NoModelNodeFunctions(_DummyNodeFunctions):
    def __init__(self):
        super().__init__()
        self._chat_model = SimpleNamespace(tool_calling_mode="json")
        self._token_callback = Mock()
        self.stream_internal_calls = 0

    def _stream_internal_response(self, *_args, **_kwargs):
        self.stream_internal_calls += 1
        raise AssertionError("model synthesis should not run")


class _CapturingCallModelNodeFunctions(_DummyNodeFunctions):
    def __init__(self):
        super().__init__()
        self._chat_model = SimpleNamespace(
            tool_calling_mode="json",
            tools=["rag_search"],
            tool_choice={"function": {"name": "rag_search"}},
        )
        self._tools = ["rag_search"]
        self.captured = None

    def _trim_messages(self, messages):
        return messages

    def _build_prompt(self, trimmed_messages):
        return trimmed_messages

    def _generate_response(self, prompt, generation_kwargs):
        self.captured = {
            "prompt": prompt,
            "generation_kwargs": generation_kwargs,
            "chat_model_tools": self._chat_model.tools,
            "bound_tools": list(self._tools),
            "tool_choice": self._chat_model.tool_choice,
        }
        return AIMessage(content="model response", tool_calls=[])


class _VerificationFallbackNodeFunctions(_DummyNodeFunctions):
    def __init__(self):
        super().__init__()
        self._chat_model = SimpleNamespace(tool_calling_mode="json")
        self._streamed_messages = [
            AIMessage(
                content=(
                    "Miss Marple looks into a resort murder after a doctor "
                    "realizes he once recognized a killer from a snapshot."
                ),
                tool_calls=[],
            ),
            AIMessage(
                content=(
                    '"Focus on the murder mystery, the telling of the '
                    "story, the setting (clubs), and the specific detail "
                    'about the snapshot." '
                    "(This looks like an instruction "
                    "or a note rather than a full answer, but I need to "
                    "treat it as the starting point to be verified against "
                    "search results)."
                ),
                tool_calls=[],
            ),
        ]

    def _stream_internal_response(self, *_args, **_kwargs):
        return self._streamed_messages.pop(0)


class _DocumentFollowupPromptNodeFunctions(_DummyNodeFunctions):
    def __init__(self):
        super().__init__()
        self._system_prompt = "planner prompt"
        self.prompt_updates = []
        self.prompt_built_with = None
        self.prompt_seen = None

    def update_system_prompt(self, system_prompt):
        self.prompt_updates.append(system_prompt)
        self._system_prompt = system_prompt

    def get_system_prompt_with_context(
        self,
        action,
        tool_categories=None,
        force_tool=None,
    ):
        assert action == LLMActionType.CHAT
        assert tool_categories is None
        assert force_tool is None
        return "final conversational prompt"

    def _build_prompt(self, trimmed_messages):
        self.prompt_built_with = self._system_prompt
        return trimmed_messages

    def _stream_model_response(
        self,
        prompt,
        generation_kwargs=None,
        thinking_metadata=None,
    ):
        self.prompt_seen = self._system_prompt
        return AIMessage(content="Conversational reply", tool_calls=[])

    def _recover_forced_response_content(
        self,
        response_message,
        reject_structure_only=False,
    ):
        return response_message.content

    def _looks_like_instruction_reflection(self, visible_content):
        return False


class _CallModelDocumentFollowupNodeFunctions(_DummyNodeFunctions):
    def __init__(self):
        super().__init__()
        self._system_prompt = "planner prompt"
        self.prompt_updates = []
        self.prompt_built_with = None
        self.prompt_seen = None
        self._chat_model = SimpleNamespace(
            tool_calling_mode="json",
            tools=["analyze_loaded_document"],
            tool_choice={
                "function": {"name": "analyze_loaded_document"}
            },
        )
        self._tools = ["analyze_loaded_document"]

    def update_system_prompt(self, system_prompt):
        self.prompt_updates.append(system_prompt)
        self._system_prompt = system_prompt

    def _trim_messages(self, messages):
        return messages

    def _build_prompt(self, trimmed_messages):
        self.prompt_built_with = self._system_prompt
        return trimmed_messages

    def _generate_response(self, prompt, generation_kwargs):
        self.prompt_seen = self._system_prompt
        return AIMessage(content="Conversational reply", tool_calls=[])


def test_route_after_tools_returns_model_for_rag_search():
    """RAG search results should return to the model for a streamed answer."""
    mixin = _DummyNodeFunctions()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "document summary"},
                    }
                ],
            ),
            ToolMessage(
                content="Found 1 relevant chunk.",
                tool_call_id="tool-1",
                name="rag_search",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "model"


def test_route_after_tools_returns_model_for_synthesized_document_rag_route():
    """Synthesized document answers should return to the model node."""
    mixin = _DummyNodeFunctions()
    mixin._current_document_query_route = SimpleNamespace(
        intent="summary",
        force_tool="rag_search",
        answer_mode="synthesized",
    )
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "summarize this document"},
                    }
                ],
            ),
            ToolMessage(
                content="Found 1 relevant chunk.",
                tool_call_id="tool-1",
                name="rag_search",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "model"


def test_route_after_tools_returns_model_for_document_analysis_route():
    """Whole-document analysis should stay in the synthesized document path."""
    mixin = _DummyNodeFunctions()
    mixin.llm_request = SimpleNamespace(document_answer_mode="synthesized")
    mixin._current_document_query_route = SimpleNamespace(
        intent="summary",
        force_tool="rag_search",
        answer_mode="synthesized",
    )
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "analyze_loaded_document",
                        "args": {"query": "summarize this document"},
                    }
                ],
            ),
            ToolMessage(
                content="Current document analysis:\n\nAnalysis mode: chunked_document",
                tool_call_id="tool-1",
                name="analyze_loaded_document",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "model"


def test_route_after_tools_forces_response_for_inspection_tool():
    """Inspection results should bypass another model planning turn."""
    mixin = _DummyNodeFunctions()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "inspect_loaded_documents",
                        "args": {},
                    }
                ],
            ),
            ToolMessage(
                content="Loaded documents:\nDocument 1: Example.pdf",
                tool_call_id="tool-1",
                name="inspect_loaded_documents",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "force_response"


def test_route_after_tools_keeps_search_web_in_model_loop():
    """Deep-research web search should still allow further tool use."""
    mixin = _DummyNodeFunctions()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "search_web",
                        "args": {"query": "latest updates"},
                    }
                ],
            ),
            ToolMessage(
                content="Search results here.",
                tool_call_id="tool-1",
                name="search_web",
            ),
        ]
    }

    assert mixin._route_after_tools(state) == "model"


def test_route_after_model_forces_response_for_duplicate_tool_call():
    """Duplicate tool calls in one turn should force a synthesized reply."""
    mixin = _DummyNodeFunctions()
    state = {
        "messages": [
            HumanMessage(content="search for updates"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "search_web",
                        "args": {"query": "latest updates"},
                    }
                ],
            ),
            ToolMessage(
                content="Search results here.",
                tool_call_id="tool-1",
                name="search_web",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-2",
                        "name": "search_web",
                        "args": {"query": "latest updates"},
                    }
                ],
            ),
        ]
    }

    assert mixin._route_after_model(state) == "force_response"


def test_call_model_disables_tools_for_synthesized_document_followup():
    """Synthesized document follow-ups should answer without another tool call."""
    mixin = _CapturingCallModelNodeFunctions()
    mixin.llm_request = SimpleNamespace(document_answer_mode="synthesized")
    state = {
        "messages": [
            HumanMessage(content="what is this book about?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "what is this book about?"},
                    }
                ],
            ),
            ToolMessage(
                content="Found 1 relevant chunk.",
                tool_call_id="tool-1",
                name="rag_search",
            ),
        ],
        "generation_kwargs": {"temperature": 0.3},
    }

    result = mixin._call_model(state)

    assert result["messages"][0].content == "model response"
    assert mixin.captured == {
        "prompt": state["messages"],
        "generation_kwargs": {"temperature": 0.3},
        "chat_model_tools": None,
        "bound_tools": [],
        "tool_choice": None,
    }
    assert mixin._chat_model.tools == ["rag_search"]
    assert mixin._chat_model.tool_choice == {
        "function": {"name": "rag_search"}
    }
    assert mixin._tools == ["rag_search"]


def test_force_response_node_uses_only_current_turn_tool_results():
    """Force synthesis should ignore older tool messages from prior turns."""
    mixin = _CapturingNodeFunctions()
    state = {
        "messages": [
            HumanMessage(content="what document is this?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "what document is this?"},
                    }
                ],
            ),
            ToolMessage(
                content="Matched documents:\nDocument 1: Old.pdf",
                tool_call_id="tool-1",
                name="rag_search",
            ),
            AIMessage(content="Old answer", tool_calls=[]),
            HumanMessage(content="what chapters are in it?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-2",
                        "name": "rag_search",
                        "args": {"query": "what chapters are in it?"},
                    }
                ],
            ),
            ToolMessage(
                content="Document structure:\n1. INTRODUCTION",
                tool_call_id="tool-2",
                name="rag_search",
            ),
        ],
        "generation_kwargs": {},
    }

    result = mixin._force_response_node(state)

    assert result["messages"][0].content == "forced response"
    tool_content, tool_name, user_question = mixin.captured
    assert "Old.pdf" not in tool_content
    assert "Document structure:" in tool_content
    assert tool_name == "rag_search"
    assert user_question == "what chapters are in it?"


def test_post_tool_instructions_ignore_previous_turn_tool_results():
    """Fresh user turns should not inherit stale tool-result guidance."""
    mixin = _DummyNodeFunctions()
    mixin._chat_model = SimpleNamespace(tool_calling_mode="json")

    prompt = mixin._add_post_tool_instructions(
        "Base prompt",
        [
            HumanMessage(content="what document is this?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "what document is this?"},
                    }
                ],
            ),
            ToolMessage(
                content="Matched documents:\nDocument 1: Old.pdf",
                tool_call_id="tool-1",
                name="rag_search",
            ),
            AIMessage(content="Old answer", tool_calls=[]),
            HumanMessage(content="what chapters are in it?"),
        ],
    )

    assert prompt == "Base prompt"


def test_post_tool_instructions_keep_current_turn_research_state():
    """Research-mode post-tool instructions should still inspect current turn data."""
    mixin = _DummyNodeFunctions()
    mixin._chat_model = SimpleNamespace(tool_calling_mode="react")
    mixin._force_tool = "search_web"

    prompt = mixin._add_post_tool_instructions(
        "Base prompt",
        [
            HumanMessage(content="research the latest updates"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "search_web",
                        "args": {"query": "latest updates"},
                    }
                ],
            ),
            ToolMessage(
                content="Search results:\nhttps://example.com/article",
                tool_call_id="tool-1",
                name="search_web",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-2",
                        "name": "scrape_website",
                        "args": {"url": "https://example.com/article"},
                    }
                ],
            ),
            ToolMessage(
                content="A" * 250,
                tool_call_id="tool-2",
                name="scrape_website",
            ),
        ],
    )

    assert "EXPAND SOURCE COVERAGE" in prompt


def test_post_tool_instructions_specialize_rag_structure_answers():
    """RAG structure answers should avoid another tool pass and metadata chatter."""
    mixin = _DummyNodeFunctions()
    mixin._chat_model = SimpleNamespace(tool_calling_mode="json")

    prompt = mixin._add_post_tool_instructions(
        "Base prompt",
        [
            HumanMessage(content="what chapters are in it?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "what chapters are in it?"},
                    }
                ],
            ),
            ToolMessage(
                content="Document structure:\n1. INTRODUCTION",
                tool_call_id="tool-1",
                name="rag_search",
            ),
        ],
    )

    assert "section names only" in prompt
    assert "Do NOT call another tool" in prompt
    assert "Do NOT discuss your reasoning" in prompt


def test_post_tool_instructions_specialize_rag_summary_answers():
    """Summary answers should avoid genre and series hallucinations."""
    mixin = _DummyNodeFunctions()
    mixin._chat_model = SimpleNamespace(tool_calling_mode="json")

    prompt = mixin._add_post_tool_instructions(
        "Base prompt",
        [
            HumanMessage(content="what is this book about?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "rag_search",
                        "args": {"query": "what is this book about?"},
                    }
                ],
            ),
            ToolMessage(
                content="Opening context. Haunted Hollywood studio mystery.",
                tool_call_id="tool-1",
                name="rag_search",
            ),
        ],
    )

    assert "Do NOT infer a genre, series, trilogy, collection, or bibliography" in prompt
    assert "Treat uncanny or dreamlike atmosphere as mood" in prompt
    assert "Do NOT attribute quoted criticism, accusations, or stray dialogue" in prompt
    assert "Do NOT call another tool" in prompt


def test_build_search_results_prompt_uses_document_route_for_inspection():
    """Forced synthesis should honor the request-scoped inspection intent."""
    mixin = _DummyNodeFunctions()
    mixin._current_document_query_route = SimpleNamespace(
        intent="identity",
        force_tool="inspect_loaded_documents",
    )

    prompt = mixin._build_search_results_prompt(
        "Loaded documents:\nDocument 1: Example.pdf",
        "inspect_loaded_documents",
        "what is this document?",
    )

    assert "answer directly and briefly" in prompt
    assert "Do not mention search results or instructions" in prompt


def test_build_search_results_prompt_uses_premise_guidance_for_book_about():
    """Book-about questions should emphasize premise over stray scenes."""
    mixin = _DummyNodeFunctions()
    mixin._current_document_query_route = SimpleNamespace(
        intent="summary",
        force_tool="rag_search",
    )

    prompt = mixin._build_search_results_prompt(
        "Evidence excerpts:\nOpening context. Haunted Hollywood studio.",
        "rag_search",
        "what is this book about?",
    )

    assert "lead with the premise, setting, central conflict" in prompt
    assert "Treat isolated later scenes" in prompt
    assert "Prefer the inciting incident, victim, investigator, and case setup" in prompt
    assert "Do not infer genre, series, trilogy, collection" in prompt
    assert "prefer a grounded mystery or noir framing" in prompt
    assert "Do not describe literal resurrection" in prompt
    assert "Do not attribute criticism, accusations, or quoted dialogue" in prompt
    assert "currently loaded document" in prompt
    assert "do not ask which book, story, or document they mean" in prompt.lower()


def test_build_search_results_prompt_treats_document_analysis_as_document_tool():
    """Whole-document analysis should receive document-summary guidance."""
    mixin = _DummyNodeFunctions()
    mixin._current_document_query_route = SimpleNamespace(
        intent="summary",
        force_tool="rag_search",
    )

    prompt = mixin._build_search_results_prompt(
        "Current document analysis:\n\nAnalysis mode: full_document",
        "analyze_loaded_document",
        "what is this book about?",
    )

    assert "answering a question about a currently loaded document" in prompt
    assert "lead with the premise, setting, central conflict" in prompt


def test_build_search_results_prompt_specializes_compare_document_tasks():
    """Comparison requests should receive comparison-specific guidance."""
    mixin = _DummyNodeFunctions()
    mixin._current_document_query_route = SimpleNamespace(
        intent="compare",
        force_tool="rag_search",
    )

    prompt = mixin._build_search_results_prompt(
        "Evidence excerpts:\nResult set A. Result set B.",
        "rag_search",
        "compare the two result sections in this document",
    )

    assert "asking for a comparison" in prompt
    assert "similarities" in prompt
    assert "differences" in prompt


def test_build_search_results_prompt_specializes_transform_document_tasks():
    """Formatting requests should receive structure-aware guidance."""
    mixin = _DummyNodeFunctions()
    mixin._current_document_query_route = SimpleNamespace(
        intent="transform",
        force_tool="rag_search",
    )

    prompt = mixin._build_search_results_prompt(
        "Evidence excerpts:\nVitals and lab values.",
        "rag_search",
        "summarize the results in a table",
    )

    assert "organize or reformat" in prompt
    assert "follow the requested structure" in prompt


def test_get_document_query_intent_detects_transform_tasks_from_text():
    """Fallback intent routing should detect new transform-style tasks."""
    mixin = _DummyNodeFunctions()

    assert mixin._get_document_query_intent(
        "summarize the lab results in a table"
    ) == "transform"


def test_generate_response_message_uses_deterministic_structure_answer():
    """Structure answers should not invoke model synthesis."""
    mixin = _NoModelNodeFunctions()
    mixin.llm_request = SimpleNamespace(
        document_query_intent="structure",
        document_primary_tool="inspect_loaded_documents",
        document_answer_mode="deterministic",
    )

    response = mixin._generate_response_message_from_results(
        "Document structure:\n1. INTRODUCTION\n2. PROLOGUE",
        "inspect_loaded_documents",
        "what chapters are in it?",
    )

    assert response is not None
    assert response.content == "INTRODUCTION\nPROLOGUE"
    assert mixin.stream_internal_calls == 0
    mixin._token_callback.assert_called_once_with("INTRODUCTION\nPROLOGUE")


def test_generate_response_message_uses_deterministic_identity_answer():
    """Identity answers should not invoke model synthesis."""
    mixin = _NoModelNodeFunctions()
    mixin.llm_request = SimpleNamespace(
        document_query_intent="identity",
        document_primary_tool="inspect_loaded_documents",
        document_answer_mode="deterministic",
    )

    response = mixin._generate_response_message_from_results(
        "Loaded documents:\n\nDocument 1: The Satanic Bible - Anton LaVey.pdf\n"
        "Inferred title from filename: The Satanic Bible\n"
        "Inferred author from filename: Anton LaVey\n"
        "File type: .pdf",
        "inspect_loaded_documents",
        "what is this document?",
    )

    assert response is not None
    assert response.content == (
        "This document is a PDF document titled 'The Satanic Bible' by Anton LaVey."
    )
    assert mixin.stream_internal_calls == 0


def test_get_document_query_intent_prefers_request_metadata():
    """Request-scoped metadata should override manager-cached document intent."""
    mixin = _DummyNodeFunctions()
    mixin.llm_request = SimpleNamespace(document_query_intent="structure")
    mixin._current_document_query_route = SimpleNamespace(intent="identity")

    assert mixin._get_document_query_intent("what is this document?") == (
        "structure"
    )


def test_get_document_query_intent_treats_book_about_as_summary():
    """Book-about fallback heuristics should map to summary intent."""
    mixin = _DummyNodeFunctions()

    assert mixin._get_document_query_intent("what is this book about?") == (
        "summary"
    )


def test_recover_forced_response_content_rejects_summary_prompt_echo():
    """Summary prompt guidance should not leak into the final visible answer."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            "Explain the central worldview/argument/subject first, then "
            "cover supporting ideas/details. Merge overlapping evidence. "
            "Prefer specific details."
        ),
        additional_kwargs={
            "thinking_content": (
                "1. The book presents a darkly comic cemetery mystery where "
                "the living and dead constantly brush against each other.\n"
                "2. It follows eccentric characters as they investigate "
                "crypts, danger, memory, and grief in a setting where the "
                "past keeps intruding on the present."
            )
        },
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == (
        "The book presents a darkly comic cemetery mystery where the "
        "living and dead constantly brush against each other. It follows "
        "eccentric characters as they investigate crypts, danger, memory, "
        "and grief in a setting where the past keeps intruding on the "
        "present."
    )


def test_recover_forced_response_content_rejects_verification_meta_text():
    """Verifier meta-review text should not surface as the visible answer."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            '"Focus on the murder mystery, the telling of the story, the '
            'setting (clubs), and the specific detail about the snapshot." '
            "(This looks like an instruction or a note rather than a full "
            "answer, but I need to treat it as the starting point to be "
            "verified against search results)."
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_recover_forced_response_content_rejects_search_results_preface():
    """Search-engine style prefaced summaries should not surface directly."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            "Based on the search results, this appears to be a mystery novel "
            "about a murder and a photograph. Would you like me to search "
            "for more specific details?"
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_recover_forced_response_content_rejects_document_excerpt_search_offer():
    """Document-excerpt hedging and search offers should not surface."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            "Based on the document excerpt, this appears to be a mystery "
            "novel about a murder and a photograph. Would you like me to "
            "search for more specific details about the plot, characters, "
            "or themes in the document?"
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_recover_forced_response_content_rejects_wrapped_verification_verdict():
    """Wrapped verification verdict text should not surface as the answer."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            '"Narrator remembers seeing someone twenty years ago on roller '
            'skates... killed in a car crash." -> Supported by evidence.'
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_recover_forced_response_content_rejects_summary_direction_text():
    """Imperative summary directions should not surface as the answer."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            "Focus on the murder mystery aspect, the conversation between "
            "the two characters, and the specific clue (the snapshot)."
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_recover_forced_response_content_rejects_summary_format_description():
    """Summary format descriptions should not surface as the answer."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            "A bulleted list of key elements extracted from a snippet "
            "(Setting, Topic, Characters, Action, Context, Tone)."
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_recover_forced_response_content_rejects_summary_clarification():
    """Clarification requests should not replace a document summary."""
    mixin = _DummyNodeFunctions()
    response = AIMessage(
        content=(
            "I'm a bit confused about which specific book you're referring "
            "to, as the search results only provide a short excerpt. Could "
            "you clarify the title or author of the book you're asking "
            "about?"
        ),
        tool_calls=[],
    )

    recovered = mixin._recover_forced_response_content(
        response,
        reject_structure_only=True,
    )

    assert recovered == ""


def test_generate_response_message_keeps_draft_when_verifier_returns_meta_text():
    """Bad verifier meta output should not replace a usable drafted answer."""
    mixin = _VerificationFallbackNodeFunctions()

    response = mixin._generate_response_message_from_results(
        "Evidence excerpts:\nA doctor recalls recognizing a murderer from a "
        "snapshot at a Caribbean resort.",
        "rag_search",
        "what is this book about?",
    )

    assert response is not None
    assert response.content == (
        "Miss Marple looks into a resort murder after a doctor realizes he "
        "once recognized a killer from a snapshot."
    )


def test_document_conversational_pass_uses_final_system_prompt_override():
    """Final document replies should swap back to a chat-style prompt."""
    mixin = _DocumentFollowupPromptNodeFunctions()
    mixin.llm_request = SimpleNamespace(
        final_system_prompt="final override prompt"
    )

    response = mixin._run_document_conversational_pass(
        "Grounded answer",
        user_question="what is this book about?",
        message_history=[HumanMessage(content="what is this book about?")],
    )

    assert response is not None
    assert response.content == "Conversational reply"
    assert mixin.prompt_built_with == "final override prompt"
    assert mixin.prompt_seen == "final override prompt"
    assert mixin._system_prompt == "planner prompt"
    assert mixin.prompt_updates == [
        "final override prompt",
        "planner prompt",
    ]


def test_call_model_uses_final_prompt_for_document_analysis_followup():
    """Planner-selected document followups should answer with chat prompt."""
    mixin = _CallModelDocumentFollowupNodeFunctions()
    mixin.llm_request = SimpleNamespace(
        document_answer_mode="synthesized",
        final_system_prompt="final override prompt",
    )
    state = {
        "messages": [
            HumanMessage(content="what is this book about?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "analyze_loaded_document",
                        "args": {
                            "query": "what is this book about?",
                        },
                    }
                ],
            ),
            ToolMessage(
                content=(
                    "Current document analysis:\n\n"
                    "Analysis mode: chunked_document\n\n"
                    "Refined whole-document synthesis:\n"
                    "Overview: A detective investigates a murder."
                ),
                tool_call_id="tool-1",
                name="analyze_loaded_document",
            ),
        ],
        "generation_kwargs": {"temperature": 0.2},
    }

    result = mixin._call_model(state)

    assert result["messages"][0].content == "Conversational reply"
    assert mixin.prompt_built_with == "final override prompt"
    assert mixin.prompt_seen == "final override prompt"
    assert mixin._system_prompt == "planner prompt"
    assert mixin.prompt_updates == [
        "final override prompt",
        "planner prompt",
    ]
    assert mixin._chat_model.tools == ["analyze_loaded_document"]
    assert mixin._chat_model.tool_choice == {
        "function": {"name": "analyze_loaded_document"}
    }
    assert mixin._tools == ["analyze_loaded_document"]