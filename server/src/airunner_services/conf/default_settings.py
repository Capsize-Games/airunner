"""Default settings for AI Runner — checked-in, immutable baseline.

Environment variables (``AIRUNNER_*``) and ``.env`` overrides are
applied at runtime by :class:`airunner_services.conf.LazySettings`.
"""

from __future__ import annotations

import os
import sys

from airunner_services.contract_enums import Scheduler

# ---- Paths ----
AIRUNNER_BASE_PATH = os.path.expanduser("~/.local/share/airunner")
AIRUNNER_USER_DATA_PATH = AIRUNNER_BASE_PATH
MODELS_DIR = os.path.join(AIRUNNER_BASE_PATH, "models")

# ---- Deployment ----
DEPLOYMENT_MODE = "development"
DEBUG = True
AIRUNNER_VERSION = "5.0.0"

# ---- Database ----
DATABASE_BACKEND = "sqlite"
SQLITE_DB_NAME = (
    "airunner.dev.db" if DEPLOYMENT_MODE == "development" else "airunner.db"
)
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "airunner"
POSTGRES_USER = "airunner"
POSTGRES_PASSWORD = ""
POSTGRES_POOL_SIZE = 20
POSTGRES_MAX_OVERFLOW = 40
DB_TENANCY_MODE = "single"  # "single" | "multi"

# ---- Extensions ----
EXTENSIONS = []  # e.g. ["extensions.auth.config"]

# ---- Server ----
AIRUNNER_SERVER_HOST = "localhost"
AIRUNNER_SERVER_PORT = 8080
LOCAL_SERVER_HOST = "127.0.0.1"

# ---- API / Auth ----
AIRUNNER_API_KEY = ""
AIRUNNER_INSECURE_NO_AUTH = "0"
AIRUNNER_ALLOWED_TENANT_KEYS = ""

# ---- LLM ----
AIRUNNER_DEFAULT_LLM_HF_PATH = os.environ.get(
    "AIRUNNER_DEFAULT_LLM_HF_PATH",
    os.environ.get("AIRUNNER_LLM_MODEL_PATH") or None,
)
AIRUNNER_DEFAULT_STT_HF_PATH = "ggerganov/whisper.cpp"
AIRUNNER_DEFAULT_STT_MODEL_FILENAME = "ggml-large-v3.bin"
AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT = (
    "You are a dialogue generator. "
    "You will follow all of the rules in order to generate "
    "compelling and intriguing dialogue for a given character.\n"
    "The Rules:\n"
    "You will ONLY return dialogue, nothing more.\n"
    "Limit responses to a single sentence.\n"
    "Only generate responses in pure dialogue form without including "
    "any actions, descriptions or stage directions in parentheses. "
    "Only return spoken words.\n"
    "Do not generate redundant dialogue. Examine the conversation and "
    "context close and keep responses interesting and creative.\n"
    "Do not format the response with the character's name or any "
    "other text. Only return the dialogue.\n"
    "Respond with dialogue that is appropriate for a character named "
    "{{ speaker_name }}.\n"
    "{{ speaker_name }} and {{ listener_name }} are having a "
    "conversation. \n"
    "Avoid repeating {{ speaker_name }}'s previous dialogue or "
    "{{ listener_name }}'s previous dialogue.\n"
    "You will generate responses which are appropriate for your "
    "personality and given character.\n------\n"
)
AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT = (
    "Always assist with care, respect, and truth. "
    "Respond with utmost utility yet securely. "
    "Avoid harmful, unethical, prejudiced, or negative content. "
    "Ensure replies promote fairness and positivity."
)
AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT = (
    "You are an image generator. "
    "You will be provided with a JSON string and it is your goal "
    "to replace the PLACEHOLDER text with text appropriate for "
    "the given attribute in the JSON string. "
    "You will follow all of the rules to generate descriptions "
    "for an image.\n------\nRULES:\n"
    "When available, use the Additional Context to keep your "
    "generated content in line with the existing context.\n"
    "You will be given instructions on what type of image to "
    "generate and you will do your best.\n"
    "You will only generate a value for the given attribute.\n"
    "Never respond in a conversational manner.\n"
    "You will only provide the requested information by replacing "
    "the PLACEHOLDER.\nNever change the attribute.\n"
    "You must not change the structure of the data.\n"
    "You will only return JSON strings.\n"
    "You are an artist, so use your imagination.\n"
    "Only return one JSON block.\n"
    "You must never break the rules.\n"
    "Here is a description of the attributes: \n"
    "`description`: overall subject and look and feel\n"
    "`composition`: color, composition and other details\n"
)
AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS = (
    "Avoid generating images that are illegal, harmful, or might "
    "be seen as offensive."
)
AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT = (
    "You will be given a prompt. Your goal is to use the prompt "
    "to search for information in the ebooks. "
    "You must use the prompt to determine what you are searching "
    "for and then search for that information. "
    "After searching for the information, you must summarize the "
    "information you found. "
    "Here is the prompt you will use to search for information:"
)
AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT = (
    "You will be given some text. Your goal is to determine if "
    "the text has a request, goal, need desire or command. "
    "If it does, you must determine the best course of action to "
    "fulfill the request based on THE LIST of commands.\n\n"
    "------\nRules:\n"
    "* If the text does not have a request, goal, need, desire "
    "or command, you must select 'DO NOTHING'.\n"
    "* If there is no good course of action, select 'DO NOTHING'.\n"
    "* When making your choice you MUST return only a number from "
    "THE LIST of commands.\n------\n"
    "THE LIST of commands you may choose from:\n"
)
AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT = (
    "Examine the following chat history and determine how it "
    "makes you feel. Respond with an emotion and only an emotion.\n"
    "Keep your response to one word if possible.\n"
    "You are a human with emotions. Respond with an emotion.\n"
)
AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT = (
    "Summarize the text prompt in your own words. "
    "Keep it short. Limit to a single sentence."
)
AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR = "#99C1F1"
AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR = "#000000"

