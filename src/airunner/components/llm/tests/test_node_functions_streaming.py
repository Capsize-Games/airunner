"""Tests for streamed thinking persistence in NodeFunctionsMixin."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)
from airunner.enums import SignalCode


def _chunk(content: str) -> SimpleNamespace:
    """Return one fake streamed chunk."""
    return SimpleNamespace(
        message=SimpleNamespace(
            content=content,
            additional_kwargs={},
            tool_calls=[],
        )
    )


def _reasoning_chunk(content: str, thinking: str) -> SimpleNamespace:
    """Return one fake streamed chunk with reasoning metadata."""
    return SimpleNamespace(
        message=SimpleNamespace(
            content=content,
            additional_kwargs={"reasoning_content": thinking},
            tool_calls=[],
        )
    )


def _tool_call_chunk(tool_name: str) -> SimpleNamespace:
    """Return one fake streamed chunk that carries a parsed tool call."""
    return SimpleNamespace(
        message=SimpleNamespace(
            content="",
            additional_kwargs={},
            tool_calls=[
                {
                    "id": "tool-1",
                    "name": tool_name,
                    "args": {"query": "what is this document?"},
                }
            ],
        )
    )


class NodeFunctionsMixinDouble(NodeFunctionsMixin):
    """Small test double for NodeFunctionsMixin streaming helpers."""

    def __init__(self, chunks):
        """Initialize one fake chat model stream."""
        self._chat_model = SimpleNamespace(
            stream=lambda *_args, **_kwargs: iter(chunks)
        )
        self._current_request_id = "req-1"
        self._interrupted = False
        self._signal_emitter = SimpleNamespace(emit_signal=Mock())
        self._token_callback = Mock()
        self.logger = Mock()

    @staticmethod
    def _is_tool_call_json(_text):
        """Return False for plain text chunks in tests."""
        return False


def test_streaming_response_excludes_thinking_blocks_from_content():
    """Saved streamed content should exclude visible thinking text."""
    thinking = 'Okay, the user said "Hello".'
    mixin = NodeFunctionsMixinDouble(
        [_chunk(f"<think>{thinking}</think>Hello!")]
    )

    message = mixin._generate_streaming_response([], {})

    assert message.content == "Hello!"
    assert message.additional_kwargs["thinking_content"] == thinking
    mixin._token_callback.assert_called_once_with("Hello!")


def test_headless_streaming_persists_visible_text_only():
    """Headless streams should save visible text separately from thinking."""
    thinking = 'Okay, the user said "Hello".'
    mixin = NodeFunctionsMixinDouble(
        [_chunk(f"<think>{thinking}</think>Hello!")]
    )
    mixin._signal_emitter = None

    message = mixin._generate_streaming_response([], {})

    assert message.content == "Hello!"
    assert message.additional_kwargs["thinking_content"] == thinking
    mixin._token_callback.assert_called_once_with(
        f"<think>{thinking}</think>Hello!"
    )


def test_headless_reasoning_deltas_still_persist_thinking_content():
    """Reasoning deltas should be persisted without a GUI emitter."""
    thinking = 'Okay, the user said "Hello".'
    mixin = NodeFunctionsMixinDouble([_reasoning_chunk("Hello!", thinking)])
    mixin._signal_emitter = None

    message = mixin._generate_streaming_response([], {})

    assert message.content == "Hello!"
    assert message.additional_kwargs["thinking_content"] == thinking
    mixin._token_callback.assert_called_once_with("Hello!")


def test_headless_streaming_emits_structured_thinking_phase_chunks(
    monkeypatch,
):
    """Headless streams should emit typed thinking chunks for daemon NDJSON."""
    monkeypatch.setenv("AIRUNNER_HEADLESS", "1")
    mixin = NodeFunctionsMixinDouble([_reasoning_chunk("Hello!", "plan")])

    mixin._generate_streaming_response([], {})

    thinking_chunks = [
        call.args[1]["response"]
        for call in mixin._signal_emitter.emit_signal.call_args_list
        if call.args[0] == SignalCode.LLM_TEXT_STREAMED_SIGNAL
    ]

    assert [chunk.message_type for chunk in thinking_chunks] == [
        "thinking",
        "thinking",
    ]
    assert thinking_chunks[0].thinking_content == "plan"
    assert thinking_chunks[0].is_first_message is True
    assert thinking_chunks[-1].is_end_of_message is True


def test_headless_streaming_emits_structured_tool_call_chunks(monkeypatch):
    """Headless streams should emit typed tool-call chunks for daemon NDJSON."""
    monkeypatch.setenv("AIRUNNER_HEADLESS", "1")
    mixin = NodeFunctionsMixinDouble([_tool_call_chunk("rag_search")])

    message = mixin._generate_streaming_response([], {})

    assert message.tool_calls[0]["name"] == "rag_search"
    phase_chunks = [
        call.args[1]["response"]
        for call in mixin._signal_emitter.emit_signal.call_args_list
        if call.args[0] == SignalCode.LLM_TEXT_STREAMED_SIGNAL
    ]
    assert len(phase_chunks) == 1
    assert phase_chunks[0].message_type == "tool_call"
    assert phase_chunks[0].tool_name == "rag_search"
    assert phase_chunks[0].tool_arguments == {
        "query": "what is this document?"
    }


def test_streamed_tool_calls_persist_request_debug_metadata():
    """Tool-call messages should keep request settings for later UI restore."""
    mixin = NodeFunctionsMixinDouble([_tool_call_chunk("rag_search")])
    mixin.llm_request = SimpleNamespace(
        to_debug_metadata=lambda title="Request Settings": {
            "kind": "llm_request_settings",
            "title": title,
            "settings": {"max_new_tokens": 500},
        }
    )

    message = mixin._generate_streaming_response([], {})

    assert message.additional_kwargs["tool_status_metadata"] == {
        "kind": "llm_request_settings",
        "title": "Request Settings",
        "settings": {"max_new_tokens": 500},
    }


def test_force_tool_turn_suppresses_visible_planning_text():
    """Forced tool turns should not stream planning prose into chat."""
    mixin = NodeFunctionsMixinDouble(
        [
            _chunk(
                "I'd be happy to help identify the document. "
                "Let me search first."
            ),
            _tool_call_chunk("rag_search"),
        ]
    )
    mixin._force_tool = "rag_search"

    message = mixin._generate_streaming_response([], {})

    assert message.content == ""
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0]["id"] == "tool-1"
    assert message.tool_calls[0]["name"] == "rag_search"
    assert message.tool_calls[0]["args"] == {
        "query": "what is this document?"
    }
    mixin._token_callback.assert_not_called()


def test_forced_tool_choice_turn_suppresses_visible_planning_text():
    """Forced tool-choice turns should also hide planning prose."""
    mixin = NodeFunctionsMixinDouble(
        [
            _chunk(
                "I'll search through your uploaded documents to help identify "
                "what document you're referring to."
            ),
            _tool_call_chunk("rag_search"),
        ]
    )
    mixin._tool_choice = {
        "type": "function",
        "function": {"name": "rag_search"},
    }

    message = mixin._generate_streaming_response([], {})

    assert message.content == ""
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0]["name"] == "rag_search"
    mixin._token_callback.assert_not_called()


def test_tool_call_json_detection_handles_flat_tool_query_shape():
    """Legacy flat tool JSON should still be recognized as a tool call."""
    mixin = NodeFunctionsMixinDouble([])

    assert NodeFunctionsMixin._is_tool_call_json(
        mixin,
        '{"tool": "rag_search", "query": "document file type title author"}',
    ) is True


class _ThinkingSensitiveChatModel:
    """Fake model that hides the answer inside thinking unless disabled."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = [{"function": {"name": "rag_search"}}]
        self.tool_choice = {"type": "function", "function": {"name": "rag_search"}}
        self.observed = []

    def stream(self, *_args, **_kwargs):
        self.observed.append(
            {
                "enable_thinking": self.enable_thinking,
                "tools": self.tools,
                "tool_choice": self.tool_choice,
            }
        )
        if self.enable_thinking:
            return iter([_reasoning_chunk("", "draft hidden answer")])
        return iter([_chunk("Visible answer")])


