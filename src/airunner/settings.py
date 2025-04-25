"""
====================================================================
--------------------------------------------------------------------
CAPSIZE LLC
--------------------------------------------------------------------
====================================================================

See the user agreement and license agreement and other applicable
agreements before using this software.

If you find any application which uses AI Runner as a backend,
audit the application by using this repository as a reference.

All current and future security documentation will be contained
within this file.
"""

from dotenv import load_dotenv
import os
import sys
import logging

from airunner.enums import Scheduler

if os.environ.get("DEV_ENV", "1") == "1":
    load_dotenv(override=True)

python_venv_dir = os.path.dirname(sys.executable)

DEV_ENV = os.environ.get("DEV_ENV", "1") == "1"

NLTK_DOWNLOAD_DIR = os.path.join(
    python_venv_dir,
    "..",
    "lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/",
)
AIRUNNER_DEFAULT_LLM_HF_PATH = os.environ.get(
    "AIRUNNER_AIRUNNER_DEFAULT_LLM_HF_PATH",
    "w4ffl35/Ministral-8B-Instruct-2410-doublequant",
)
AIRUNNER_DEFAULT_STT_HF_PATH = os.environ.get(
    "AIRUNNER_DEFAULT_STT_HF_PATH", "openai/whisper-tiny"
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
        f"Only return one JSON block. Do not generate instructions or additional information.\n"
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
AIRUNNER_BASE_PATH = os.environ.get(
    "AIRUNNER_BASE_PATH", os.path.expanduser("~/.local/share/airunner")
)
AIRUNNER_PHOTO_REALISTIC_PROMPT = os.environ.get(
    "AIRUNNER_PHOTO_REALISTIC_PROMPT",
    (
        "photo, photograph, photography, high-definition, video, "
        "realistic, hyper-realistic, film, 8k, 4k, ultra-detailed, "
        "highly detailed, realistic lighting"
    ),
)
AIRUNNER_PHOTO_REALISTIC_NEGATIVE_PROMPT = os.environ.get(
    "AIRUNNER_PHOTO_REALISTIC_NEGATIVE_PROMPT",
    (
        "illustration, drawing, cartoon, not real, fake, cgi, 3d animation, "
        "3d art, sculpture, animation, anime, Digital art, Concept art, Pixel art"
    ),
)
AIRUNNER_ILLUSTRATION_PROMPT = os.environ.get(
    "AIRUNNER_ILLUSTRATION_PROMPT",
    (
        "illustration, drawing, cartoon, not real, fake, cgi, 3d animation, "
        "3d art, sculpture, animation, anime, Digital art, Concept art, Pixel art"
    ),
)
AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT = os.environ.get(
    "AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT",
    (
        "photo, photograph, photography, high-definition, video, "
        "realistic, hyper-realistic, film"
    ),
)
AIRUNNER_PAINTING_PROMPT = os.environ.get(
    "AIRUNNER_PAINTING_PROMPT",
    ("painting, art, canvas, brush strokes, colors, professional painting, "),
)
AIRUNNER_PAINTING_NEGATIVE_PROMPT = os.environ.get(
    "AIRUNNER_PAINTING_NEGATIVE_PROMPT",
    AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT,
)
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
AIRUNNER_NSFW_CONTENT_DETECTED_MESSAGE = os.environ.get(
    "AIRUNNER_NSFW_CONTENT_DETECTED_MESSAGE", "NSFW content detected"
)
AIRUNNER_DISCORD_URL = os.environ.get("AIRUNNER_DISCORD_URL", None)
AIRUNNER_SLEEP_TIME_IN_MS = os.environ.get("AIRUNNER_SLEEP_TIME_IN_MS", 10)

default_name = "airunner.db"
if DEV_ENV:
    default_name = "airunner.dev.db"
AIRUNNER_DB_NAME = os.environ.get("AIRUNNER_DB_NAME", default_name)

# Set the database URL
DB_PATH = os.path.expanduser(
    os.path.join("~", ".local", "share", "airunner", "data", AIRUNNER_DB_NAME)
)
default_url = "sqlite:///" + DB_PATH
AIRUNNER_DB_URL = os.environ.get("AIRUNNER_DATABASE_URL", default_url)
if AIRUNNER_DB_URL == "" or not AIRUNNER_DB_URL:
    AIRUNNER_DB_URL = default_url

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
AIRUNNER_LLM_PERFORM_ANALYSIS = (
    os.getenv("AIRUNNER_LLM_PERFORM_ANALYSIS", "1") == "1"
)
AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY = (
    os.getenv("AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY", "1") == "1"
)
AIRUNNER_LLM_PRINT_SYSTEM_PROMPT = (
    os.getenv("AIRUNNER_LLM_PRINT_SYSTEM_PROMPT", "0") == "1"
)
AIRUNNER_LLM_OPENROUTER_MODEL = os.getenv(
    "AIRUNNER_LLM_OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"
)
AIRUNNER_LLM_USE_WEATHER_PROMPT = (
    os.environ.get("AIRUNNER_LLM_USE_WEATHER_PROMPT", "1") == "1"
)

# Identity
AIRUNNER_ORGANIZATION = os.environ.get("AIRUNNER_ORGANIZATION", "Capsize LLC")
AIRUNNER_APPLICATION_NAME = os.environ.get(
    "AIRUNNER_APPLICATION_NAME", "AI Runner"
)
AIRUNNER_MESSAGE_BACKEND = os.environ.get("AIRUNNER_MESSAGE_BACKEND", None)
AIRUNNER_ART_ENABLED = os.environ.get("AIRUNNER_ART_ENABLED", "1") == "1"
AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED = (
    os.environ.get("AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED", "1") == "1"
)
AIRUNNER_LLM_USE_CHATBOT_MOOD = (
    os.environ.get("AIRUNNER_LLM_USE_CHATBOT_MOOD", "1") == "1"
)
AIRUNNER_LLM_PERFORM_CONVERSATION_RAG = (
    os.environ.get("AIRUNNER_LLM_PERFORM_CONVERSATION_RAG", "1") == "1"
)
AIRUNNER_TTS_MODEL_TYPE = os.environ.get("AIRUNNER_TTS_MODEL_TYPE", None)
AIRUNNER_TTS_SPEAKER_RECORDING_PATH = os.environ.get(
    "AIRUNNER_TTS_SPEAKER_RECORDING_PATH", ""
)

# Headless
AIRUNNER_LLM_ON = os.environ.get("AIRUNNER_LLM_ON", "0") == "1"
AIRUNNER_TTS_ON = os.environ.get("AIRUNNER_TTS_ON", "0") == "1"
AIRUNNER_STT_ON = os.environ.get("AIRUNNER_STT_ON", "0") == "1"
AIRUNNER_SD_ON = os.environ.get("AIRUNNER_SD_ON", "0") == "1"
AIRUNNER_CN_ON = os.environ.get("AIRUNNER_CN_ON", "0") == "1"
AIRUNNER_LLM_CHAT_STORE = os.environ.get("AIRUNNER_LLM_CHAT_STORE", "db")
AIRUNNER_DISABLE_SETUP_WIZARD = (
    os.environ.get("AIRUNNER_DISABLE_SETUP_WIZARD", "0") == "1"
)
AIRUNNER_ART_MODEL_PATH = os.environ.get("AIRUNNER_ART_MODEL_PATH", "")
AIRUNNER_ART_MODEL_VERSION = os.environ.get("AIRUNNER_ART_MODEL_VERSION", "")
AIRUNNER_ART_PIPELINE = os.environ.get("AIRUNNER_ART_PIPELINE", "")
AIRUNNER_ART_SCHEDULER = os.environ.get("AIRUNNER_ART_SCHEDULER", "")
AIRUNNER_LOCAL_FILES_ONLY = (
    os.environ.get("AIRUNNER_LOCAL_FILES_ONLY", "1") == "1"
)

AIRUNNER_ART_USE_COMPEL = os.environ.get("AIRUNNER_ART_USE_COMPEL", None)
if AIRUNNER_ART_USE_COMPEL is not None:
    AIRUNNER_ART_USE_COMPEL = AIRUNNER_ART_USE_COMPEL == "1"

# Memory
AIRUNNER_MEM_USE_LAST_CHANNELS = os.environ.get(
    "AIRUNNER_USE_LAST_CHANNELS", None
)
AIRUNNER_MEM_USE_ATTENTION_SLICING = os.environ.get(
    "AIRUNNER_USE_ATTENTION_SLICING", None
)
AIRUNNER_MEM_USE_ENABLE_VAE_SLICING = os.environ.get(
    "AIRUNNER_USE_ENABLE_VAE_SLICING", None
)
AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS = os.environ.get(
    "AIRUNNER_USE_ACCELERATED_TRANSFORMERS", None
)
AIRUNNER_MEM_USE_TILED_VAE = os.environ.get("AIRUNNER_USE_TILED_VAE", None)
AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD = os.environ.get(
    "AIRUNNER_ENABLE_MODEL_CPU_OFFLOAD", None
)
AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD = os.environ.get(
    "AIRUNNER_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD", None
)
AIRUNNER_MEM_USE_TOME_SD = os.environ.get("AIRUNNER_USE_TOME_SD", None)
AIRUNNER_MEM_TOME_SD_RATIO = os.environ.get("AIRUNNER_TOME_SD_RATIO", None)
AIRUNNER_MEM_SD_DEVICE = os.environ.get("AIRUNNER_MEM_SD_DEVICE", None)
AIRUNNER_MEM_LLM_DEVICE = os.environ.get("AIRUNNER_MEM_LLM_DEVICE", None)
AIRUNNER_MEM_TTS_DEVICE = os.environ.get("AIRUNNER_MEM_TTS_DEVICE", None)
AIRUNNER_MEM_STT_DEVICE = os.environ.get("AIRUNNER_MEM_STT_DEVICE", None)


def get_log_level_from_env():
    log_level_str = os.environ.get("AIRUNNER_LOG_LEVEL", "DEBUG").upper()
    log_levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return log_levels.get(log_level_str, logging.DEBUG)


AIRUNNER_LOG_LEVEL = get_log_level_from_env()
AIRUNNER_DISABLE_FLASH_ATTENTION = (
    os.environ.get("AIRUNNER_DISABLE_FLASH_ATTENTION", "0") == "1"
)
AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE = "Insufficient GPU memory."
AIRUNNER_ENABLE_OPEN_VOICE = (
    os.environ.get("AIRUNNER_ENABLE_OPEN_VOICE", "0") == "1"
)
AIRUNNER_MOOD_PROMPT_OVERRIDE = os.environ.get(
    "AIRUNNER_MOOD_PROMPT_OVERRIDE", None
)
AIRUNNER_LOG_FILE = os.environ.get(
    "AIRUNNER_LOG_FILE", os.path.join(AIRUNNER_BASE_PATH, "airunner.log")
)
AIRUNNER_SAVE_LOG_TO_FILE = (
    os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "1") == "1"
)
AIRUNNER_DISABLE_FACEHUGGERSHIELD = (
    os.environ.get("AIRUNNER_DISABLE_FACEHUGGERSHIELD", "0") == "1"
)
CUDA_ERROR = "CUDA out of memory"
