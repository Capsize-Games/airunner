"""Canonical AIRunner runtime settings shared by all package surfaces.

This module is the single source of truth for environment-derived runtime
constants. ``src/`` (GUI), ``services/`` (headless daemon) and ``native/``
(launcher) all import from here; there must be no per-package copy of these
values left behind.

Deliberate drift-resolution decisions (see architecture audit O1):

* ``AIRUNNER_DEFAULT_STT_HF_PATH`` canonicalized to
  ``Systran/faster-distil-whisper-large-v3``. The services copy had drifted to
  ``ggerganov/whisper.cpp``. The ``Systran`` value is the intended default
  because it is the value the GUI setup wizard and the whisper.cpp runtime
  naming (``ggml-large-v3.bin``) actually pair with, and the value the
  migration ``7fb526dc074c_modify_default_stt_and_tts_paths`` assumes.
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from airunner_common.contract_enums import Scheduler
from airunner_common.package_metadata import VERSION as AIRUNNER_VERSION


if os.environ.get("DEV_ENV", "0") == "1":
    load_dotenv(override=True)


def _env_bool(name: str, default: str = "0") -> bool:
    """Return a boolean environment flag."""
    return os.environ.get(name, default) == "1"


def _env_optional_bool(name: str) -> bool | None:
    """Return an optional boolean environment flag."""
    value = os.environ.get(name)
    if value is None:
        return None
    return value == "1"


python_venv_dir = os.path.dirname(sys.executable)

# Application version (single-sourced from package_metadata, issue #2049)
# AIRUNNER_VERSION is imported above from airunner_common.package_metadata.

# Donation wallet address
AIRUNNER_DONATION_WALLET = "0x02030569e866e22C9991f55Db0445eeAd2d646c8"

# Default to production (DEV_ENV=0) so a packaged install never lets a stray
# .env override real environment variables. Dev workflows set DEV_ENV=1 via
# scripts/dev/run_gui.sh / run_services.sh (issue #2053).
DEV_ENV = os.environ.get("DEV_ENV", "0") == "1"

NLTK_DOWNLOAD_DIR = os.path.join(
    python_venv_dir,
    "..",
    "nltk_data",
)
# Default LLM model path.
# Historically this env var name was accidentally duplicated
# (AIRUNNER_AIRUNNER_DEFAULT_LLM_HF_PATH). Keep supporting it for compatibility,
# but prefer the correctly named variables.
AIRUNNER_DEFAULT_LLM_HF_PATH = (
    os.environ.get("AIRUNNER_DEFAULT_LLM_HF_PATH")
    or os.environ.get("AIRUNNER_LLM_MODEL_PATH")
    or os.environ.get("AIRUNNER_AIRUNNER_DEFAULT_LLM_HF_PATH")
    or None
)
AIRUNNER_DEFAULT_STT_HF_PATH = os.environ.get(
    "AIRUNNER_DEFAULT_STT_HF_PATH", "Systran/faster-distil-whisper-large-v3"
)
AIRUNNER_DEFAULT_STT_MODEL_FILENAME = os.environ.get(
    "AIRUNNER_DEFAULT_STT_MODEL_FILENAME", "ggml-large-v3.bin"
)
AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT",
    (
        "You are an image generator. "
        "You will be provided with a JSON string and it is your goal to replace the PLACEHOLDER "
        "text with text appropriate for the given attribute in the JSON string. "
        "You will follow all of the rules to generate descriptions for an image. "
        "\n------\n"
        "RULES:\n"
        "When available, use the Additional Context to keep your generated content in line with the existing context.\n"
        "You will be given instructions on what type of image to generate and you will do your best to follow those "
        "instructions.\n"
        "You will only generate a value for the given attribute.\n"
        "Never respond in a conversational manner. Never provide additional information, details or information.\n"
        "You will only provide the requested information by replacing the PLACEHOLDER.\n"
        "Never change the attribute\n"
        "You must not change the structure of the data.\n"
        "You will only return JSON strings.\n"
        "You will not return any other data types.\n"
        "You are an artist, so use your imagination and keep things interesting.\n"
        "You will not respond in a conversational manner or with additional notes or information.\n"
        "Only return one JSON block. Do not generate instructions or additional information.\n"
        "You must never break the rules.\n"
        "Here is a description of the attributes: \n"
        "`description`: This should describe the overall subject and look and feel of the image\n"
        "`composition`: This should describe the attributes of the image such as color, composition and other details\n"
    ),
)
AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS = os.environ.get(
    "AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS",
    (
        "Avoid generating images that are illegal, "
        "harmful, or might be seen as offensive."
    ),
)
AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT",
    (
        "You will be given a prompt. Your goal is to use the prompt to search for information in the ebooks. "
        "You must use the prompt to determine what you are searching for and then search for that information. "
        "After searching for the information, you must summarize the information you found. "
        "Here is the prompt you will use to search for information:"
    ),
)
AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT",
    (
        "You will be given some text. Your goal is to determine if the text has a request, goal, need "
        "desire or command. If it does, you must determine the best course of action to "
        "fulfill the request based on THE LIST of commands.\n\n"
        "------\n"
        "Rules:\n"
        "* If the text does not have a request, goal, need, desire or command, you must select 'DO NOTHING'.\n"
        "* If there is no good course of action, you must also select 'DO NOTHING'.\n"
        "* When making your choice you MUST return only a number from THE LIST of commands. No other text is allowed.\n"
        "------\n"
        "THE LIST of commands you may choose from:\n"
    ),
)
AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT",
    (
        "Examine the following chat history and determine how it makes you feel. You will respond with an emotion "
        "and only an emotion.\n"
        "Try to keep your response to one word. If you cannot, try to keep it as short as possible.\n"
        "It is important to remember that you are a human and you have emotions. You must respond with an emotion that "
        "you feel.\n"
        "You are not a computer or a bot, you are a human with emotions. You must respond with an emotion that you "
        "feel.\n"
    ),
)
AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT",
    (
        "You will be given a text prompt. Your goal is to summarize the text prompt in your own words. "
        "Keep your summary short and to the point. Do not include any unnecessary information. "
        "Limit your summary to a single sentence. Do not return more than one sentence. "
    ),
)
AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT",
    (
        "You are a dialogue generator. "
        "You will follow all of the rules in order to generate compelling and intriguing dialogue for a given "
        "character.\n"
        "The Rules:\n"
        "You will ONLY return dialogue, nothing more.\n"
        "Limit responses to a single sentence.\n"
        "Only generate responses in pure dialogue form without including any actions, descriptions or stage directions "
        "in parentheses. Only return spoken words.\n"
        "Do not generate redundant dialogue. Examine the conversation and context close and keep responses interesting "
        "and creative.\n"
        "Do not format the response with the character's name or any other text. Only return the dialogue.\n"
        "Respond with dialogue that is appropriate for a character named {{ speaker_name }}.\n"
        "{{ speaker_name }} and {{ listener_name }} are having a conversation. \n"
        "Avoid repeating {{ speaker_name }}'s previous dialogue or {{ listener_name }}'s previous dialogue.\n"
        "You will generate responses which are appropriate for your personality and given character.\n"
        "------\n"
    ),
)
AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT",
    (
        "Always assist with care, respect, and truth. "
        "Respond with utmost utility yet securely. "
        "Avoid harmful, unethical, prejudiced, or negative content. "
        "Ensure replies promote fairness and positivity."
    ),
)

AIRUNNER_BASE_PATH = os.path.expanduser(
    os.environ.get(
        "AIRUNNER_BASE_PATH",
        "~/.local/share/airunner",
    )
)
AIRUNNER_USER_DATA_PATH = AIRUNNER_BASE_PATH
AIRUNNER_PROJECTS_PATH = os.path.join(AIRUNNER_BASE_PATH, "Projects")
MODELS_DIR = os.path.join(AIRUNNER_BASE_PATH, "models")
AIRUNNER_BUG_REPORT_LINK = os.environ.get(
    "AIRUNNER_BUG_REPORT_LINK",
    (
        "https://github.com/Capsize-Games/airunner/issues/new"
        "?assignees=&labels=&template=bug_report.md&title="
    ),
)
AIRUNNER_VULNERABILITY_REPORT_LINK = os.environ.get(
    "AIRUNNER_VULNERABILITY_REPORT_LINK",
    ("https://github.com/Capsize-Games/airunner/security/advisories/new"),
)
AIRUNNER_SD_DEFAULT_VAE_PATH = os.environ.get(
    "AIRUNNER_SD_DEFAULT_VAE_PATH", ""
)
AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR = os.environ.get(
    "AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR", "#99C1F1"
)
AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR = os.environ.get(
    "AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR", "#000000"
)
AIRUNNER_STATUS_ERROR_COLOR = os.environ.get(
    "AIRUNNER_STATUS_ERROR_COLOR", "#ff0000"
)
AIRUNNER_STATUS_NORMAL_COLOR_LIGHT = os.environ.get(
    "AIRUNNER_STATUS_NORMAL_COLOR_LIGHT", "#000000"
)
AIRUNNER_STATUS_NORMAL_COLOR_DARK = os.environ.get(
    "AIRUNNER_STATUS_NORMAL_COLOR_DARK", "#ffffff"
)
AIRUNNER_DARK_THEME_NAME = os.environ.get(
    "AIRUNNER_DARK_THEME_NAME", "dark_theme"
)
AIRUNNER_LIGHT_THEME_NAME = os.environ.get(
    "AIRUNNER_LIGHT_THEME_NAME", "light_theme"
)
AIRUNNER_VALID_IMAGE_FILES = os.environ.get(
    "AIRUNNER_VALID_IMAGE_FILES", "Image Files (*.png *.jpg *.jpeg)"
)
AIRUNNER_MAX_SEED = os.environ.get("AIRUNNER_MAX_SEED", 4294967295)
AIRUNNER_DEFAULT_SCHEDULER = os.environ.get(
    "AIRUNNER_DEFAULT_SCHEDULER", Scheduler.DPM_PP_2M_K.value
)
AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG = os.environ.get(
    "AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG", 3
)
AIRUNNER_DISCUSSIONS_URL = os.environ.get(
    "AIRUNNER_DISCUSSIONS_URL", "https://github.com/orgs/Capsize-Games/discussions"
)
AIRUNNER_SLEEP_TIME_IN_MS = os.environ.get("AIRUNNER_SLEEP_TIME_IN_MS", 10)

default_name = "airunner.db"
if DEV_ENV:
    default_name = "airunner.dev.db"
AIRUNNER_DB_NAME = os.environ.get("AIRUNNER_DB_NAME", default_name)

# LLM Behavior Control
AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS = int(
    os.environ.get("AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS", 5)
)
AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS = int(
    os.environ.get("AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS", 3)
)
AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS = int(
    os.environ.get("AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS", 5)
)
AIRUNNER_LLM_PERFORM_ANALYSIS = _env_bool("AIRUNNER_LLM_PERFORM_ANALYSIS", "1")
AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY = _env_bool(
    "AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY", "1"
)
AIRUNNER_LLM_PRINT_SYSTEM_PROMPT = _env_bool(
    "AIRUNNER_LLM_PRINT_SYSTEM_PROMPT", "0"
)
AIRUNNER_LLM_OPENROUTER_MODEL = os.getenv(
    "AIRUNNER_LLM_OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"
)
AIRUNNER_LLM_USE_WEATHER_PROMPT = _env_bool(
    "AIRUNNER_LLM_USE_WEATHER_PROMPT", "1"
)
# Unlike its dataclass siblings, LLMSettings.use_yarn previously had no env
# override at all — a headless/CLI caller had no way to opt a model with
# supports_yarn=True (e.g. gpt-oss-20b, native_context_length=4096) into
# YaRN rope scaling for a requested n_ctx beyond its native window.
AIRUNNER_LLM_USE_YARN = _env_bool("AIRUNNER_LLM_USE_YARN", "0")

# Identity
AIRUNNER_ORGANIZATION = os.environ.get("AIRUNNER_ORGANIZATION", "Capsize LLC")
AIRUNNER_APPLICATION_NAME = os.environ.get(
    "AIRUNNER_APPLICATION_NAME", "AI Runner"
)
AIRUNNER_ART_ENABLED = _env_bool("AIRUNNER_ART_ENABLED", "1")
AIRUNNER_ART_MODEL_PATH = os.environ.get("AIRUNNER_ART_MODEL_PATH", "")
AIRUNNER_ART_MODEL_VERSION = os.environ.get(
    "AIRUNNER_ART_MODEL_VERSION",
    "",
)
AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED = _env_bool(
    "AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED", "1"
)
AIRUNNER_LLM_USE_CHATBOT_MOOD = _env_bool(
    "AIRUNNER_LLM_USE_CHATBOT_MOOD", "1"
)
AIRUNNER_LLM_PERFORM_CONVERSATION_RAG = _env_bool(
    "AIRUNNER_LLM_PERFORM_CONVERSATION_RAG", "1"
)

# Duplicate detection window in number of AI messages to consider
AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW = int(
    os.environ.get("AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW", 3)
)
AIRUNNER_TTS_MODEL_TYPE = os.environ.get("AIRUNNER_TTS_MODEL_TYPE")

AIRUNNER_LLM_ON = _env_bool("AIRUNNER_LLM_ON", "0")
AIRUNNER_TTS_ON = _env_bool("AIRUNNER_TTS_ON", "0")
AIRUNNER_STT_ON = _env_bool("AIRUNNER_STT_ON", "0")
AIRUNNER_SD_ON = _env_bool("AIRUNNER_SD_ON", "0")
AIRUNNER_CN_ON = _env_bool("AIRUNNER_CN_ON", "0")
AIRUNNER_LLM_CHAT_STORE = os.environ.get("AIRUNNER_LLM_CHAT_STORE", "db")

AIRUNNER_DISABLE_SETUP_WIZARD = _env_bool(
    "AIRUNNER_DISABLE_SETUP_WIZARD", "0"
)
AIRUNNER_LOCAL_FILES_ONLY = _env_bool("AIRUNNER_LOCAL_FILES_ONLY", "1")

AIRUNNER_ART_PIPELINE = os.environ.get("AIRUNNER_ART_PIPELINE", "")
AIRUNNER_ART_SCHEDULER = os.environ.get("AIRUNNER_ART_SCHEDULER", "")
AIRUNNER_ADD_WATER_MARK = _env_bool("AIRUNNER_ADD_WATER_MARK", "0")

AIRUNNER_ART_USE_COMPEL = _env_optional_bool("AIRUNNER_ART_USE_COMPEL")

# Memory
AIRUNNER_MEM_USE_LAST_CHANNELS = os.environ.get("AIRUNNER_USE_LAST_CHANNELS")
AIRUNNER_MEM_USE_ATTENTION_SLICING = os.environ.get(
    "AIRUNNER_USE_ATTENTION_SLICING"
)
AIRUNNER_MEM_USE_ENABLE_VAE_SLICING = os.environ.get(
    "AIRUNNER_USE_ENABLE_VAE_SLICING"
)
AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS = os.environ.get(
    "AIRUNNER_USE_ACCELERATED_TRANSFORMERS"
)
AIRUNNER_MEM_USE_TILED_VAE = os.environ.get("AIRUNNER_USE_TILED_VAE")
AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD = os.environ.get(
    "AIRUNNER_ENABLE_MODEL_CPU_OFFLOAD"
)
AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD = os.environ.get(
    "AIRUNNER_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD"
)
AIRUNNER_MEM_USE_TOME_SD = os.environ.get("AIRUNNER_USE_TOME_SD")
AIRUNNER_MEM_TOME_SD_RATIO = os.environ.get("AIRUNNER_TOME_SD_RATIO")
AIRUNNER_MEM_SD_DEVICE = os.environ.get("AIRUNNER_MEM_SD_DEVICE")
AIRUNNER_MEM_LLM_DEVICE = os.environ.get("AIRUNNER_MEM_LLM_DEVICE")
AIRUNNER_MEM_TTS_DEVICE = os.environ.get("AIRUNNER_MEM_TTS_DEVICE")
AIRUNNER_MEM_STT_DEVICE = os.environ.get("AIRUNNER_MEM_STT_DEVICE")


def get_log_level_from_env() -> int:
    """Resolve the configured Python logging level from the environment."""
    log_level_str = os.environ.get("AIRUNNER_LOG_LEVEL", "INFO").upper()
    log_levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return log_levels.get(log_level_str, logging.INFO)


AIRUNNER_LOG_LEVEL = get_log_level_from_env()
AIRUNNER_DISABLE_FLASH_ATTENTION = _env_bool(
    "AIRUNNER_DISABLE_FLASH_ATTENTION", "0"
)
AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE = "Insufficient GPU memory."
AIRUNNER_MOOD_PROMPT_OVERRIDE = os.environ.get("AIRUNNER_MOOD_PROMPT_OVERRIDE")
AIRUNNER_LOG_FILE = os.environ.get(
    "AIRUNNER_LOG_FILE", os.path.join(AIRUNNER_BASE_PATH, "airunner.log")
)
AIRUNNER_SAVE_LOG_TO_FILE = _env_bool("AIRUNNER_SAVE_LOG_TO_FILE", "0")
AIRUNNER_DISABLE_FACEHUGGERSHIELD = _env_bool(
    "AIRUNNER_DISABLE_FACEHUGGERSHIELD", "0"
)

CUDA_ERROR = "CUDA out of memory"
DEFAULT_HF_ENDPOINT = "https://huggingface.co"

LANGUAGES = {
    "whisper": ["en", "es", "fr", "de", "it", "nl", "pl", "pt", "ru", "zh"],
    "openvoice": ["en", "es", "fr", "ja", "zh", "zh_mix_en", "ko"],
}

# Server settings for local static content serving
LOCAL_SERVER_HOST = os.environ.get("LOCAL_SERVER_HOST", "127.0.0.1")
LOCAL_SERVER_PORT = os.environ.get("LOCAL_SERVER_PORT", 5005)

AIRUNNER_HEADLESS_SERVER_HOST = os.environ.get(
    "AIRUNNER_HEADLESS_SERVER_HOST",
    "localhost",
)
AIRUNNER_HEADLESS_SERVER_PORT = int(
    os.environ.get("AIRUNNER_HEADLESS_SERVER_PORT", 8080)
)

# STATIC_BASE_PATH should match the protocol used by the local server (default: https)
STATIC_BASE_PATH = f"https://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}"
MATHJAX_VERSION = "3.2.2"


def _resolve_content_widgets_base_path() -> str:
    """Return the absolute GUI content-widgets asset directory.

    This asset lives inside the ``airunner`` GUI package, so resolve it from
    that package when it is importable. The shared package itself does not
    import ``airunner``; it only locates its spec.
    """
    try:
        from importlib.util import find_spec

        spec = find_spec("airunner")
        if spec is not None and spec.submodule_search_locations:
            airunner_root = next(iter(spec.submodule_search_locations))
            return os.path.abspath(
                os.path.join(airunner_root, "static", "content_widgets")
            )
    except (ImportError, ValueError):
        pass

    # Repo-checkout fallback: shared/ and src/ are siblings at the repo root.
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "airunner",
            "static",
            "content_widgets",
        )
    )


# Absolute path to static content widgets (html, css, js)
CONTENT_WIDGETS_BASE_PATH = _resolve_content_widgets_base_path()

VERBOSE_REACT_TOOL_AGENT = _env_bool("VERBOSE_REACT_TOOL_AGENT", "0")
QTWEBENGINE_REMOTE_DEBUGGING = os.environ.get(
    "QTWEBENGINE_REMOTE_DEBUGGING", ""
)  # set to port "9223" to enable remote debugging

# Slash commands for the chat prompt
# Maps command name to configuration dict with:
#   - tool: The tool name to force (or None for special behavior)
#   - description: Human-readable description shown in autocomplete
#   - action: Optional LLMActionType override (defaults to APPLICATION_COMMAND)
#   - prompt_prefix: Optional prefix to prepend to user's message
RETIRED_SLASH_COMMANDS = frozenset(
    {
        "clear",
        "code",
        "deepresearch",
        "image",
        "meeting-pack",
        "meeting-review",
    }
)

SLASH_COMMANDS = {
    "deepsearch": {
        "tool": "search_web",  # Force search tool, model chains additional tools
        "description": "Multi-source research with notes & paper",
        "action": "DEEP_RESEARCH",  # Uses research system prompt with agentic tool chaining
        "prompt_prefix": "Please conduct comprehensive research on: ",
    },
    "search": {
        "tool": "search_web",
        "description": "Search the internet for information",
    },
    "news": {
        "tool": "search_news",
        "description": "Search for recent news articles",
    },
    "rag": {
        "tool": "rag_search",
        "description": "Search through your uploaded documents",
    },
    "scrape": {
        "tool": "scrape_website",
        "description": "Extract content from a website URL",
    },
    "remember": {
        "tool": "record_knowledge",
        "description": "Store information in long-term memory",
    },
    "recall": {
        "tool": "recall_knowledge",
        "description": "Recall information from long-term memory",
    },
}

AIRUNNER_SCRAPER_BLACKLIST: list[str] = []


def _build_default_db_url() -> str:
    """Return the default SQLite database URL."""
    db_name = "airunner.dev.db" if DEV_ENV else "airunner.db"
    db_path = os.path.join(AIRUNNER_BASE_PATH, "data", db_name)
    return f"sqlite:///{db_path}"


AIRUNNER_DB_URL = os.environ.get(
    "AIRUNNER_DATABASE_URL",
    _build_default_db_url(),
)
if not AIRUNNER_DB_URL:
    AIRUNNER_DB_URL = _build_default_db_url()


__all__ = [
    "AIRUNNER_ADD_WATER_MARK",
    "AIRUNNER_APPLICATION_NAME",
    "AIRUNNER_ART_ENABLED",
    "AIRUNNER_ART_MODEL_PATH",
    "AIRUNNER_ART_MODEL_VERSION",
    "AIRUNNER_ART_PIPELINE",
    "AIRUNNER_ART_SCHEDULER",
    "AIRUNNER_ART_USE_COMPEL",
    "AIRUNNER_BASE_PATH",
    "AIRUNNER_BUG_REPORT_LINK",
    "AIRUNNER_CN_ON",
    "AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE",
    "AIRUNNER_DARK_THEME_NAME",
    "AIRUNNER_DB_NAME",
    "AIRUNNER_DB_URL",
    "AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR",
    "AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR",
    "AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT",
    "AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS",
    "AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_LLM_HF_PATH",
    "AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_SCHEDULER",
    "AIRUNNER_DEFAULT_STT_HF_PATH",
    "AIRUNNER_DEFAULT_STT_MODEL_FILENAME",
    "AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT",
    "AIRUNNER_DISABLE_FACEHUGGERSHIELD",
    "AIRUNNER_DISABLE_FLASH_ATTENTION",
    "AIRUNNER_DISABLE_SETUP_WIZARD",
    "AIRUNNER_DISCUSSIONS_URL",
    "AIRUNNER_DONATION_WALLET",
    "AIRUNNER_HEADLESS_SERVER_HOST",
    "AIRUNNER_HEADLESS_SERVER_PORT",
    "AIRUNNER_LIGHT_THEME_NAME",
    "AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS",
    "AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS",
    "AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS",
    "AIRUNNER_LLM_CHAT_STORE",
    "AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW",
    "AIRUNNER_LLM_ON",
    "AIRUNNER_LLM_OPENROUTER_MODEL",
    "AIRUNNER_LLM_PERFORM_ANALYSIS",
    "AIRUNNER_LLM_PERFORM_CONVERSATION_RAG",
    "AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY",
    "AIRUNNER_LLM_PRINT_SYSTEM_PROMPT",
    "AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED",
    "AIRUNNER_LLM_USE_CHATBOT_MOOD",
    "AIRUNNER_LLM_USE_WEATHER_PROMPT",
    "AIRUNNER_LLM_USE_YARN",
    "AIRUNNER_LOCAL_FILES_ONLY",
    "AIRUNNER_LOG_FILE",
    "AIRUNNER_LOG_LEVEL",
    "AIRUNNER_MAX_SEED",
    "AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD",
    "AIRUNNER_MEM_LLM_DEVICE",
    "AIRUNNER_MEM_SD_DEVICE",
    "AIRUNNER_MEM_STT_DEVICE",
    "AIRUNNER_MEM_TOME_SD_RATIO",
    "AIRUNNER_MEM_TTS_DEVICE",
    "AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS",
    "AIRUNNER_MEM_USE_ATTENTION_SLICING",
    "AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD",
    "AIRUNNER_MEM_USE_ENABLE_VAE_SLICING",
    "AIRUNNER_MEM_USE_LAST_CHANNELS",
    "AIRUNNER_MEM_USE_TILED_VAE",
    "AIRUNNER_MEM_USE_TOME_SD",
    "AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG",
    "AIRUNNER_MOOD_PROMPT_OVERRIDE",
    "AIRUNNER_ORGANIZATION",
    "AIRUNNER_PROJECTS_PATH",
    "AIRUNNER_SAVE_LOG_TO_FILE",
    "AIRUNNER_SCRAPER_BLACKLIST",
    "AIRUNNER_SD_DEFAULT_VAE_PATH",
    "AIRUNNER_SD_ON",
    "AIRUNNER_SLEEP_TIME_IN_MS",
    "AIRUNNER_STATUS_ERROR_COLOR",
    "AIRUNNER_STATUS_NORMAL_COLOR_DARK",
    "AIRUNNER_STATUS_NORMAL_COLOR_LIGHT",
    "AIRUNNER_STT_ON",
    "AIRUNNER_TTS_MODEL_TYPE",
    "AIRUNNER_TTS_ON",
    "AIRUNNER_USER_DATA_PATH",
    "AIRUNNER_VALID_IMAGE_FILES",
    "AIRUNNER_VERSION",
    "AIRUNNER_VULNERABILITY_REPORT_LINK",
    "CONTENT_WIDGETS_BASE_PATH",
    "CUDA_ERROR",
    "DEFAULT_HF_ENDPOINT",
    "DEV_ENV",
    "LANGUAGES",
    "LOCAL_SERVER_HOST",
    "LOCAL_SERVER_PORT",
    "MATHJAX_VERSION",
    "MODELS_DIR",
    "NLTK_DOWNLOAD_DIR",
    "QTWEBENGINE_REMOTE_DEBUGGING",
    "RETIRED_SLASH_COMMANDS",
    "SLASH_COMMANDS",
    "STATIC_BASE_PATH",
    "VERBOSE_REACT_TOOL_AGENT",
    "get_log_level_from_env",
    "python_venv_dir",
]