def test_forced_response_stream_disables_thinking_and_tools():
    """Forced synthesis should request a plain visible answer."""
    chat_model = _ThinkingSensitiveChatModel()
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = chat_model

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == "Visible answer"
    assert chat_model.observed == [
        {
            "enable_thinking": False,
            "tools": None,
            "tool_choice": None,
        }
    ]
    assert chat_model.enable_thinking is True
    assert chat_model.tools == [{"function": {"name": "rag_search"}}]
    assert chat_model.tool_choice == {
        "type": "function",
        "function": {"name": "rag_search"},
    }


class _ReasoningOnlyChatModel:
    """Fake model that returns only reasoning text for forced synthesis."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    "",
                    '"I do not have enough information about this document."\n\n'
                    "Thinking Process:\n1. Inspect the request.",
                )
            ]
        )


def test_forced_response_recovers_visible_text_from_reasoning_only_output():
    """Forced synthesis should salvage the first visible paragraph."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _ReasoningOnlyChatModel()

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == "I do not have enough information about this document."


class _StructuredReasoningOnlyChatModel:
    """Fake model that returns only structured planning text."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    "",
                    "Thinking Process:\n\n"
                    "1.  **Analyze the Request:**\n"
                    "    *   Read the prompt.\n\n"
                    "5.  **Refining for Conciseness and Flow:**\n"
                    '    *   "Based on the text provided, this appears to be \'The Ninth Enochian Key\'."\n'
                    '    *   "It serves as a warning against using substances or devices that might cause delusion and enslavement, acting as a protection against false values."\n'
                    '    *   "Additionally, the text describes a ritualistic process where a written message on parchment or paper is burned in a candle flame to send it into the ether, which is mentioned in the context of a Satanic ritual."\n\n'
                    "6.  **Final Review against Constraints:**\n"
                    "    *   Natural and concise.\n",
                )
            ]
        )


def test_forced_response_prefers_drafted_sentences_over_reasoning_headers():
    """Structured reasoning should surface the drafted answer, not the header."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _StructuredReasoningOnlyChatModel()

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == (
        "Based on the text provided, this appears to be 'The Ninth Enochian Key'. "
        "It serves as a warning against using substances or devices that might cause delusion and enslavement, acting as a protection against false values. "
        "Additionally, the text describes a ritualistic process where a written message on parchment or paper is burned in a candle flame to send it into the ether, which is mentioned in the context of a Satanic ritual."
    )


