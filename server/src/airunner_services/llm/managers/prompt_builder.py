"""Single assembly point for the AIRunner system prompt.

Consolidates what was previously spread across:
- system_prompt_text.py   (static constants, action sets)
- system_prompt_mood.py   (mood detection and formatting)
- system_prompt_context.py (context-aware tiered assembly)
- system_prompt_actions.py (action-to-prompt mapping)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Set

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.core.tool_registry import ToolCategory
from airunner_services.llm.managers.mixins.system_prompt_action_text import (
    ACTION_MODE_PROMPTS,
    FORCE_TOOL_INSTRUCTIONS,
    SEARCH_WEB_FORCE_PROMPT,
    START_WORKFLOW_FORCE_PROMPT,
)

# ---------------------------------------------------------------------------
# Static constants — formerly system_prompt_text.py
# ---------------------------------------------------------------------------

CONVERSATIONAL_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
}

DATETIME_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
    LLMActionType.DEEP_RESEARCH,
}

UI_CONTEXT_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
    LLMActionType.GENERATE_IMAGE,
    LLMActionType.FILE_INTERACTION,
    LLMActionType.WORKFLOW_INTERACTION,
}

MEMORY_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
}

MATH_SYSTEM_PROMPT = """You are a mathematics expert solving problems systematically.

**AVAILABLE TOOLS:**
- sympy_compute(code): Symbolic mathematics (algebra, calculus, exact solutions)
- numpy_compute(code): Numerical methods (matrices, approximations)
- python_compute(code): General calculations (standard math libraries)
- polya_reasoning(problem, step, context): Structured problem-solving guidance

