import os
from dataclasses import dataclass

# Try to load environment variables from .env file
# This is mainly for development; in production, env vars should be set in the environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is not installed, continue without it
    # environment variables will be read directly from the OS
    pass

@dataclass
class LLMSettings:
    use_local_llm: bool = False
    use_open_router: bool = False
    open_router_api_key: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_router_api_key = os.getenv(
            "OPENROUTER_API_KEY", 
            self.open_router_api_key
        )
        self.use_local_llm = os.getenv(
            "AIRUNNER_USE_LOCAL_LLM", 
            "1" if self.use_local_llm else "0"
        ) == "1"
        self.use_open_router = os.getenv(
            "AIRUNNER_USE_OPEN_ROUTER", 
            "1" if self.use_open_router else "0"
        ) == "1"