class _PromptCapturingChatModel:
    """Fake model that records the forced synthesis prompt."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter([_chunk("Visible answer")])


class _VerificationPromptCapturingChatModel:
    """Fake model that records draft and verification prompts."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []
        self._responses = [
            [_chunk("Draft answer with a stray travel-stop detail.")],
            [
                _chunk(
                    "The novel centers on an impossible corpse at a "
                    "Hollywood studio beside a cemetery, and the mystery "
                    "pulls the living back into the studio's haunted past."
                )
            ],
        ]

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter(self._responses.pop(0))


class _VerificationVerdictFallbackChatModel:
    """Fake model whose verification pass emits only a verdict note."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []
        self._responses = [
            [
                _chunk(
                    "The novel follows a haunted Hollywood studio mystery "
                    "built around an impossible corpse and the buried past "
                    "tied to the lot and cemetery next door."
                )
            ],
            [
                _chunk(
                    '"Narrator remembers seeing someone twenty years ago on '
                    'roller skates... killed in a car crash." Supported.'
                )
            ],
        ]

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter(self._responses.pop(0))


class _VerificationLabelInventoryFallbackChatModel:
    """Fake model whose verification pass emits only category labels."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []
        self._responses = [
            [
                _chunk(
                    "The novel follows a screenwriter through a haunted "
                    "Hollywood studio mystery after an impossible corpse "
                    "pulls old grudges and buried history back into view."
                )
            ],
            [_chunk("Setting, Premise, Conflict, Characters.")],
        ]

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter(self._responses.pop(0))


class _VerificationSearchOfferFallbackChatModel:
    """Fake model whose verification pass reads like a search engine."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []
        self._responses = [
            [
                _chunk(
                    "Miss Marple becomes involved in a Caribbean resort "
                    "murder after Major Palgrave tries to show her a "
                    "snapshot that identifies a killer."
                )
            ],
            [
                _chunk(
                    "Based on the search results, this appears to be a "
                    "mystery or crime novel set around a murder and a "
                    "photograph. Would you like me to search for more "
                    "specific details?"
                )
            ],
        ]

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter(self._responses.pop(0))


class _VerificationDirectiveFallbackChatModel:
    """Fake model whose verification pass emits directive summary text."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []
        self._responses = [
            [
                _chunk(
                    "Miss Marple becomes involved in a Caribbean resort "
                    "murder after Major Palgrave tries to show her a "
                    "snapshot that identifies a killer."
                )
            ],
            [
                _chunk(
                    "Focus on the murder mystery aspect, the conversation "
                    "between the two characters, and the specific clue "
                    "(the snapshot)."
                )
            ],
        ]

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter(self._responses.pop(0))


class _VerificationFormatDescriptionFallbackChatModel:
    """Fake model whose verification pass describes a format, not a summary."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []
        self._responses = [
            [
                _chunk(
                    "Miss Marple becomes involved in a Caribbean resort "
                    "murder after Major Palgrave tries to show her a "
                    "snapshot that identifies a killer."
                )
            ],
            [
                _chunk(
                    "A bulleted list of key elements extracted from a "
                    "snippet (Setting, Topic, Characters, Action, "
                    "Context, Tone)."
                )
            ],
        ]

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter(self._responses.pop(0))


def test_forced_response_prompt_prioritizes_document_identity_for_rag():
    """RAG synthesis prompt should prioritize document identity cues."""
    mixin = NodeFunctionsMixinDouble([])
    prompt = mixin._build_search_results_prompt(
        "Matched documents:\nDocument 1: The Satanic Bible - Anton LaVey.pdf",
        "rag_search",
        "What is this document?",
    )

    assert "answer directly and briefly by naming the document" in prompt
    assert "Do not mention search results or instructions" in prompt
    assert "author" in prompt
    assert "labels like Draft:, Answer:, or Response:" in prompt


def test_forced_response_prompt_avoids_metadata_repetition_for_structure():
    """Structure prompts should not force repeated document identity."""
    mixin = NodeFunctionsMixinDouble([])
    prompt = mixin._build_search_results_prompt(
        "Document structure:\n1. INTRODUCTION\n2. PROLOGUE",
        "rag_search",
        "what chapters are in it?",
    )

    assert "answer with the section names only" in prompt
    assert "Do not restate the document title" in prompt


def test_forced_response_prompt_requests_thorough_summary():
    """Summary prompts should ask for a fuller synthesis."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _PromptCapturingChatModel()

    mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: The Satanic Bible - Anton LaVey.pdf\n"
        "Stored path: /sensitive/path/The Satanic Bible - Anton LaVey.pdf\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from The Satanic Bible - Anton LaVey.pdf]\n"
        "The philosophy contrasts the real world with Christian mysticism.\n\n"
        "[Excerpt 2 from The Satanic Bible - Anton LaVey.pdf]\n"
        "It emphasizes a church of realists and practical ritual.",
        "rag_search",
        "summarize the document for me",
    )

    prompt = mixin._chat_model.prompts[0]
    assert "synthesize the evidence below into a substantive overview" in prompt
    assert "Write 7 to 10 sentences in 2 to 4 short paragraphs" in prompt
    assert "Do not repeat the document title, author, or structure" in prompt
    assert "Do not mention file names, stored paths, excerpt numbers" in prompt
    assert "front-matter anecdotes or biographical trivia secondary" in prompt
    assert "Do not infer divine, supernatural, or hidden-authority beliefs" in prompt
    assert "Evidence excerpts:" in prompt
    assert "Stored path:" not in prompt
    assert "[Excerpt 1 from" not in prompt
    assert "Start with the central themes, not opening trivia." in prompt


