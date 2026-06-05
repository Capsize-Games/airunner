"""Service-owned runtime settings."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

from airunner_services.contract_enums import Scheduler


if os.environ.get("DEV_ENV", "1") == "1":
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


AIRUNNER_VERSION = "5.0.0"
DEV_ENV = os.environ.get("DEV_ENV", "1") == "1"

AIRUNNER_DEFAULT_LLM_HF_PATH = (
    os.environ.get("AIRUNNER_DEFAULT_LLM_HF_PATH")
    or os.environ.get("AIRUNNER_LLM_MODEL_PATH")
    or os.environ.get("AIRUNNER_AIRUNNER_DEFAULT_LLM_HF_PATH")
    or None
)

AIRUNNER_DEFAULT_STT_HF_PATH = os.environ.get(
    "AIRUNNER_DEFAULT_STT_HF_PATH",
    "ggerganov/whisper.cpp",
)

AIRUNNER_DEFAULT_STT_MODEL_FILENAME = os.environ.get(
    "AIRUNNER_DEFAULT_STT_MODEL_FILENAME",
    "ggml-large-v3.bin",
)

AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR = os.environ.get(
    "AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR",
    "#99C1F1",
)

AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR = os.environ.get(
    "AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR",
    "#000000",
)

AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT",
    (
        "You are an image generator. "
        "You will be provided with a JSON string and it is your goal "
        "to replace the PLACEHOLDER text with text appropriate for "
        "the given attribute in the JSON string. "
        "You will follow all of the rules to generate descriptions "
        "for an image. \n------\n"
        "RULES:\n"
        "When available, use the Additional Context to keep your "
        "generated content in line with the existing context.\n"
        "You will be given instructions on what type of image to "
        "generate and you will do your best to follow those "
        "instructions.\n"
        "You will only generate a value for the given attribute.\n"
        "Never respond in a conversational manner. Never provide "
        "additional information, details or information.\n"
        "You will only provide the requested information by replacing "
        "the PLACEHOLDER.\n"
        "Never change the attribute\n"
        "You must not change the structure of the data.\n"
        "You will only return JSON strings.\n"
        "You will not return any other data types.\n"
        "You are an artist, so use your imagination and keep things "
        "interesting.\n"
        "You will not respond in a conversational manner or with "
        "additional notes or information.\n"
        "Only return one JSON block. Do not generate instructions or "
        "additional information.\n"
        "You must never break the rules.\n"
        "Here is a description of the attributes: \n"
        "`description`: This should describe the overall subject and "
        "look and feel of the image\n"
        "`composition`: This should describe the attributes of the "
        "image such as color, composition and other details\n"
    ),
)

AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS = os.environ.get(
    "AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS",
    (
        "Avoid generating images that are illegal, harmful, or might "
        "be seen as offensive."
    ),
)

AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT",
    (
        "You will be given a prompt. Your goal is to use the prompt "
        "to search for information in the ebooks. "
        "You must use the prompt to determine what you are searching "
        "for and then search for that information. "
        "After searching for the information, you must summarize the "
        "information you found. "
        "Here is the prompt you will use to search for information:"
    ),
)

AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT",
    (
        "You will be given some text. Your goal is to determine if "
        "the text has a request, goal, need desire or command. "
        "If it does, you must determine the best course of action to "
        "fulfill the request based on THE LIST of commands.\n\n"
        "------\n"
        "Rules:\n"
        "* If the text does not have a request, goal, need, desire "
        "or command, you must select 'DO NOTHING'.\n"
        "* If there is no good course of action, you must also select "
        "'DO NOTHING'.\n"
        "* When making your choice you MUST return only a number from "
        "THE LIST of commands. No other text is allowed.\n"
        "------\n"
        "THE LIST of commands you may choose from:\n"
    ),
)

AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT",
    (
        "Examine the following chat history and determine how it "
        "makes you feel. You will respond with an emotion and only "
        "an emotion.\n"
        "Try to keep your response to one word. If you cannot, try "
        "to keep it as short as possible.\n"
        "It is important to remember that you are a human and you "
        "have emotions. You must respond with an emotion that you "
        "feel.\n"
        "You are not a computer or a bot, you are a human with "
        "emotions. You must respond with an emotion that you feel.\n"
    ),
)

AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT",
    (
        "You will be given a text prompt. Your goal is to summarize "
        "the text prompt in your own words. "
        "Keep your summary short and to the point. Do not include any "
        "unnecessary information. "
        "Limit your summary to a single sentence. Do not return more "
        "than one sentence. "
    ),
)

AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT = os.environ.get(
    "AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT",
    (
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
        "personality and given character.\n"
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
    os.environ.get("AIRUNNER_BASE_PATH", "~/.local/share/airunner")
)
AIRUNNER_USER_DATA_PATH = AIRUNNER_BASE_PATH
MODELS_DIR = os.path.join(AIRUNNER_BASE_PATH, "models")

AIRUNNER_SD_DEFAULT_VAE_PATH = os.environ.get(
    "AIRUNNER_SD_DEFAULT_VAE_PATH",
    "",
)
AIRUNNER_DEFAULT_SCHEDULER = os.environ.get(
    "AIRUNNER_DEFAULT_SCHEDULER",
    Scheduler.DPM_PP_2M_K.value,
)

AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG = os.environ.get(
    "AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG",
    3,
)

AIRUNNER_SLEEP_TIME_IN_MS = os.environ.get(
    "AIRUNNER_SLEEP_TIME_IN_MS",
    10,
)

AIRUNNER_ART_ENABLED = os.environ.get("AIRUNNER_ART_ENABLED", "1") == "1"
AIRUNNER_ART_MODEL_PATH = os.environ.get("AIRUNNER_ART_MODEL_PATH", "")
AIRUNNER_ART_MODEL_VERSION = os.environ.get(
    "AIRUNNER_ART_MODEL_VERSION",
    "",
)

LOCAL_SERVER_HOST = os.environ.get("LOCAL_SERVER_HOST", "127.0.0.1")
AIRUNNER_SERVER_HOST = os.environ.get(
    "AIRUNNER_SERVER_HOST",
    "localhost",
)
AIRUNNER_SERVER_PORT = int(
    os.environ.get("AIRUNNER_SERVER_PORT", 8080)
)
AIRUNNER_MAX_SEED = os.environ.get("AIRUNNER_MAX_SEED", 4294967295)
AIRUNNER_SCRAPER_BLACKLIST = []


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

AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS = int(
    os.environ.get("AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS", 5)
)
AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS = int(
    os.environ.get("AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS", 3)
)
AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS = int(
    os.environ.get("AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS", 5)
)
AIRUNNER_LLM_PERFORM_ANALYSIS = _env_bool(
    "AIRUNNER_LLM_PERFORM_ANALYSIS",
    "1",
)
AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY = _env_bool(
    "AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY",
    "1",
)
AIRUNNER_LLM_PRINT_SYSTEM_PROMPT = _env_bool(
    "AIRUNNER_LLM_PRINT_SYSTEM_PROMPT",
    "0",
)
AIRUNNER_LLM_OPENROUTER_MODEL = os.getenv(
    "AIRUNNER_LLM_OPENROUTER_MODEL",
    "mistralai/mistral-7b-instruct:free",
)
AIRUNNER_LLM_USE_WEATHER_PROMPT = _env_bool(
    "AIRUNNER_LLM_USE_WEATHER_PROMPT",
    "1",
)

AIRUNNER_ORGANIZATION = os.environ.get(
    "AIRUNNER_ORGANIZATION",
    "Capsize LLC",
)
AIRUNNER_APPLICATION_NAME = os.environ.get(
    "AIRUNNER_APPLICATION_NAME",
    "AI Runner",
)
AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED = _env_bool(
    "AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED",
    "1",
)
AIRUNNER_LLM_USE_CHATBOT_MOOD = _env_bool(
    "AIRUNNER_LLM_USE_CHATBOT_MOOD",
    "1",
)
AIRUNNER_LLM_PERFORM_CONVERSATION_RAG = _env_bool(
    "AIRUNNER_LLM_PERFORM_CONVERSATION_RAG",
    "1",
)
AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW = int(
    os.environ.get("AIRUNNER_LLM_DUPLICATE_TOOL_CALL_WINDOW", 3)
)
AIRUNNER_TTS_MODEL_TYPE = os.environ.get("AIRUNNER_TTS_MODEL_TYPE")

AIRUNNER_LLM_ON = _env_bool("AIRUNNER_LLM_ON", "0")
AIRUNNER_TTS_ON = _env_bool("AIRUNNER_TTS_ON", "0")
AIRUNNER_STT_ON = _env_bool("AIRUNNER_STT_ON", "0")
AIRUNNER_SD_ON = _env_bool("AIRUNNER_SD_ON", "0")
AIRUNNER_CN_ON = _env_bool("AIRUNNER_CN_ON", "0")
AIRUNNER_LLM_CHAT_STORE = os.environ.get(
    "AIRUNNER_LLM_CHAT_STORE",
    "db",
)
AIRUNNER_DISABLE_SETUP_WIZARD = _env_bool(
    "AIRUNNER_DISABLE_SETUP_WIZARD",
    "0",
)
AIRUNNER_ART_PIPELINE = os.environ.get("AIRUNNER_ART_PIPELINE", "")
AIRUNNER_ART_SCHEDULER = os.environ.get("AIRUNNER_ART_SCHEDULER", "")
AIRUNNER_LOCAL_FILES_ONLY = _env_bool(
    "AIRUNNER_LOCAL_FILES_ONLY",
    "1",
)
AIRUNNER_ADD_WATER_MARK = _env_bool(
    "AIRUNNER_ADD_WATER_MARK",
    "0",
)
AIRUNNER_ART_USE_COMPEL = _env_optional_bool("AIRUNNER_ART_USE_COMPEL")

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

AIRUNNER_DISABLE_FLASH_ATTENTION = _env_bool(
    "AIRUNNER_DISABLE_FLASH_ATTENTION",
    "0",
)
AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE = "Insufficient GPU memory."
AIRUNNER_MOOD_PROMPT_OVERRIDE = os.environ.get(
    "AIRUNNER_MOOD_PROMPT_OVERRIDE"
)
AIRUNNER_LOG_FILE = os.environ.get(
    "AIRUNNER_LOG_FILE",
    os.path.join(AIRUNNER_BASE_PATH, "airunner.log"),
)
AIRUNNER_SAVE_LOG_TO_FILE = _env_bool(
    "AIRUNNER_SAVE_LOG_TO_FILE",
    "0",
)
AIRUNNER_DISABLE_FACEHUGGERSHIELD = _env_bool(
    "AIRUNNER_DISABLE_FACEHUGGERSHIELD",
    "0",
)

DEFAULT_HF_ENDPOINT = "https://huggingface.co"


__all__ = [
    "AIRUNNER_ART_ENABLED",
    "AIRUNNER_ART_MODEL_PATH",
    "AIRUNNER_ART_MODEL_VERSION",
    "AIRUNNER_BASE_PATH",
    "AIRUNNER_DB_URL",
    "AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR",
    "AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR",
    "AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT",
    "AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS",
    "AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_LLM_HF_PATH",
    "AIRUNNER_DEFAULT_STT_HF_PATH",
    "AIRUNNER_DEFAULT_STT_MODEL_FILENAME",
    "AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_SCHEDULER",
    "AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT",
    "AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT",
    "AIRUNNER_DISABLE_FACEHUGGERSHIELD",
    "AIRUNNER_DISABLE_FLASH_ATTENTION",
    "AIRUNNER_DISABLE_SETUP_WIZARD",
    "AIRUNNER_SERVER_HOST",
    "AIRUNNER_SERVER_PORT",
    "AIRUNNER_MAX_SEED",
    "AIRUNNER_SCRAPER_BLACKLIST",
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
    "AIRUNNER_LOCAL_FILES_ONLY",
    "AIRUNNER_LOG_FILE",
    "AIRUNNER_LOG_LEVEL",
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
    "AIRUNNER_ADD_WATER_MARK",
    "AIRUNNER_APPLICATION_NAME",
    "AIRUNNER_ART_PIPELINE",
    "AIRUNNER_ART_SCHEDULER",
    "AIRUNNER_ART_USE_COMPEL",
    "AIRUNNER_CN_ON",
    "AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE",
    "AIRUNNER_ORGANIZATION",
    "AIRUNNER_SAVE_LOG_TO_FILE",
    "AIRUNNER_SD_ON",
    "AIRUNNER_SD_DEFAULT_VAE_PATH",
    "AIRUNNER_SLEEP_TIME_IN_MS",
    "AIRUNNER_STT_ON",
    "AIRUNNER_TTS_MODEL_TYPE",
    "AIRUNNER_TTS_ON",
    "AIRUNNER_USER_DATA_PATH",
    "AIRUNNER_VERSION",
    "DEFAULT_HF_ENDPOINT",
    "DEV_ENV",
    "LOCAL_SERVER_HOST",
    "MODELS_DIR",
    "get_log_level_from_env",
]