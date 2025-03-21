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
from PySide6 import QtCore
from airunner.enums import (
    Scheduler,
    SignalCode,
)
load_dotenv()
python_venv_dir = os.path.dirname(sys.executable)
NLTK_DOWNLOAD_DIR = os.path.join(
    python_venv_dir,
    "..",
    "lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/"
)
DEFAULT_LLM_HF_PATH = "w4ffl35/Ministral-8B-Instruct-2410-doublequant"
DEFAULT_STT_HF_PATH = "openai/whisper-tiny"
DEFAULT_IMAGE_SYSTEM_PROMPT = os.environ.get(
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
    )
)
DEFAULT_IMAGE_LLM_GUARDRAILS = os.environ.get(
    "AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS", (
        "Avoid generating images that are illegal, "
        "harmful, or might be seen as offensive."
    )
)
DEFAULT_RAG_SEARCH_SYSTEM_PROMPT = os.environ.get(
    "DEFAULT_RAG_SEARCH_SYSTEM_PROMPT",
    (
        "You will be given a prompt. Your goal is to use the prompt to search for information in the ebooks. "
        "You must use the prompt to determine what you are searching for and then search for that information. "
        "After searching for the information, you must summarize the information you found. "
        "Here is the prompt you will use to search for information:"
    )
)
DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT = os.environ.get(
    "DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT",
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
    )
)
DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT = os.environ.get(
    "DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT",
    (
        "Examine the following chat history and determine how it makes you feel. You will respond with an emotion "
        "and only an emotion.\n"
        "Try to keep your response to one word. If you cannot, try to keep it as short as possible.\n"
        "It is important to remember that you are a human and you have emotions. You must respond with an emotion that "
        "you feel.\n"
        "You are not a computer or a bot, you are a human with emotions. You must respond with an emotion that you "
        "feel.\n"
    )
)
DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT = os.environ.get(
    "DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT",
    (
        "You will be given a text prompt. Your goal is to summarize the text prompt in your own words. "
        "Keep your summary short and to the point. Do not include any unnecessary information. "
        "Limit your summary to a single sentence. Do not return more than one sentence. "
    )
)
DEFAULT_CHATBOT_SYSTEM_PROMPT = os.environ.get(
    "DEFAULT_CHATBOT_SYSTEM_PROMPT",
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
    )
)
DEFAULT_CHATBOT_GUARDRAILS_PROMPT = os.environ.get(
    "DEFAULT_CHATBOT_GUARDRAILS_PROMPT",
    (
        "Always assist with care, respect, and truth. "
        "Respond with utmost utility yet securely. "
        "Avoid harmful, unethical, prejudiced, or negative content. "
        "Ensure replies promote fairness and positivity."
    )
)
BASE_PATH = os.environ.get("BASE_PATH", "~/.local/share/airunner")
DEFAULT_PATH_SETTINGS = {
    "documents_path": os.path.expanduser(
        os.path.join(
            "text",
            "other",
            "documents"
        )
    ),
    "ebook_path": os.path.expanduser(
        os.path.join(
            "text",
            "other",
            "ebooks"
        )
    ),
    "image_path": os.path.expanduser(
        os.path.join(
            "art",
            "other",
            "images"
        )
    ),
    "llama_index_path": os.path.expanduser(
        os.path.join(
            "text",
            "rag",
            "db"
        )
    ),
    "webpages_path": os.path.expanduser(
        os.path.join(
            "text",
            "other",
            "webpages"
        )
    ),
    "stt_model_path": os.path.expanduser(
        os.path.join(
            "text",
            "models",
            "stt"
        )
    ),
    "tts_model_path": os.path.expanduser(
        os.path.join(
            "text",
            "models",
            "tts"
        )
    ),
}
PHOTO_REALISTIC_NEGATIVE_PROMPT = os.environ.get(
    "PHOTO_REALISTIC_NEGATIVE_PROMPT",
    (
        "illustration, drawing, cartoon, not real, fake, cgi, 3d animation, "
        "3d art, sculpture, animation, anime, Digital art, Concept art, Pixel art"
    )
)