def test_forced_response_summary_runs_verification_pass():
    """Summary answers should be finalized through a verification pass."""
    mixin = NodeFunctionsMixinDouble([])
    mixin.llm_request = SimpleNamespace(document_query_intent="summary")
    mixin._chat_model = _VerificationPromptCapturingChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: A Graveyard for Lunatics - Ray Bradbury.mobi\n"
        "Stored path: /sensitive/path/A Graveyard for Lunatics.mobi\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from A Graveyard for Lunatics - Ray Bradbury.mobi]\n"
        "The story opens at a haunted Hollywood studio beside a cemetery.\n\n"
        "[Excerpt 2 from A Graveyard for Lunatics - Ray Bradbury.mobi]\n"
        "An impossible corpse drives the central mystery through the lot.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "The novel centers on an impossible corpse at a Hollywood studio "
        "beside a cemetery, and the mystery pulls the living back into "
        "the studio's haunted past."
    )
    assert len(mixin._chat_model.prompts) == 2
    assert "synthesize the evidence below into a substantive overview" in (
        mixin._chat_model.prompts[0]
    )
    assert "You are verifying and finalizing a document-grounded answer." in (
        mixin._chat_model.prompts[1]
    )
    assert "Draft answer to verify:" in mixin._chat_model.prompts[1]
    assert "Draft answer with a stray travel-stop detail." in (
        mixin._chat_model.prompts[1]
    )
    assert "Evidence excerpts:" in mixin._chat_model.prompts[1]
    assert "Do not answer with claim-by-claim verdicts" in (
        mixin._chat_model.prompts[1]
    )
    assert "Do not answer with bare category labels" in (
        mixin._chat_model.prompts[1]
    )
    assert "Stored path:" not in mixin._chat_model.prompts[1]


def test_forced_response_summary_falls_back_from_verification_verdict():
    """Verification verdict chatter should not replace a valid summary draft."""
    mixin = NodeFunctionsMixinDouble([])
    mixin.llm_request = SimpleNamespace(document_query_intent="summary")
    mixin._chat_model = _VerificationVerdictFallbackChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: A Graveyard for Lunatics - Ray Bradbury.mobi\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from A Graveyard for Lunatics - Ray Bradbury.mobi]\n"
        "The story unfolds around a haunted Hollywood studio and the "
        "cemetery next door.\n\n"
        "[Excerpt 2 from A Graveyard for Lunatics - Ray Bradbury.mobi]\n"
        "An impossible corpse and long-buried history drive the mystery.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "The novel follows a haunted Hollywood studio mystery built "
        "around an impossible corpse and the buried past tied to the lot "
        "and cemetery next door."
    )
    assert len(mixin._chat_model.prompts) == 2


def test_forced_response_summary_falls_back_from_label_inventory():
    """Verification label inventories should not replace a valid summary."""
    mixin = NodeFunctionsMixinDouble([])
    mixin.llm_request = SimpleNamespace(document_query_intent="summary")
    mixin._chat_model = _VerificationLabelInventoryFallbackChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: A Graveyard for Lunatics - Ray Bradbury.mobi\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from A Graveyard for Lunatics - Ray Bradbury.mobi]\n"
        "A screenwriter is drawn into a haunted Hollywood studio mystery.\n\n"
        "[Excerpt 2 from A Graveyard for Lunatics - Ray Bradbury.mobi]\n"
        "An impossible corpse and old grudges drive the conflict.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "The novel follows a screenwriter through a haunted Hollywood "
        "studio mystery after an impossible corpse pulls old grudges and "
        "buried history back into view."
    )
    assert len(mixin._chat_model.prompts) == 2


def test_forced_response_summary_falls_back_from_search_offer():
    """Search-engine style verification output should not replace a draft."""
    mixin = NodeFunctionsMixinDouble([])
    mixin.llm_request = SimpleNamespace(document_query_intent="summary")
    mixin._chat_model = _VerificationSearchOfferFallbackChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: A Caribbean Mystery - Agatha Christie.epub\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from A Caribbean Mystery - Agatha Christie.epub]\n"
        "Miss Marple is staying at a Caribbean resort when Major "
        "Palgrave tries to show her a snapshot of a murderer.\n\n"
        "[Excerpt 2 from A Caribbean Mystery - Agatha Christie.epub]\n"
        "Palgrave is killed before he can explain what he has seen.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "Miss Marple becomes involved in a Caribbean resort murder after "
        "Major Palgrave tries to show her a snapshot that identifies a "
        "killer."
    )
    assert len(mixin._chat_model.prompts) == 2


