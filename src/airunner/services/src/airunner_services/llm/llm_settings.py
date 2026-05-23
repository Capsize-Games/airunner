"""Service-owned settings for Large Language Model functionality."""

import os
from dataclasses import dataclass

if os.environ.get("DEV_ENV", "1") == "1":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

from airunner_services.settings import (
    AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS,
    AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS,
    AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS,
    AIRUNNER_LLM_OPENROUTER_MODEL,
    AIRUNNER_LLM_PERFORM_ANALYSIS,
    AIRUNNER_LLM_PERFORM_CONVERSATION_RAG,
    AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY,
    AIRUNNER_LLM_PRINT_SYSTEM_PROMPT,
    AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED,
    AIRUNNER_LLM_USE_CHATBOT_MOOD,
    AIRUNNER_LLM_USE_WEATHER_PROMPT,
)


@dataclass
class LLMSettings:
    """Configuration options for local and API-backed LLM usage."""

    use_weather_prompt: bool = AIRUNNER_LLM_USE_WEATHER_PROMPT
    update_mood_after_n_turns: int = (
        AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS
    )
    summarize_after_n_turns: int = AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS
    perform_conversation_summary: bool = (
        AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY
    )
    max_function_calls: int = AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS
    model: str = AIRUNNER_LLM_OPENROUTER_MODEL
    print_llm_system_prompt: bool = AIRUNNER_LLM_PRINT_SYSTEM_PROMPT
    llm_perform_analysis: bool = AIRUNNER_LLM_PERFORM_ANALYSIS
    update_user_data_enabled: bool = AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED
    use_chatbot_mood: bool = AIRUNNER_LLM_USE_CHATBOT_MOOD
    perform_conversation_rag: bool = AIRUNNER_LLM_PERFORM_CONVERSATION_RAG
    auto_extract_knowledge: bool = True

    core_facts_count: int = 10
    rag_facts_count: int = 5
    use_rag_for_facts: bool = True

    use_local_llm: bool = True
    use_openrouter: bool = False
    use_ollama: bool = False
    use_openai: bool = False

    use_yarn: bool = False
    yarn_target_context: int = 0

    enable_thinking: bool = True

    ollama_model: str = "llama2"
    ollama_base_url: str = "http://localhost:11434"

    openai_model: str = "gpt-4"

    @property
    def use_api(self) -> bool:
        """Return whether any remote API backend is active."""
        return bool(
            getattr(self, "use_openrouter", False)
            or getattr(self, "use_openai", False)
            or getattr(self, "use_ollama", False)
        )


AIRUNNER_LLM_USE_OPENAI = False


__all__ = ["AIRUNNER_LLM_USE_OPENAI", "LLMSettings"]