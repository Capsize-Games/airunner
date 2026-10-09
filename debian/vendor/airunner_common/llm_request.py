"""Shared LLM request payload (issue Capsize-Games/airunner#2221).

Desktop (``airunner``) and services (``airunner-services``) each carried
their own ``LLMRequest`` dataclass. Unlike ``LLMResponse`` (#2188), both
copies also carried real per-topology *business logic* -- different ORM
and settings resolution (``from_chatbot``/``from_llm_settings``),
independently-authored generation-preset tables (``for_action``) and two
different serialization targets (desktop's daemon-wire ``to_dict`` vs.
services' direct-``generate()`` ``to_generation_kwargs``). None of that
belongs in this dependency-light foundation, so only the dataclass
*fields* move here; each distribution subclasses this class and keeps its
own methods verbatim.

This class is deliberately the **contract subset** -- exactly the fields
both distributions need -- not the union of every field either side
happens to declare. The private fields stay private:

* desktop-only (planning/pre-processing state, always popped before the
  daemon wire payload is built): ``final_system_prompt``,
  ``rewritten_prompt``, ``preprocessed_primary_tool``, ``planner_mode``,
  ``planner_tool_hints``, ``attached_document_*``, ``document_*``,
  ``request_plan``;
* services-only (Ollama/OpenAI-compat + GGUF runtime selection):
  ``gguf_runtime_profile``, ``client_tools``, ``client_tool_choice``,
  ``raw_mode``.

Unioning those into this base would *not* have been behavior-neutral.
Services' legacy-API route layer copies untrusted request fields onto an
``LLMRequest`` behind a ``hasattr(llm_request, key)`` filter
(``airunner_services.api.routes.legacy_llm_helpers._populate_llm_fields``)
and its request model sets ``extra="allow"``
(``LegacyLLMGenerateRequest``) -- so gaining the desktop-only attributes
would have let an external API caller start injecting desktop-local
planning state (``request_plan``, ``document_summary_focus``, ...) into a
services request, some of which the RAG helpers already read
defensively. Keeping each side's private fields on its own subclass
preserves the ``hasattr`` result set exactly, so this move is field-for-
field a no-op on both sides. See #2221 for the full investigation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from airunner_common.contract_enums import MessageRole


@dataclass
class LLMRequest:
    """The desktop/daemon LLM request fields both distributions share.

    Subclassed (not used directly) by each distribution, which add only
    their own private fields and their own classmethods. Every field here
    carries the same name, type and default it had on both sides before
    the merge, so a subclass instance is indistinguishable from the
    pre-merge class for every shared field.
    """

    do_sample: bool = True
    early_stopping: bool = True
    eta_cutoff: int = 200
    length_penalty: float = 1.0
    max_new_tokens: int = 8192  # Qwen2.5 generation limit, Qwen3 can do 32768
    min_length: int = 1
    no_repeat_ngram_size: int = 3  # Block 3-word phrase repetition
    num_beams: int = 1
    num_return_sequences: int = 1
    repetition_penalty: float = 1.15  # Penalize token repetition
    temperature: float = 0.7  # Qwen3 non-thinking mode recommended
    top_k: int = 20  # Qwen3 recommended value
    top_p: float = 0.8  # Qwen3 non-thinking mode recommended
    use_cache: bool = True
    do_tts_reply: bool = True  # Whether to convert the reply to speech
    node_id: Optional[str] = None
    use_memory: bool = True
    ephemeral: bool = False  # If True, conversation won't be saved to database
    # Default: no tools (empty list). Use None for all tools.
    tool_categories: Optional[List[str]] = field(default_factory=list)
    role: MessageRole = MessageRole.USER
    system_prompt: Optional[str] = None  # Optional system prompt override
    response_format: Optional[str] = (
        None  # Override response format instruction (e.g., "json")
    )
    # List of file paths to load into RAG
    rag_files: Optional[List[str]] = field(default_factory=list)
    # If True, conversation stays in memory but not saved to database
    ephemeral_conversation: bool = False
    # Optional prompt augmentation toggles (used when a custom
    # system_prompt is provided).
    include_mood: Optional[bool] = None
    include_datetime: Optional[bool] = None
    include_style: Optional[bool] = None
    include_memory: Optional[bool] = None
    include_ui_context: Optional[bool] = None
    # Request-level thinking toggle (Qwen3-style <think> blocks).
    # None means "use the global DB/default setting".
    enable_thinking: Optional[bool] = None
    # GPT-OSS reasoning effort override for runtimes without a native API knob.
    reasoning_effort: Optional[str] = None
    model: str = ""
    # Request-level backend selection
    model_service: Optional[str] = None  # local | openrouter | ollama
    api_model: Optional[str] = None  # provider model name for API backends
    # Request-level quantization override for local HF models. Consumed by the
    # model manager before loading; must NOT reach transformers generate().
    dtype: Optional[str] = None  # auto | 4bit | 8bit | 32bit
    # Force a specific tool to be called (from slash commands)
    force_tool: Optional[str] = None
    # List of PIL Image objects for vision-capable models
    images: Optional[List[Any]] = field(default_factory=list)