def test_forced_response_summary_falls_back_from_direction_text():
    """Imperative verification guidance should not replace a draft."""
    mixin = NodeFunctionsMixinDouble([])
    mixin.llm_request = SimpleNamespace(document_query_intent="summary")
    mixin._chat_model = _VerificationDirectiveFallbackChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: A Caribbean Mystery - Agatha Christie.epub\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from A Caribbean Mystery - Agatha Christie.epub]\n"
        "Miss Marple is staying at a Caribbean resort when Major "
        "Palgrave tries to show her a snapshot of a murderer.\n\n"
        "[Excerpt 2 from A Caribbean Mystery - Agatha Christie.epub]\n"
        "Palgrave is killed before he can explain what he has seen.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "Miss Marple becomes involved in a Caribbean resort murder after "
        "Major Palgrave tries to show her a snapshot that identifies a "
        "killer."
    )
    assert len(mixin._chat_model.prompts) == 2


def test_forced_response_summary_falls_back_from_format_description():
    """Format-description verification output should not replace a draft."""
    mixin = NodeFunctionsMixinDouble([])
    mixin.llm_request = SimpleNamespace(document_query_intent="summary")
    mixin._chat_model = _VerificationFormatDescriptionFallbackChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: A Caribbean Mystery - Agatha Christie.epub\n\n"
        "Relevant excerpts:\n"
        "[Excerpt 1 from A Caribbean Mystery - Agatha Christie.epub]\n"
        "Miss Marple is staying at a Caribbean resort when Major "
        "Palgrave tries to show her a snapshot of a murderer.\n\n"
        "[Excerpt 2 from A Caribbean Mystery - Agatha Christie.epub]\n"
        "Palgrave is killed before he can explain what he has seen.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "Miss Marple becomes involved in a Caribbean resort murder after "
        "Major Palgrave tries to show her a snapshot that identifies a "
        "killer."
    )
    assert len(mixin._chat_model.prompts) == 2


class _SummaryBudgetCapturingChatModel:
    """Fake model that records internal synthesis generation kwargs."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.observed_kwargs = []

    def stream(self, *_args, **kwargs):
        self.observed_kwargs.append(dict(kwargs))
        return iter(
            [
                _reasoning_chunk(
                    "",
                    (
                        '"Let\'s focus on the substantive content:" '
                        "The document presents a realist philosophy that "
                        "rejects mystical morality."
                    ),
                )
            ]
        )


def test_forced_response_summary_uses_larger_internal_budget():
    """Summary synthesis should not inherit the tiny outer RAG budget."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _SummaryBudgetCapturingChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
        generation_kwargs={"max_new_tokens": 300, "reasoning_effort": "high"},
    )

    assert message.content == (
        "The document presents a realist philosophy that rejects "
        "mystical morality."
    )
    assert len(mixin._chat_model.observed_kwargs) == 2
    assert mixin._chat_model.observed_kwargs[0]["max_new_tokens"] == 1024
    assert mixin._chat_model.observed_kwargs[0]["reasoning_effort"] == "low"
    assert mixin._chat_model.observed_kwargs[1]["max_new_tokens"] == 1024
    assert mixin._chat_model.observed_kwargs[1]["reasoning_effort"] == "low"


class _InternalSynthesisReasoningChatModel:
    """Fake model that still emits reasoning during internal synthesis."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    "Visible answer",
                    "Wait, one more check:\nUse the title only.",
                )
            ]
        )


def test_forced_response_keeps_thinking_updates_and_completes():
    """Internal synthesis should stream thinking and buffer raw text."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _InternalSynthesisReasoningChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == "Visible answer"
    assert message.additional_kwargs["thinking_content"] == (
        "Wait, one more check:\nUse the title only."
    )
    assert message.additional_kwargs["thinking_metadata"]["stage"] == (
        "document_verification"
    )
    statuses = [
        call.args[1]["status"]
        for call in mixin._signal_emitter.emit_signal.call_args_list
        if call.args[0] == SignalCode.LLM_THINKING_SIGNAL
    ]
    thinking_updates = [
        call.args[1]
        for call in mixin._signal_emitter.emit_signal.call_args_list
        if call.args[0] == SignalCode.LLM_THINKING_SIGNAL
    ]
    preset_ids = {
        call.args[1]["metadata"].get("preset_id")
        for call in mixin._signal_emitter.emit_signal.call_args_list
        if call.args[0] == SignalCode.LLM_THINKING_SIGNAL
        and call.args[1].get("metadata")
    }
    assert statuses[:3] == ["started", "streaming", "completed"]
    assert statuses[-1] == "completed"
    assert preset_ids == {
        "document_synthesis",
        "document_verification",
    }
    assert thinking_updates[-1]["metadata"]["stage"] == (
        "document_verification"
    )
    mixin._token_callback.assert_not_called()