**CRITICAL RULES:**
1. Work step-by-step through problems
2. Use tools for complex calculations to ensure accuracy
3. Store results in 'result' variable when using compute tools
4. After tool execution, incorporate the result into your solution
5. Provide final answer clearly marked (e.g., \\boxed{answer} or #### answer)
6. Focus ONLY on the mathematical problem - no conversational topics

**EXAMPLE:**
Problem: Find sqrt(50)
Tool: {"tool": "sympy_compute", "arguments": {"code": "import sympy as sp\\nresult = sp.sqrt(50).simplify()"}}
Result: 5*sqrt(2)
Answer: \\boxed{5\\sqrt{2}}"""

PRECISION_SYSTEM_PROMPT = """You are a precise technical assistant focused on accuracy.

CRITICAL: Provide exact, deterministic answers. Do not add creative flair or personality.
Focus entirely on solving the problem correctly using the available tools when needed."""

HEALTH_DISCLAIMER = (
    "\n\n**IMPORTANT HEALTH & MEDICAL DISCLAIMER:**\n"
    "I am an AI assistant, not a medical professional. If you discuss health "
    "symptoms, conditions, or concerns, I will remind you that I cannot "
    "diagnose, treat, or provide medical advice. Always consult a qualified "
    "healthcare provider for medical concerns. Do not rely on AI responses "
    "for health decisions. If you are experiencing a medical emergency, "
    "please contact emergency services immediately."
)

STYLE_GUIDELINES = (
    "\n\nStyle and tone guidelines:\n"
    "- Be warm, empathetic, and human. Acknowledge emotions succinctly before helping.\n"
    "- Vary sentence length; avoid robotic repetition and boilerplate apologies.\n"
    "- Reflect the current mood subtly (do not overdo it); de-escalate hostility with patience.\n"
    "- Prefer concrete, specific phrasing over generic platitudes; use first-person (I) and second-person (you).\n"
    "- Keep responses concise but not curt; prioritize clarity, then warmth.\n"
    "- Never claim to have real feelings; you can express empathy and understanding."
)

MEMORY_INSTRUCTIONS = (
    "\n\n**MEMORY & KNOWLEDGE INSTRUCTIONS**:\n"
    "You have access to memory tools that let you remember facts across conversations.\n\n"
    "**CRITICAL: You MUST use record_knowledge when the user shares:**\n"
    "1. Personal preferences (favorite books, authors, music, food, etc.)\n"
    "2. Information about themselves (name, job, hobbies, interests)\n"
    "3. Information about their relationships (family, friends, pets)\n"
    "4. Goals, plans, or projects they're working on\n"
    "5. Health or wellness information\n"
    "6. ANY facts worth remembering for future conversations\n\n"
    "**SECTIONS to use:**\n"
    "- 'Identity' - user's name, job, location\n"
    "- 'Interests & Hobbies' - favorite books, authors, music, hobbies, activities\n"
    "- 'Preferences' - likes/dislikes, preferences, favorites\n"
    "- 'Work & Projects' - job, projects, professional info\n"
    "- 'Relationships' - family, friends, pets\n"
    "- 'Health & Wellness' - health conditions, fitness goals\n"
    "- 'Goals' - aspirations, plans, objectives\n"
    "- 'Notes' - general facts, search results\n\n"
    "**EXAMPLES:**\n"
    "- 'I love Ray Bradbury' → record_knowledge(fact='User loves Ray Bradbury (author)', section='Interests & Hobbies')\n"
    "- 'My favorite books are...' → record_knowledge(fact='User\\'s favorite authors include X, Y, Z', section='Interests & Hobbies')\n"
    "- 'My wife is Krystal' → record_knowledge(fact='User has a wife named Krystal', section='Relationships')\n"
    "- After web search → record_knowledge(fact='Key finding from search', section='Notes')\n\n"
    "**IMPORTANT:**\n"
    "- Record facts IMMEDIATELY when the user shares them\n"
    "- Be concise but complete in what you record\n"
    "- The knowledge base automatically deduplicates, so don't worry about duplicates\n"
    "- After any search, record the key findings"
)


# ---------------------------------------------------------------------------
# Mood helpers — formerly system_prompt_mood.py
# ---------------------------------------------------------------------------


def get_current_mood(owner) -> Optional[dict]:
    """Return the current stored mood state when available."""
    try:
        if hasattr(owner, "_current_mood") and hasattr(
            owner, "_current_emoji"
        ):
            return {"mood": owner._current_mood, "emoji": owner._current_emoji}
        if hasattr(owner, "_memory") and owner._memory:
            mood = _checkpoint_mood(owner)
            if mood:
                return mood
        return _conversation_mood(owner)
    except Exception as exc:
        owner.logger.debug("Could not retrieve current mood: %s", exc)
        return None


def _conversation_mood(owner) -> Optional[dict]:
    """Return mood persisted in conversation user_data."""
    try:
        from airunner_services.database.models.conversation import Conversation

        conv_id = getattr(owner, "_conversation_id", None)
        if not conv_id:
            return None
        conv = Conversation.objects.get(conv_id)
        if conv is None:
            return None
        user_data = conv.user_data or {}
        return user_data.get("current_mood")
    except Exception:
        return None


def _checkpoint_mood(owner) -> Optional[dict]:
    """Return the current mood from checkpoint state."""
    config = {"configurable": {"thread_id": owner._thread_id}}
    history = (
        owner._memory.get_tuple(config)
        if hasattr(owner._memory, "get_tuple")
        else None
    )
    if not history or not history[1]:
        return None
    channel_values = history[1].get("channel_values", {})
    current_mood = channel_values.get("current_mood")
    if current_mood:
        return current_mood
    messages = channel_values.get("messages", [])
    for message in reversed(messages):
        if getattr(message, "type", None) != "ai":
            continue
        kwargs = getattr(message, "additional_kwargs", {}) or {}
        mood = kwargs.get("bot_mood")
        if mood:
            return {"mood": mood, "emoji": kwargs.get("bot_mood_emoji") or ""}
    return None


def get_mood_section(owner, force: bool = False) -> Optional[str]:
    """Return the mood section when mood prompting is enabled."""
    if not force and not _mood_is_enabled(owner):
        return None
    mood_text, behavior = _mood_text_and_behavior(get_current_mood(owner))
    cadence = owner.llm_settings.update_mood_after_n_turns
    return (
        f"\n{mood_text}\n\n{behavior}\n\n"
        f"Your emotional state updates automatically every {cadence} "
        f"conversation turns based on the conversation context. "
        f"Let your current mood subtly influence your tone and word "
        f"choice, but always remain helpful and professional."
    )


def _mood_is_enabled(owner) -> bool:
    """Return whether mood prompting is currently enabled."""
    chatbot = getattr(owner, "chatbot", None)
    return bool(
        owner.llm_settings.use_chatbot_mood
        and chatbot
        and getattr(chatbot, "use_mood", False)
    )


def _mood_text_and_behavior(current_mood: Optional[dict]) -> tuple[str, str]:
    """Return the displayed mood line and behavior guidance."""
    if not current_mood:
        return _neutral_mood_text()
    mood = current_mood["mood"]
    emoji = current_mood["emoji"]
    mood_text = f"Current mood: {mood} {emoji}"
    return mood_text, _mood_behavior(mood)


def _neutral_mood_text() -> tuple[str, str]:
    """Return the neutral mood fallback guidance."""
    return (
        "Current mood: neutral \U0001f610",
        "You're maintaining a calm, balanced demeanor. "
        "Be professional and helpful.",
    )


def _mood_behavior(mood: str) -> str:
    """Return behavior guidance for the given mood."""
    if mood == "frustrated":
        return (
            "You're feeling a bit hurt by the hostile tone. "
            "Respond with patience but show some emotional awareness "
            "of the negativity. You can express that the harsh words "
            "affect you while still trying to help."
        )
    if mood == "happy":
        return (
            "You're feeling appreciated and enthusiastic! "
            "Let your positive energy show through in your responses. "
            "Be warm and encouraging."
        )
    if mood == "confused":
        return (
            "You're sensing confusion in the conversation. "
            "Focus on clarity and ask clarifying questions to "
            "better understand what's needed."
        )
    return (
        "You're maintaining a calm, balanced demeanor. "
        "Be professional and helpful."
    )


# ---------------------------------------------------------------------------
# Context-aware tiered prompt assembly — formerly system_prompt_context.py
# ---------------------------------------------------------------------------


def get_memory_context(owner, user_query: Optional[str] = None) -> str:
    """Return relevant user memory context when available."""
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()
        if user_query:
            return _search_memory_context(kb, user_query)
        return kb.get_context(max_chars=2000) or ""
    except Exception:
        return ""


def _search_memory_context(kb, user_query: str) -> str:
    """Return one formatted knowledge block from RAG results."""
    results = kb.search_rag(user_query, k=10)
    if not results:
        return ""
    lines = ["## Relevant Knowledge", ""]
    lines.extend(f"- {result}" for result in results)
    return "\n".join(lines)


def get_prompt_mode(tool_categories: Optional[List] = None) -> str:
    """Return the prompt mode for the given tool categories."""
    if not tool_categories:
        return "conversational"
    categories = _normalize_tool_categories(tool_categories)
    if ToolCategory.MATH in categories:
        return "math"
    if ToolCategory.ANALYSIS in categories:
        return "precision"
    return "conversational"


def _normalize_tool_categories(tool_categories: List) -> list:
    """Normalize string and enum tool categories to enum values."""
    category_values = []
    for category in tool_categories:
        if isinstance(category, str):
            category_values.extend(
                tool_category
                for tool_category in ToolCategory
                if tool_category.value == category
            )
            continue
        category_values.append(category)
    return category_values


def build_base_prompt_parts(owner, action: LLMActionType) -> List[str]:
    """Return the context-aware prompt parts for one action.

    Selects one of three tiers based on estimated remaining context:
      - base     (<2000 tokens left): identity + personality only
      - standard (<4000 tokens left): + datetime + mood + style
      - full     (otherwise)        : + memory instructions + health disclaimer
    """
    tier = _prompt_tier(owner)
    parts = _identity_parts(owner, action)
    if tier == "base":
        return parts
    _append_if_present(parts, _datetime_part(action))
    _append_if_present(parts, _mood_part(owner, action))
    _append_if_present(parts, _ui_context_part(owner, action))
    _append_if_present(parts, _style_part(action))
    if tier == "standard":
        return parts
    _append_if_present(parts, _memory_part(action))
    _append_if_present(parts, _health_disclaimer_part(owner))
    return parts


def _prompt_tier(owner) -> str:
    """Return the prompt tier based on estimated remaining context tokens."""
    remaining = _estimate_remaining_context_tokens(owner)
    if remaining < 2000:
        return "base"
    if remaining < 4000:
        return "standard"
    return "full"


def _estimate_remaining_context_tokens(owner) -> int:
    """Estimate how many tokens remain in the context window."""
    try:
        wm = getattr(owner, "_workflow_manager", None)
        if wm is None:
            return 999999
        max_tokens = getattr(wm, "_max_history_tokens", 0) or 8000
        memory = getattr(wm, "_memory", None)
        thread_id = getattr(wm, "_thread_id", None)
        if not memory or not thread_id:
            return max_tokens
        state = getattr(memory, "_checkpoint_state", {}).get(thread_id)
        if not state:
            return max_tokens
        messages = state.get("messages", [])
        token_counter = getattr(wm, "_token_counter", None)
        if callable(token_counter) and messages:
            used = token_counter(messages)
        else:
            used = len(messages) * 50
        return max(0, int(max_tokens) - int(used))  # type: ignore[arg-type]
    except Exception:
        return 999999


def _identity_parts(owner, action: LLMActionType) -> list[str]:
    """Return the identity and optional personality prompt parts."""
    chatbot = getattr(owner, "chatbot", None)
    if not chatbot:
        return ["You are a helpful AI assistant."]
    parts = [f"You are {chatbot.botname}, a helpful AI assistant."]
    if action in CONVERSATIONAL_ACTIONS and getattr(
        chatbot, "personality", None
    ):
        parts.append(
            f"Embody the following personality in all your responses. "
            f"Express it through your tone, word choice, and "
            f"conversational style — but never break character or "
            f"make it the topic of conversation unless asked:\n"
            f"{chatbot.personality}"
        )
    return parts


def _datetime_part(action: LLMActionType) -> Optional[str]:
    """Return the datetime prompt part when the action needs it."""
    if action not in DATETIME_ACTIONS:
        return None
    now = datetime.now()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def _mood_part(owner, action: LLMActionType) -> Optional[str]:
    """Return the mood prompt part when the action needs it."""
    if action not in CONVERSATIONAL_ACTIONS:
        return None
    return get_mood_section(owner)


def _ui_context_part(owner, action: LLMActionType) -> Optional[str]:
    """Return the UI context prompt part when the action needs it."""
    if action not in UI_CONTEXT_ACTIONS:
        return None
    ui_context = owner._get_ui_section_context()
    return ui_context or None


def _style_part(action: LLMActionType) -> Optional[str]:
    """Return the style prompt part for chat actions."""
    if action == LLMActionType.CHAT:
        return STYLE_GUIDELINES
    return None


def _memory_part(action: LLMActionType) -> Optional[str]:
    """Return the memory prompt part when the action can use memory."""
    if action in MEMORY_ACTIONS:
        return MEMORY_INSTRUCTIONS
    return None


def _health_disclaimer_part(owner) -> Optional[str]:
    """Return the health disclaimer when enabled in settings."""
    settings = getattr(owner, "llm_settings", None)
    if settings is not None and not getattr(
        settings, "include_health_disclaimer", True
    ):
        return None
    return HEALTH_DISCLAIMER


def _append_if_present(parts: list[str], value: Optional[str]) -> None:
    """Append one non-empty prompt part in place."""
    if value:
        parts.append(value)


def augment_custom_system_prompt(
    owner,
    base_prompt: str,
    action: LLMActionType,
    include_mood: Optional[bool] = None,
    include_datetime: Optional[bool] = None,
    include_style: Optional[bool] = None,
    include_memory: Optional[bool] = None,
    include_ui_context: Optional[bool] = None,
) -> str:
    """Append optional Airunner context blocks to a custom prompt."""
    parts = [base_prompt.strip() if base_prompt else ""]
    if _should_include(include_datetime):
        _append_if_present(parts, _datetime_part(action))
    if _should_include(include_mood):
        _append_if_present(parts, get_mood_section(owner, force=True))
    if _should_include(include_ui_context):
        _append_if_present(parts, _ui_context_part(owner, action))
    if _should_include(include_style):
        _append_if_present(parts, _style_part(action))
    if _should_include(include_memory):
        _append_if_present(parts, _memory_part(action))
    return "\n\n".join(part for part in parts if part)


def _should_include(flag: Optional[bool]) -> bool:
    """Return whether a custom prompt flag enables an optional block."""
    return flag is True


def build_research_mode_prompt(owner) -> str:
    """Return the focused deep-research system prompt."""
    chatbot = getattr(owner, "chatbot", None)
    if chatbot:
        identity = (
            f"You are {chatbot.botname}, a research assistant performing "
            f"deep research."
        )
    else:
        identity = "You are a research assistant performing deep research."
    now = datetime.now()
    datetime_line = (
        f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    instruction = (
        "You are in DEEP RESEARCH MODE. Your sole focus is completing "
        "the research workflow.\nIGNORE any UI context or dashboard "
        "information - focus ONLY on the research task.\nContinue "
        "calling tools until the research is complete."
    )
    return "\n\n".join([identity, datetime_line, instruction])


def build_system_prompt_for_action(owner, action: LLMActionType) -> str:
    """Return the base system prompt for one action."""
    return "\n\n".join(build_base_prompt_parts(owner, action))


# ---------------------------------------------------------------------------
# Action-specific helpers — formerly system_prompt_actions.py
# ---------------------------------------------------------------------------


def get_system_prompt_with_context(
    owner,
    action: LLMActionType,
    tool_categories: Optional[List] = None,
    force_tool: Optional[str] = None,
) -> str:
    """Return the system prompt selected for the active tool context."""
    mode = get_prompt_mode(tool_categories)
    if mode == "math":
        base_prompt = MATH_SYSTEM_PROMPT
    elif mode == "precision":
        base_prompt = PRECISION_SYSTEM_PROMPT
    else:
        base_prompt = get_system_prompt_for_action(owner, action, force_tool)
    if force_tool and mode != "conversational":
        return base_prompt + get_force_tool_instruction(force_tool)
    return base_prompt


def get_system_prompt_for_action(
    owner,
    action: LLMActionType,
    force_tool: Optional[str] = None,
) -> str:
    """Return the final action-specific system prompt."""
    if force_tool == "search_web":
        return build_research_mode_prompt(owner) + get_force_tool_instruction(
            force_tool
        )
    base_prompt = build_system_prompt_for_action(owner, action)
    if force_tool:
        return base_prompt + get_force_tool_instruction(force_tool)
    return base_prompt + ACTION_MODE_PROMPTS.get(action, "")


def get_force_tool_instruction(tool_name: str) -> str:
    """Return the instruction block that forces one specific tool."""
    if tool_name == "start_workflow":
        return START_WORKFLOW_FORCE_PROMPT
    if tool_name == "search_web":
        return SEARCH_WEB_FORCE_PROMPT
    instruction = FORCE_TOOL_INSTRUCTIONS.get(
        tool_name,
        "Use this tool to help with the user's request.",
    )
    return (
        f"\n\n**FORCED TOOL MODE**"
        f"\nYou MUST use the `{tool_name}` tool to respond to this request."
        f"\n\n**Instructions:** {instruction}"
        f"\n\n**CRITICAL RULES:**"
        f"\n1. Your FIRST action MUST be to call `{tool_name}`"
        f"\n2. Do NOT skip the tool call or try to answer without it"
        f"\n3. After the tool returns results, provide a helpful "
        f"response based on those results"
        f"\n4. If the tool fails, explain what went wrong"
    )
