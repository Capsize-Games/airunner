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
    AIRUNNER_USE_LOCAL_LLM,
    AIRUNNER_USE_OPENROUTER,
    AIRUNNER_OPENROUTER_API_KEY,
    AIRUNNER_USE_OPENAI,
    AIRUNNER_OPENAI_API_KEY,
)


@dataclass
class LLMSettings:
    use_local_llm: bool = AIRUNNER_USE_LOCAL_LLM
    use_openrouter: bool = AIRUNNER_USE_OPENROUTER
    openrouter_api_key: str = AIRUNNER_OPENROUTER_API_KEY
    use_openai: bool = AIRUNNER_USE_OPENAI
    openai_api_key: str = AIRUNNER_OPENAI_API_KEY
    model: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_local_llm = os.getenv(
            "AIRUNNER_USE_LOCAL_LLM", 
            "1" if self.use_local_llm else "0"
        ) == "1"
        self.use_openrouter = os.getenv(
            "AIRUNNER_USE_OPENROUTER", 
            "1" if self.use_openrouter else "0"
        ) == "1"
        self.openrouter_api_key = os.getenv(
            "AIRUNNER_OPENROUTER_API_KEY", 
            self.openrouter_api_key
        )
        self.use_openai = os.getenv(
            "AIRUNNER_USE_OPENAI", 
            "1" if self.use_openai else "0"
        ) == "1"
        self.openai_api_key = os.getenv(
            "AIRUNNER_OPENAI_API_KEY", 
            self.openai_api_key
        )
        self.model = os.getenv(
            "AIRUNNER_LLM_MODEL", 
            self.model
        )
    
    @property
    def use_api(self) -> bool:
        return (
            self.use_openrouter or
            self.use_openai
        )