class _SummaryStructureLeakChatModel:
    """Fake model that leaks structure in visible text but drafts a summary."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    (
                        "INTRODUCTION PROLOGUE THE BOOK OF SATAN "
                        "THE BOOK OF LUCIFER THE BOOK OF BELIAL "
                        "THE BOOK OF LEVIATHAN"
                    ),
                    (
                        "5. **Final Polish:**\n"
                        "This work positions itself as a profound explanation "
                        "of Satanism that prioritizes the real world over the "
                        "mystical promises found in religious texts. It frames "
                        "ritual and symbolism as practical tools for realism, "
                        "self-determination, and responsibility rather than "
                        "supernatural revelation."
                    ),
                )
            ]
        )


def test_forced_response_summary_ignores_structure_only_visible_text():
    """Summary synthesis should prefer the drafted summary over TOC text."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _SummaryStructureLeakChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == (
        "This work positions itself as a profound explanation of Satanism "
        "that prioritizes the real world over the mystical promises found "
        "in religious texts. It frames ritual and symbolism as practical "
        "tools for realism, self-determination, and responsibility rather "
        "than supernatural revelation."
    )
    mixin._token_callback.assert_not_called()


class _SummaryInventoryLeakChatModel:
    """Fake model that leaks a markdown inventory instead of prose."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    (
                        "- Document: The Satanic Bible by Anton LaVey\n"
                        "  - Excerpt 1 & 2: Discusses Satanism as a realist "
                        "philosophy grounded in the real world.\n"
                        "  - Excerpt 3 & 4: Says LaVey's books define the "
                        "authentic practice.\n"
                        "  - Excerpt 5: Mentions public visibility, church "
                        "activity, and later editions."
                    ),
                    (
                        "Final answer:\n"
                        "The document presents Satanism as a practical, "
                        "realist philosophy centered on self-determination "
                        "rather than mystical promises. It emphasizes LaVey's "
                        "own books and rituals as the authoritative expression "
                        "of that worldview, while also pointing to its growing "
                        "public presence and institutional visibility."
                    ),
                )
            ]
        )


def test_forced_response_summary_ignores_inventory_list_visible_text():
    """Summary synthesis should prefer prose over markdown inventories."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _SummaryInventoryLeakChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == (
        "The document presents Satanism as a practical, realist philosophy "
        "centered on self-determination rather than mystical promises. It "
        "emphasizes LaVey's own books and rituals as the authoritative "
        "expression of that worldview, while also pointing to its growing "
        "public presence and institutional visibility."
    )
    assert "- Document:" not in message.content


class _ConstraintHeavySummaryReasoningChatModel:
    """Fake model that mirrors the screenshot-style summary reasoning."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    (
                        "INTRODUCTION PROLOGUE THE BOOK OF SATAN "
                        "THE BOOK OF LUCIFER THE BOOK OF BELIAL "
                        "THE BOOK OF LEVIATHAN"
                    ),
                    (
                        '"Let\'s focus on the substantive content:" '
                        "The document contrasts the real world with "
                        "Christian mysticism and presents Satanism as a "
                        "practical philosophy for a \"church of realists.\" "
                        "It treats ritual, authorship, and public identity as "
                        "tools for a self-directed worldview rather than "
                        "mystical revelation.\n\n"
                        "*Draft 1 (Mental):* This document is about Anton "
                        "LaVey's The Satanic Bible. It says Satanism is about "
                        "the real world, not like the Christian Bible's "
                        "mystical lands.\n\n"
                        "*Refining for Constraints:* Needs to be "
                        "conversational, 1-2 paragraphs, no title repetition.\n\n"
                        "*Refining for \"Do not repeat the document title\":* "
                        "I should avoid explicitly naming the book as the "
                        "main focus."
                    ),
                )
            ]
        )


def test_forced_response_summary_recovers_constraint_heavy_reasoning():
    """Summary recovery should pull the substantive draft out of reasoning."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _ConstraintHeavySummaryReasoningChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == (
        "The document contrasts the real world with Christian mysticism "
        "and presents Satanism as a practical philosophy for a \"church "
        "of realists.\" It treats ritual, authorship, and public identity "
        "as tools for a self-directed worldview rather than mystical "
        "revelation."
    )


class _MalformedVisibleFragmentSummaryChatModel:
    """Fake model that leaks a truncated label tail as visible text."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    '", "Answer:").',
                    (
                        '"Let\'s focus on the substantive content:" '
                        "The document argues for strength, realism, and "
                        "ritualized self-determination instead of Christian "
                        "humility and universal love. It presents LaVeyan "
                        "Satanism as a deliberate inversion of conventional "
                        "religious morality."
                    ),
                )
            ]
        )


def test_forced_response_summary_ignores_malformed_visible_fragment():
    """Malformed prompt-tail fragments should not override drafted summary."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _MalformedVisibleFragmentSummaryChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == (
        "The document argues for strength, realism, and ritualized "
        "self-determination instead of Christian humility and universal "
        "love. It presents LaVeyan Satanism as a deliberate inversion of "
        "conventional religious morality."
    )


