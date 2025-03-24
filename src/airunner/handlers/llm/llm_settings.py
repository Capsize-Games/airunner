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
)


@dataclass
class LLMSettings:
    use_local_llm: bool = AIRUNNER_LLM_USE_LOCAL
    use_openrouter: bool = AIRUNNER_LLM_USE_OPENROUTER
    openrouter_api_key: str = AIRUNNER_LLM_OPENROUTER_API_KEY
    use_openai: bool = AIRUNNER_LLM_USE_OPENAI
    openai_api_key: str = AIRUNNER_LLM_OPENAI_API_KEY
    perform_conversation_summary: bool = AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY
    model: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = os.getenv(
            "AIRUNNER_LLM_OPENROUTER_MODEL", 
            self.model
        )
    
    @property
    def use_api(self) -> bool:
        return (
            self.use_openrouter or
            self.use_openai
        )
