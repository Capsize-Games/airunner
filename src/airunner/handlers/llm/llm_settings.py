import os
from dataclasses import dataclass

# Try to load environment variables from .env file
# This is mainly for development; in production, env vars should be set
# in the environment
if os.environ.get("DEV_ENV", "1") == "1":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        # python-dotenv is not installed, continue without it
        # environment variables will be read directly from the OS
        pass

from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.settings import (
    AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY,
    AIRUNNER_LLM_USE_WEATHER_PROMPT,
    AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS,
    AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS,
    AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS,
    AIRUNNER_LLM_OPENROUTER_MODEL,
    AIRUNNER_LLM_PRINT_SYSTEM_PROMPT,
    AIRUNNER_LLM_PERFORM_ANALYSIS,
    AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED,
    AIRUNNER_LLM_USE_CHATBOT_MOOD,
    AIRUNNER_LLM_PERFORM_CONVERSATION_RAG,
)


@dataclass
class LLMSettings:
    """
    Settings for Large Language Model functionality.
    Contains configuration options for local and API-based LLM usage.
    """

    use_weather_prompt: bool = (
        AIRUNNER_LLM_USE_WEATHER_PROMPT  # Fixed trailing comma
    )
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