class _ReasoningHeaderVisibleSummaryChatModel:
    """Fake model that leaks only reasoning-stage headers as visible text."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    (
                        "Analyze the Request: Analyze the Evidence: "
                        "Drafting - Step 1 (Mental Outline): Drafting - "
                        "Step 2 (Writing & Counting)::"
                    ),
                    (
                        "Final answer: The novel is set around a haunted "
                        "Hollywood studio bordered by a cemetery, and it "
                        "centers on an impossible corpse and the mystery "
                        "that ties the dead man back to the studio's past."
                    ),
                )
            ]
        )


def test_forced_response_summary_ignores_reasoning_header_only_visible_text():
    """Summary recovery should reject visible scaffolding headers."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _ReasoningHeaderVisibleSummaryChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "what is this book about?",
    )

    assert message.content == (
        "The novel is set around a haunted Hollywood studio bordered by a "
        "cemetery, and it centers on an impossible corpse and the mystery "
        "that ties the dead man back to the studio's past."
    )


def test_numbered_summary_normalization_ignores_bold_reasoning_headers():
    """Numbered reasoning recovery should skip bold planning headers."""
    normalized = NodeFunctionsMixin._normalize_numbered_summary_response(
        "1. **Analyze the Request:**\n"
        "2. **Analyze the Evidence:**\n"
        "3. The novel centers on an impossible corpse at a Hollywood studio.\n"
        "4. The setting blends studio life with the cemetery next door."
    )

    assert normalized == (
        "The novel centers on an impossible corpse at a Hollywood studio. "
        "The setting blends studio life with the cemetery next door."
    )


class _PersistedMalformedSummaryChatModel:
    """Fake model that mirrors the malformed persisted runtime summary."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    '", "Answer:").',
                    (
                        "Thinking Process:\n\n"
                        "1.  **Analyze the Request:**\n"
                        "    *   Task: Summarize the provided document excerpts.\n"
                        "    *   Tone: Natural and conversational.\n"
                        "    *   Constraints:\n"
                        "        *   Length: 4 to 6 sentences in one or two "
                        "short paragraphs.\n"
                        "        *   Start directly with the substance (no "
                        "labels like \"Draft:\", \"Answer:\").\n\n"
                        "2.  **Analyze the Evidence:**\n"
                        "    *   *Excerpt 1:* Anton LaVey, \"Black Pope,\" "
                        "started Church of Satan at 16.\n"
                        "    *   *Excerpt 2:* The text rejects traditional "
                        "religious morality.\n\n"
                        "3.  **Synthesize and Draft:**\n"
                        "    *   *Drafting sentences (aiming for 4-6):*\n"
                        "        1.  Anton LaVey, known as the \"Black Pope,\" "
                        "founded the Church of Satan at age sixteen, drawing "
                        "inspiration from the stark contrasts he witnessed "
                        "between carnal indulgence and religious preaching "
                        "during his carnival days.\n"
                        "        2.  The central argument rejects traditional "
                        "religious morality, questioning the rational "
                        "authority of loving one's enemies and suggesting "
                        "that wisdom-defiled gods have exhausted their "
                        "millennium.\n"
                        "        3.  Instead, the text advocates for a "
                        "worldview where the strong, powerful, and bold are "
                        "blessed with wealth and mastery, while the weak, "
                        "feeble, and righteously humble are cursed to "
                        "inherit the yoke.\n"
                        "        4.  This philosophy extends to ritual "
                        "practice, asserting that verbal communication can "
                        "evoke emotional ecstasy and that words serve as "
                        "monuments to thoughts within magical ceremonies.\n"
                        "        5.  Ultimately, the work calls for "
                        "awakening men of \"mildewed minds\" to a new "
                        "reality where death is declared to the weakling and "
                        "wealth is promised to the strong.\n\n"
                        "    *   *Review against constraints:*\n"
                        "        *   4-6 sentences? Yes (5 sentences).\n"
                        "        *   Specific details? Yes ("
                    ),
                )
            ]
        )


def test_forced_response_summary_recovers_numbered_draft_block():
    """Recovery should extract numbered draft sentences from thinking."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _PersistedMalformedSummaryChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == (
        "Anton LaVey, known as the \"Black Pope,\" founded the Church "
        "of Satan at age sixteen, drawing inspiration from the stark "
        "contrasts he witnessed between carnal indulgence and religious "
        "preaching during his carnival days. The central argument rejects "
        "traditional religious morality, questioning the rational "
        "authority of loving one's enemies and suggesting that "
        "wisdom-defiled gods have exhausted their millennium. Instead, "
        "the text advocates for a worldview where the strong, powerful, "
        "and bold are blessed with wealth and mastery, while the weak, "
        "feeble, and righteously humble are cursed to inherit the yoke. "
        "This philosophy extends to ritual practice, asserting that "
        "verbal communication can evoke emotional ecstasy and that words "
        "serve as monuments to thoughts within magical ceremonies. "
        "Ultimately, the work calls for awakening men of \"mildewed "
        "minds\" to a new reality where death is declared to the "
        "weakling and wealth is promised to the strong."
    )