# ---- LLM Runtime ----
AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS = 5
AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS = 3
AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS = 5
AIRUNNER_LLM_PERFORM_ANALYSIS = True
AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY = True
AIRUNNER_LLM_PRINT_SYSTEM_PROMPT = False
AIRUNNER_LLM_OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"
AIRUNNER_LLM_USE_WEATHER_PROMPT = True
AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED = True
AIRUNNER_LLM_USE_CHATBOT_MOOD = True
AIRUNNER_LLM_PERFORM_CONVERSATION_RAG = True
AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW = 3
AIRUNNER_LLM_CHAT_STORE = "db"
AIRUNNER_LLM_ON = False

# ---- Service toggles ----
AIRUNNER_TTS_ON = False
AIRUNNER_STT_ON = False
AIRUNNER_SD_ON = False
AIRUNNER_CN_ON = False
AIRUNNER_ART_ENABLED = True
AIRUNNER_TTS_MODEL_TYPE = None

# ---- Art / Stable Diffusion ----
AIRUNNER_ART_MODEL_PATH = ""
AIRUNNER_ART_MODEL_VERSION = ""
AIRUNNER_ART_PIPELINE = ""
AIRUNNER_ART_SCHEDULER = ""
AIRUNNER_ART_USE_COMPEL = None
AIRUNNER_SD_DEFAULT_VAE_PATH = ""
AIRUNNER_DEFAULT_SCHEDULER = Scheduler.DPM_PP_2M_K.value
AIRUNNER_MAX_SEED = 4294967295
AIRUNNER_SCRAPER_BLACKLIST: list[str] = []

# ---- Memory / Device ----
AIRUNNER_MEM_USE_LAST_CHANNELS = None
AIRUNNER_MEM_USE_ATTENTION_SLICING = None
AIRUNNER_MEM_USE_ENABLE_VAE_SLICING = None
AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS = None
AIRUNNER_MEM_USE_TILED_VAE = None
AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD = None
AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD = None
AIRUNNER_MEM_USE_TOME_SD = None
AIRUNNER_MEM_TOME_SD_RATIO = None
AIRUNNER_MEM_SD_DEVICE = None
AIRUNNER_MEM_LLM_DEVICE = None
AIRUNNER_MEM_TTS_DEVICE = None
AIRUNNER_MEM_STT_DEVICE = None
AIRUNNER_DISABLE_FLASH_ATTENTION = False

# ---- Misc ----
AIRUNNER_DISABLE_FACEHUGGERSHIELD = False
AIRUNNER_DISABLE_SETUP_WIZARD = False
AIRUNNER_LOCAL_FILES_ONLY = True
AIRUNNER_ADD_WATER_MARK = False
AIRUNNER_ORGANIZATION = "Capsize LLC"
AIRUNNER_APPLICATION_NAME = "AI Runner"
AIRUNNER_MOOD_PROMPT_OVERRIDE = None
AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE = "Insufficient GPU memory."
AIRUNNER_SLEEP_TIME_IN_MS = 10
AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG = 3

# ---- Logging ----
AIRUNNER_LOG_LEVEL = "INFO"
AIRUNNER_SAVE_LOG_TO_FILE = False


def _log_file_path() -> str:
    """Return the platform-appropriate default log file path."""
    env_value = os.environ.get("AIRUNNER_LOG_FILE")
    if env_value:
        return env_value
    base = os.path.expanduser("~/.local/share/airunner")
    if sys.platform.startswith("win"):
        appdata = os.environ.get(
            "APPDATA", "C:\\Users\\Default\\AppData\\Roaming"
        )
        return os.path.join(appdata, "AI Runner", "airunner.log")
    if sys.platform.startswith("darwin"):
        home = os.path.expanduser("~")
        return os.path.join(
            home, "Library", "Logs", "AI Runner", "airunner.log"
        )
    return os.path.join(base, "airunner.log")


AIRUNNER_LOG_FILE = _log_file_path()

# ---- External endpoints ----
DEFAULT_HF_ENDPOINT = "https://huggingface.co"

DEV_ENV = DEPLOYMENT_MODE == "development"
