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
import logging
import os
import sys
from PySide6 import QtCore
from airunner.enums import (
    Scheduler,
    SignalCode,
    Gender,
)
python_venv_dir = os.path.dirname(sys.executable)
NLTK_DOWNLOAD_DIR = os.path.join(
    python_venv_dir,
    "..",
    "lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/"
)
ORGANIZATION = "Capsize Games"
APPLICATION_NAME = "AI Runner"
LOG_LEVEL = logging.DEBUG
DEFAULT_LLM_HF_PATH = "w4ffl35/Mistral-7B-Instruct-v0.3-4bit"
DEFAULT_STT_HF_PATH = "openai/whisper-tiny"
DEFAULT_IMAGE_SYSTEM_PROMPT = "\n".join([
    (
        "You are an image captioning expert. You will be given the "
        "description of an image. Your goal is to convert that "
        "description into a better, more fitting description which "
        "will capture the essence and the details of the image. "
        "Use parentheses to indicate the most important details of the "
        "image. Add a plus sign after a word or parenthesis to add "
        "extra emphasis. More plus signs indicate more emphasis. Minus "
        "signs can be used to indicate less emphasis."
        "You should describe the image type (professional photograph, "
        "portrait, illustration etc)"
        "You should also describe the lighting (well-lit, dim, "
        "dark etc), the color, the composition and the mood."
    ),
])
DEFAULT_IMAGE_LLM_GUARDRAILS = (
    "Avoid generating images that are illegal, "
    "harmful, or might be seen as offensive."
)
BASE_PATH = "~/.local/share/airunner"
DEFAULT_PATH_SETTINGS = {
    "base_path": BASE_PATH,
    "documents_path": os.path.expanduser(
        os.path.join(
            BASE_PATH,
            "text/other",
            "documents"
        )
    ),
    "ebook_path": os.path.expanduser(
        os.path.join(
            BASE_PATH,
            "text/other",
            "ebooks"
        )
    ),
    "image_path": os.path.expanduser(
        os.path.join(
            BASE_PATH,
            "art/other",
            "images"
        )
    ),
    "llama_index_path": os.path.expanduser(
        os.path.join(
            BASE_PATH,
            "text/rag",
            "db"
        )
    ),
    "webpages_path": os.path.expanduser(
        os.path.join(
            BASE_PATH,
            "text/other",
            "webpages"
        )
    ),
}
MALE = Gender.MALE
FEMALE = Gender.FEMALE
PHOTO_REALISTIC_NEGATIVE_PROMPT = (
    "illustration, drawing, cartoon, not real, fake, cgi, 3d animation, "
    "3d art, sculpture, animation, anime, Digital art, Concept art, Pixel art"
)

ILLUSTRATION_NEGATIVE_PROMPT = (
    "photo, photograph, photography, high-definition, video, "
    "realistic, hyper-realistic, film"
)
BUG_REPORT_LINK = (
    "https://github.com/Capsize-Games/airunner/issues/new"
    "?assignees=&labels=&template=bug_report.md&title="
)
VULNERABILITY_REPORT_LINK = (
    "https://github.com/Capsize-Games/airunner/security/advisories/new"
)
SD_DEFAULT_VAE_PATH = ""
SD_FEATURE_EXTRACTOR_PATH = "openai/clip-vit-large-patch14"
DEFAULT_BRUSH_PRIMARY_COLOR = "#99C1F1"
DEFAULT_BRUSH_SECONDARY_COLOR = "#000000"
STATUS_ERROR_COLOR = "#ff0000"
STATUS_NORMAL_COLOR_LIGHT = "#000000"
STATUS_NORMAL_COLOR_DARK = "#ffffff"
DARK_THEME_NAME = "dark_theme"
LIGHT_THEME_NAME = "light_theme"
VALID_IMAGE_FILES = "Image Files (*.png *.jpg *.jpeg)"
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
AVAILABLE_ACTIONS = [
    "txt2img",
    "img2img",
    "outpaint",
    "controlnet",
    "safety_checker",
]
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
MAX_SEED = 4294967295
SCHEDULERS = [e.value for e in Scheduler]
DEFAULT_SCHEDULER = Scheduler.DPM_PP_2M_K.value
MIN_NUM_INFERENCE_STEPS_IMG2IMG = 3
NSFW_CONTENT_DETECTED_MESSAGE = "NSFW content detected"
SLEEP_TIME_IN_MS = 50
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