ILLUSTRATION_NEGATIVE_PROMPT = os.environ.get(
    "ILLUSTRATION_NEGATIVE_PROMPT",
    (
        "photo, photograph, photography, high-definition, video, "
        "realistic, hyper-realistic, film"
    )
)
BUG_REPORT_LINK = os.environ.get(
    "BUG_REPORT_LINK",
    (
        "https://github.com/Capsize-Games/airunner/issues/new"
        "?assignees=&labels=&template=bug_report.md&title="
    )
)
VULNERABILITY_REPORT_LINK = os.environ.get(
    "VULNERABILITY_REPORT_LINK",
    (
        "https://github.com/Capsize-Games/airunner/security/advisories/new"
    )
)
SD_DEFAULT_VAE_PATH = os.environ.get("SD_DEFAULT_VAE_PATH", "")
DEFAULT_BRUSH_PRIMARY_COLOR = os.environ.get("DEFAULT_BRUSH_PRIMARY_COLOR", "#99C1F1")
DEFAULT_BRUSH_SECONDARY_COLOR = os.environ.get("DEFAULT_BRUSH_SECONDARY_COLOR", "#000000")
STATUS_ERROR_COLOR = os.environ.get("STATUS_ERROR_COLOR", "#ff0000")
STATUS_NORMAL_COLOR_LIGHT = os.environ.get("STATUS_NORMAL_COLOR_LIGHT", "#000000")
STATUS_NORMAL_COLOR_DARK = os.environ.get("STATUS_NORMAL_COLOR_DARK", "#ffffff")
DARK_THEME_NAME = os.environ.get("DARK_THEME_NAME", "dark_theme")
LIGHT_THEME_NAME = os.environ.get("LIGHT_THEME_NAME", "light_theme")
VALID_IMAGE_FILES = os.environ.get("VALID_IMAGE_FILES", "Image Files (*.png *.jpg *.jpeg)")
ESPEAK_SETTINGS = {
    "voices": {
        "Male": [
            "m1", "m2", "m3",
        ],
        "Female": [
            "f1", "f2", "f3",
        ],
    },
    "rate": {
        "min": -100,
        "max": 100,
        "default": 0
    },
    "pitch": {
        "min": -100,
        "max": 100,
        "default": 0
    },
    "volume": {
        "min": 0,
        "max": 100,
        "default": 100
    },
    "punctuation_modes": ["none", "all", "some"],
}
SCHEDULER_CLASSES = [
    dict(
        display_name=Scheduler.EULER_ANCESTRAL.value,
        name="EulerAncestralDiscreteScheduler",
    ),
    dict(
        display_name=Scheduler.EULER.value,
        name="EulerDiscreteScheduler",
    ),
    dict(
        display_name=Scheduler.LMS.value,
        name="LMSDiscreteScheduler",
    ),
    dict(
        display_name=Scheduler.HEUN.value,
        name="HeunDiscreteScheduler",
    ),
    dict(
        display_name=Scheduler.DPM2.value,
        name="DPMSolverSinglestepScheduler",
    ),
    dict(
        display_name=Scheduler.DPM_PP_2M.value,
        name="DPMSolverMultistepScheduler",
    ),
    dict(
        display_name=Scheduler.DPM2_K.value,
        name="KDPM2DiscreteScheduler",
    ),
    dict(
        display_name=Scheduler.DPM2_A_K.value,
        name="KDPM2AncestralDiscreteScheduler",
    ),
    dict(
        display_name=Scheduler.DPM_PP_2M_K.value,
        name="DPMSolverMultistepScheduler",
    ),
    dict(
        display_name=Scheduler.DPM_PP_2M_SDE_K.value,
        name="DPMSolverMultistepScheduler",
    ),
    dict(
        display_name=Scheduler.DDIM.value,
        name="DDIMScheduler",
    ),
    dict(
        display_name=Scheduler.UNIPC.value,
        name="UniPCMultistepScheduler",
    ),
    dict(
        display_name=Scheduler.DDPM.value,
        name="DDPMScheduler",
    ),
    dict(
        display_name=Scheduler.DEIS.value,
        name="DEISMultistepScheduler",
    ),
    dict(
        display_name=Scheduler.DPM_2M_SDE_K.value,
        name="DPMSolverMultistepScheduler",
    ),
    dict(
        display_name=Scheduler.PLMS.value,
        name="PNDMScheduler",
    ),
    dict(
        display_name=Scheduler.DPM.value,
        name="DPMSolverMultistepScheduler",
    ),
]
MAX_SEED = os.environ.get("MAX_SEED", 4294967295)
DEFAULT_SCHEDULER = os.environ.get("DEFAULT_SCHEDULER", Scheduler.DPM_PP_2M_K.value)
MIN_NUM_INFERENCE_STEPS_IMG2IMG = os.environ.get("MIN_NUM_INFERENCE_STEPS_IMG2IMG", 3)
NSFW_CONTENT_DETECTED_MESSAGE = os.environ.get("NSFW_CONTENT_DETECTED_MESSAGE", "NSFW content detected")
DISCORD_URL = os.environ.get("AIRUNNER_DISCORD_URL", None)
SLEEP_TIME_IN_MS = os.environ.get("SLEEP_TIME_IN_MS", 50)
DEFAULT_SHORTCUTS = [
    {
        "display_name": "Generate Image",
        "text": "F1",
        "key": QtCore.Qt.Key.Key_F1.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Generate key. Responsible for triggering the generation of a Stable Diffusion image.",
        "signal": SignalCode.SD_GENERATE_IMAGE_SIGNAL.value
    },
    {
        "display_name": "Brush Tool",
        "text": "B",
        "key": QtCore.Qt.Key.Key_B.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Brush tool key. Responsible for selecting the brush tool.",
        "signal": SignalCode.ENABLE_BRUSH_TOOL_SIGNAL.value
    },
    {
        "display_name": "Eraser Tool",
        "text": "E",
        "key": QtCore.Qt.Key.Key_E.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Eraser tool key. Responsible for selecting the eraser tool.",
        "signal": SignalCode.ENABLE_ERASER_TOOL_SIGNAL.value
    },
    {
        "display_name": "Move Tool",
        "text": "V",
        "key": QtCore.Qt.Key.Key_V.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Move tool key. Responsible for selecting the move tool.",
        "signal": SignalCode.ENABLE_MOVE_TOOL_SIGNAL.value
    },
    {
        "display_name": "Select Tool",
        "text": "S",
        "key": QtCore.Qt.Key.Key_S.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Select tool key. Responsible for selecting the select tool.",
        "signal": SignalCode.ENABLE_SELECTION_TOOL_SIGNAL.value
    },
    {
        "display_name": "Interrupt",
        "text": "Shift+Ctrl+I",
        "key": QtCore.Qt.Key.Key_I.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "Interrupt key. Responsible for interrupting the current process.",
        "signal": SignalCode.INTERRUPT_PROCESS_SIGNAL.value
    },
    {
        "display_name": "Navigate",
        "text": "Shift+Ctrl+P",
        "key": QtCore.Qt.Key.Key_P.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "URL key. Responsible for navigating to a URL.",
        "signal": SignalCode.NAVIGATE_TO_URL.value
    },
    {
        "display_name": "Quit",
        "text": "Ctrl+Q",
        "key": QtCore.Qt.Key.Key_Q.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "Quit key. Responsible for quitting the application.",
        "signal": SignalCode.QUIT_APPLICATION.value
    },
    {
        "display_name": "Refresh Stylesheet",
        "text": "F5",
        "key": QtCore.Qt.Key.Key_F5.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Refresh the stylesheet. Useful when creating a template.",
        "signal": SignalCode.REFRESH_STYLESHEET_SIGNAL.value
    },
]
DB_PATH = os.path.expanduser(
    os.path.join(
        "~",
        ".local",
        "share",
        "airunner",
        "data",
        "airunner.db"
    )
)
default_url = "sqlite:///" + DB_PATH
DB_URL = os.environ.get("AIRUNNER_DATABASE_URL", default_url)
if DB_URL == "" or not DB_URL:
    DB_URL = default_url

# Default LLM Settings
AIRUNNER_USE_LOCAL_LLM = os.environ.get("AIRUNNER_USE_LOCAL_LLM", True)
AIRUNNER_USE_OPENROUTER = os.environ.get("AIRUNNER_USE_OPENROUTER", False)
AIRUNNER_OPENROUTER_API_KEY = os.environ.get("AIRUNNER_OPENROUTER_API_KEY", "")
AIRUNNER_USE_OPENAI = os.environ.get("AIRUNNER_USE_OPENAI", False)
AIRUNNER_OPENAI_API_KEY = os.environ.get("AIRUNNER_OPENAI_API_KEY", "")
AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS = int(os.environ.get("AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS", 5))
AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS = int(os.environ.get("AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS", 3))
AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS = int(os.environ.get("AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS", 5))