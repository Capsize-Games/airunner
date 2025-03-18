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
    USE_LOCAL_LLM_DEFAULT,
    USE_OPENROUTER_DEFAULT,
    OPENROUTER_API_KEY_DEFAULT,
    USE_OPENAI_DEFAULT,
    OPENAI_API_KEY_DEFAULT,
)


@dataclass
class LLMSettings:
    use_local_llm: bool = USE_LOCAL_LLM_DEFAULT
    
    use_open_router: bool = USE_OPENROUTER_DEFAULT
    open_router_api_key: str = OPENROUTER_API_KEY_DEFAULT
    
    use_openai: bool = USE_OPENAI_DEFAULT
    openai_api_key: str = OPENAI_API_KEY_DEFAULT

    model: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_local_llm = os.getenv(
            "AIRUNNER_USE_LOCAL_LLM", 
            "1" if self.use_local_llm else "0"
        ) == "1"
        self.use_open_router = os.getenv(
            "AIRUNNER_USE_OPEN_ROUTER", 
            "1" if self.use_open_router else "0"
        ) == "1"
        self.open_router_api_key = os.getenv(
            "AIRUNNER_OPENROUTER_API_KEY", 
            self.open_router_api_key
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