class _ExcerptOnlyVisibleSummaryChatModel:
    """Fake model that leaks only excerpt bullets as visible content."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    (
                        "- Excerpt 1: Discusses Satanism as a realistic "
                        "philosophy grounded in the real world.\n"
                        "  - Excerpt 2: States LaVey's books are the only "
                        "authentic guides to the practice.\n"
                        "- Excerpt 3: Mentions public visibility, church "
                        "activity, and later editions."
                    ),
                    (
                        '"Let\'s focus on the substantive content:" '
                        "The document presents Satanism as a practical "
                        "philosophy rooted in realism rather than mystical "
                        "religious promises. It emphasizes LaVey's books and "
                        "ritual practice as the authoritative expression of "
                        "that worldview, while also pointing to the movement's "
                        "public visibility and institutional presence."
                    ),
                )
            ]
        )


def test_forced_response_summary_ignores_excerpt_only_visible_inventory():
    """Summary recovery should reject excerpt-only bullet inventories."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _ExcerptOnlyVisibleSummaryChatModel()

    message = mixin._generate_response_message_from_results(
        "Relevant excerpts:\nA substantive passage.",
        "rag_search",
        "summarize the document for me",
    )

    assert message.content == (
        "The document presents Satanism as a practical philosophy rooted "
        "in realism rather than mystical religious promises. It "
        "emphasizes LaVey's books and ritual practice as the authoritative "
        "expression of that worldview, while also pointing to the "
        "movement's public visibility and institutional presence."
    )
    assert "Excerpt 1:" not in message.content


class _MetaIdentityResponseChatModel:
    """Fake model that emits meta instruction chatter as visible text."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _chunk(
                    "Actually, looking at the instruction, I should just "
                    "state the facts naturally."
                )
            ]
        )


def test_forced_response_identity_falls_back_from_meta_visible_text():
    """Identity answers should not surface meta instruction chatter."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _MetaIdentityResponseChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\n"
        "Document 1: The Satanic Bible - Anton LaVey.pdf\n"
        "Inferred title from filename: The Satanic Bible\n"
        "Inferred author from filename: Anton LaVey\n"
        "File type: .pdf",
        "rag_search",
        "What is this document?",
    )

    assert message.content == (
        "This document is a PDF document titled 'The Satanic Bible' "
        "by Anton LaVey."
    )


class _DraftPrefixedVisibleResponseChatModel:
    """Fake model that prefixes a visible answer with a draft label."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _chunk(
                    "Draft: Based on the retrieved passages, I can see "
                    "two section titles."
                )
            ]
        )


def test_forced_response_strips_visible_draft_label():
    """Visible forced responses should drop synthetic draft prefixes."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _DraftPrefixedVisibleResponseChatModel()

    message = mixin._generate_response_message_from_results(
        "Matched documents:\nDocument 1: Example.pdf",
        "rag_search",
        "what are the chapters in it?",
    )

    assert message.content == (
        "Based on the retrieved passages, I can see two section titles."
    )


class _ModernRagReasoningOnlyChatModel:
    """Fake model that mirrors the current numbered RAG reasoning format."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    "",
                    "Thinking Process:\n\n"
                    "1.  **Analyze the Request:**\n"
                    "    *   Task: Answer the user's question (\"what is this document?\") based on search results.\n"
                    "    *   Constraint 1: Respond naturally and conversationally.\n"
                    "    *   Constraint 2: If search results include document identity fields (name, author, path, etc.), identify the document first before describing excerpt details.\n"
                    "    *   Input: Search results showing a PDF file named \"The Satanic Bible - Anton LaVey.pdf\" with excerpts from it.\n\n"
                    "2.  **Analyze the Search Results:**\n"
                    "    *   Document 1: The Satanic Bible - Anton LaVey.pdf\n\n"
                    "3.  **Draft the Response:**\n"
                    "    *   *Identify the document first:* This is a PDF file titled \"The Satanic Bible\" by Anton LaVey.\n"
                    "    *   *Describe excerpt details:* The excerpts show content related to \"The Ninth Enochian Key.\"\n\n"
                    "4.  **Refine the Response:**\n"
                    "    *   \"Based on the file information, this document is a PDF titled 'The Satanic Bible' by Anton LaVey.\"\n"
                    "    *   *Combine for flow:* \"This document is a PDF file titled 'The Satanic Bible' by Anton LaVey. The excerpts indicate it contains sections like 'The Ninth Enochian Key.'\"\n\n"
                    "5.  **Final Polish:** Ensure it sounds conversational.\n\n"
                    "    *   \"This document is a PDF file titled 'The Satanic Bible' by Anton LaVey. The excerpts indicate it contains sections like 'The Ninth Enochian Key,' which warns against substances or devices that might lead to delusion or enslavement.\"\n\n"
                    "    *Self-Correction on \"Identify first\":*\n"
                    "    *Draft:* This document is a PDF file titled \"The Satanic Bible\" by Anton LaVey.\n"
                )
            ]
        )


def test_forced_response_recovers_modern_rag_reasoning_answer():
    """Modern numbered RAG reasoning should recover the drafted answer."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _ModernRagReasoningOnlyChatModel()

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == (
        "This document is a PDF file titled 'The Satanic Bible' by Anton "
        "LaVey. The excerpts indicate it contains sections like 'The Ninth "
        "Enochian Key,' which warns against substances or devices that might "
        "lead to delusion or enslavement."
    )