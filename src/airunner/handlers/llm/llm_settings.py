import os
from dataclasses import dataclass

# Try to load environment variables from .env file
# This is mainly for development; in production, env vars should be set 
# in the environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is not installed, continue without it
    # environment variables will be read directly from the OS
    pass

from airunner.settings import (
    AIRUNNER_LLM_USE_LOCAL,
    AIRUNNER_LLM_USE_OPENROUTER,
    AIRUNNER_LLM_OPENROUTER_API_KEY,
    AIRUNNER_LLM_USE_OPENAI,
    AIRUNNER_LLM_OPENAI_API_KEY,
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
    use_local_llm: bool = AIRUNNER_LLM_USE_LOCAL
    use_weather_prompt: bool = AIRUNNER_LLM_USE_WEATHER_PROMPT,
    update_mood_after_n_turns: int = AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS
    summarize_after_n_turns: int = AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS
    use_openrouter: bool = AIRUNNER_LLM_USE_OPENROUTER
    openrouter_api_key: str = AIRUNNER_LLM_OPENROUTER_API_KEY
    use_openai: bool = AIRUNNER_LLM_USE_OPENAI
    openai_api_key: str = AIRUNNER_LLM_OPENAI_API_KEY
    perform_conversation_summary: bool = AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY
    max_function_calls: int = AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS
    model: str = AIRUNNER_LLM_OPENROUTER_MODEL
    print_llm_system_prompt: bool = AIRUNNER_LLM_PRINT_SYSTEM_PROMPT
    llm_perform_analysis: bool = AIRUNNER_LLM_PERFORM_ANALYSIS
    update_user_data_enabled: bool = AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED
    use_chatbot_mood: bool = AIRUNNER_LLM_USE_CHATBOT_MOOD
    perform_conversation_rag: bool = AIRUNNER_LLM_PERFORM_CONVERSATION_RAG

    @property
    def use_api(self) -> bool:
        return (
            self.use_openrouter or
            self.use_openai
        )
