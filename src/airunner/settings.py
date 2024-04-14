import os
import logging
from PySide6.QtCore import Qt
from PySide6 import QtCore
from airunner.enums import GeneratorSection, StableDiffusionVersion, ImageGenerator, Scheduler, SignalCode


AIRUNNER_ENVIRONMENT = os.environ.get("AIRUNNER_ENVIRONMENT", "dev")  # dev or prod
LOG_LEVEL = logging.FATAL if AIRUNNER_ENVIRONMENT == "prod" else logging.WARNING
BASE_PATH = os.path.join(os.path.expanduser("~"), ".airunner")
SQLITE_DB_NAME = "airunner.db"
SQLITE_DB_PATH = os.path.join(BASE_PATH, SQLITE_DB_NAME)
DEFAULT_PATHS = {
    "art": {
        "models": {
            "txt2img": os.path.join(BASE_PATH, "art", "models", "txt2img"),
            "depth2img": os.path.join(BASE_PATH, "art", "models", "depth2img"),
            "pix2pix": os.path.join(BASE_PATH, "art", "models", "pix2pix"),
            "inpaint": os.path.join(BASE_PATH, "art", "models", "inpaint"),
            "upscale": os.path.join(BASE_PATH, "art", "models", "upscale"),
            "txt2vid": os.path.join(BASE_PATH, "art", "models", "txt2vid"),
            "embeddings": os.path.join(BASE_PATH, "art", "models", "embeddings"),
            "lora": os.path.join(BASE_PATH, "art", "models", "lora"),
            "vae": os.path.join(BASE_PATH, "art", "models", "vae"),
        },
        "other": {
            "images": os.path.join(BASE_PATH, "art", "other", "images"),
            "videos": os.path.join(BASE_PATH, "art", "other", "videos"),
        },
    },
    "text": {
        "models": {
            "casuallm": os.path.join(BASE_PATH, "text", "models", "casuallm"),
            "seq2seq": os.path.join(BASE_PATH, "text", "models", "seq2seq"),
            "visualqa": os.path.join(BASE_PATH, "text", "models", "visualqa"),
            "casuallm_cache": os.path.join(BASE_PATH, "text", "models", "casuallm", "cache"),
            "seq2seq_cache": os.path.join(BASE_PATH, "text", "models", "seq2seq", "cache"),
            "visualqa_cache": os.path.join(BASE_PATH, "text", "models", "visualqa", "cache"),
            "misc_cache": os.path.join(BASE_PATH, "text", "models", "misc", "cache"),
        },
        "other": {
            "ebooks": os.path.join(BASE_PATH, "text", "other", "ebooks"),
            "documents": os.path.join(BASE_PATH, "text", "other", "documents"),
            "llama_index": os.path.join(BASE_PATH, "text", "other", "llama_index"),
        }
    }
}

DEFAULT_CHATBOT = {
    "username": "User",
    "botname": "Computer",
    "use_personality": True,
    "use_mood": True,
    "use_guardrails": True,
    "use_system_instructions": True,
    "assign_names": True,
    "bot_personality": "happy. He loves {{ username }}",
    "bot_mood": "",
    "prompt_template": "Mistral 7B Instruct: Default Chatbot",
    "guardrails_prompt": (
        "Always assist with care, respect, and truth. "
        "Respond with utmost utility yet securely. "
        "Avoid harmful, unethical, prejudiced, or negative content. "
        "Ensure replies promote fairness and positivity."
    ),
    "system_instructions": (
        "You are a knowledgeable and helpful assistant. "
        "You will always do your best to answer the User "
        "with the most accurate and helpful information. "
        "You will always stay in character and respond as "
        "the assistant. ALWAYS respond in a conversational "
        "and expressive way. "
        "Use CAPITALIZATION for emphasis. "
        "NEVER generate text for the User ONLY for "
        "the assistant.\n"
        "Do not return tags, code, or any other form of "
        "non-human language. You are a human. "
        "You must communicate like a human."
    ),
    "generator_settings": {
        "max_new_tokens": 30,
        "model_type": "llm",
        "model_version": "mistralai/Mistral-7B-Instruct-v0.2",
        "min_length": 1,
        "do_sample": True,
        "early_stopping": True,
        "num_beams": 1,
        "temperature": 0.9,
        "top_p": 0.9,
        "no_repeat_ngram_size": 2,
        "top_k": 50,
        "eta_cutoff": 0.2,
        "repetition_penalty": 1.0,
        "return_result": True,
        "skip_special_tokens": True,
        "num_return_sequences": 1,
        "decoder_start_token_id": None,
        "use_cache": True,
        "seed": 42,
        "length_penalty": 0.1,
        "ngram_size": 2,
        "sequences": 1,
        "dtype": "4bit",
        "use_tool_filter": False,
        "cache_llm_to_disk": True,
        "use_gpu": True,
        "random_seed": True,
    }
}

AVAILABLE_IMAGE_FILTERS = [
    "SaturationFilter",
    "ColorBalanceFilter",
    "RGBNoiseFilter",
    "PixelFilter",
    "HalftoneFilter",
    "RegistrationErrorFilter"
]

"""
Used in the TTS Bark Preferences widget to selected a voice
"""
VOICES = {
    "English": {
        "Male": [
            "v2/en_speaker_0",
            "v2/en_speaker_1",
            "v2/en_speaker_2",
            "v2/en_speaker_3",
            "v2/en_speaker_4",
            "v2/en_speaker_5",
            "v2/en_speaker_6",
            "v2/en_speaker_7",
            "v2/en_speaker_8",
        ],
        "Female": [
            "v2/en_speaker_9"
        ],
    },
    "Chinese (Simplified)": {
        "Male": [
            "v2/zh_speaker_0",
            "v2/zh_speaker_1",
            "v2/zh_speaker_2",
            "v2/zh_speaker_3",
            "v2/zh_speaker_5",
            "v2/zh_speaker_8",
        ],
        "Female": [
            "v2/zh_speaker_4",
            "v2/zh_speaker_6",
            "v2/zh_speaker_7",
            "v2/zh_speaker_9",
        ],
    },
    "French": {
        "Male": [
            "v2/fr_speaker_0",
            "v2/fr_speaker_3",
            "v2/fr_speaker_4",
            "v2/fr_speaker_6",
            "v2/fr_speaker_7",
            "v2/fr_speaker_8",
            "v2/fr_speaker_9",
        ],
        "Female": [
            "v2/fr_speaker_1",
            "v2/fr_speaker_2",
            "v2/fr_speaker_5",
        ],
    },
    "German": {
        "Male": [
            "v2/de_speaker_0",
            "v2/de_speaker_1",
            "v2/de_speaker_2",
            "v2/de_speaker_4",
            "v2/de_speaker_5",
            "v2/de_speaker_6",
            "v2/de_speaker_7",
            "v2/de_speaker_9",
        ],
        "Female": [
            "v2/de_speaker_3",
            "v2/de_speaker_8",
        ],
    },
    "Hindi": {
        "Male": [
            "v2/hi_speaker_2",
            "v2/hi_speaker_5",
            "v2/hi_speaker_6",
            "v2/hi_speaker_7",
            "v2/hi_speaker_8",
        ],
        "Female": [
            "v2/hi_speaker_0",
            "v2/hi_speaker_1",
            "v2/hi_speaker_3",
            "v2/hi_speaker_4",
            "v2/hi_speaker_9",
        ],
    },
    "Italian": {
        "Male": [
            "v2/it_speaker_0",
            "v2/it_speaker_1",
            "v2/it_speaker_3",
            "v2/it_speaker_4",
            "v2/it_speaker_5",
            "v2/it_speaker_6",
            "v2/it_speaker_8",
        ],
        "Female": [
            "v2/it_speaker_2",
            "v2/it_speaker_7",
            "v2/it_speaker_9",
        ],
    },
    "Japanese": {
        "Male": [
            "v2/ja_speaker_2",
            "v2/ja_speaker_6",
        ],
        "Female": [
            "v2/ja_speaker_0",
            "v2/ja_speaker_1",
            "v2/ja_speaker_3",
            "v2/ja_speaker_4",
            "v2/ja_speaker_5",
            "v2/ja_speaker_7",
            "v2/ja_speaker_8",
            "v2/ja_speaker_9",
        ],
    },
    "Korean": {
        "Male": [
            "v2/ko_speaker_1",
            "v2/ko_speaker_2",
            "v2/ko_speaker_3",
            "v2/ko_speaker_4",
            "v2/ko_speaker_5",
            "v2/ko_speaker_6",
            "v2/ko_speaker_7",
            "v2/ko_speaker_8",
            "v2/ko_speaker_9",
        ],
        "Female": [
            "v2/ko_speaker_0",
        ],
    },
    "Polish": {
        "Male": [
            "v2/pl_speaker_0",
            "v2/pl_speaker_1",
            "v2/pl_speaker_2",
            "v2/pl_speaker_3",
            "v2/pl_speaker_5",
            "v2/pl_speaker_7",
            "v2/pl_speaker_8",
        ],
        "Female": [
            "v2/pl_speaker_4",
            "v2/pl_speaker_6",
            "v2/pl_speaker_9",
        ],
    },
    "Portuguese": {
        "Male": [
            "v2/pt_speaker_0",
            "v2/pt_speaker_1",
            "v2/pt_speaker_2",
            "v2/pt_speaker_3",
            "v2/pt_speaker_4",
            "v2/pt_speaker_5",
            "v2/pt_speaker_6",
            "v2/pt_speaker_7",
            "v2/pt_speaker_8",
            "v2/pt_speaker_9",
        ],
        "Female": [],
    },
    "Russian": {
        "Male": [
            "v2/ru_speaker_0",
            "v2/ru_speaker_1",
            "v2/ru_speaker_2",
            "v2/ru_speaker_3",
            "v2/ru_speaker_4",
            "v2/ru_speaker_7",
            "v2/ru_speaker_8",
        ],
        "Female": [
            "v2/ru_speaker_5",
            "v2/ru_speaker_6",
            "v2/ru_speaker_9",
        ],
    },
    "Spanish": {
        "Male": [
            "v2/es_speaker_0",
            "v2/es_speaker_1",
            "v2/es_speaker_2",
            "v2/es_speaker_3",
            "v2/es_speaker_4",
            "v2/es_speaker_5",
            "v2/es_speaker_6",
            "v2/es_speaker_7",
        ],
        "Female": [
            "v2/es_speaker_8",
            "v2/es_speaker_9",
        ],
    },
    "Turkish": {
        "Male": [
            "v2/tr_speaker_0",
            "v2/tr_speaker_1",
            "v2/tr_speaker_2",
            "v2/tr_speaker_3",
            "v2/tr_speaker_6",
            "v2/tr_speaker_7",
            "v2/tr_speaker_8",
            "v2/tr_speaker_9",
        ],
        "Female": [
            "v2/tr_speaker_4",
            "v2/tr_speaker_5",
        ],
    },
}
TRANSLATION_LANGUAGES = [
    "English",
    "Spanish",
]
TRANSLATION_MODELS = {
    "English": None,
    "Spanish": None,
}
MALE = "Male"
FEMALE = "Female"
PHOTO_REALISTIC_NEGATIVE_PROMPT = (
    "illustration, drawing, cartoon, not real, fake, cgi, 3d animation, "
    "3d art, sculpture, animation, anime, Digital art, Concept art, Pixel art"
)
ILLUSTRATION_NEGATIVE_PROMPT = (
    "photo, photograph, photography, high-definition, video, realistic, hyper-realistic, film"
)

BUG_REPORT_LINK = "https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title="
DISCORD_LINK = "https://discord.gg/ukcgjEpc5f"
VULNERABILITY_REPORT_LINK = "https://github.com/Capsize-Games/airunner/security/advisories/new"

# Set default models, currently only for stablediffusion (later Kandinsky as well)
DEFAULT_MODELS = {}
sd_key = ImageGenerator.STABLEDIFFUSION.value
DEFAULT_MODELS[sd_key] = {}
DEFAULT_MODELS[sd_key][GeneratorSection.TXT2IMG] = {
    "version": StableDiffusionVersion.SDXL_TURBO,
    "model": "stabilityai/sd-turbo",
}
DEFAULT_MODELS[sd_key][GeneratorSection.IMG2IMG] = {
    "version": StableDiffusionVersion.SDXL_TURBO,
    "model": "stabilityai/sd-turbo",
}
DEFAULT_MODELS[sd_key][GeneratorSection.INPAINT] = {
    "version": StableDiffusionVersion.SD1_5,
    "model": "runwayml/stable-diffusion-inpainting",
}
DEFAULT_MODELS[sd_key][GeneratorSection.OUTPAINT] = DEFAULT_MODELS[sd_key][GeneratorSection.INPAINT]
DEFAULT_MODELS[sd_key][GeneratorSection.DEPTH2IMG] = {
    "version": StableDiffusionVersion.SD1_5,
    "model": "stabilityai/stable-diffusion-2-depth",
}
DEFAULT_MODELS[sd_key][GeneratorSection.PIX2PIX] = {
    "version": StableDiffusionVersion.SD1_5,
    "model": "timbrooks/instruct-pix2pix",
}
DEFAULT_MODELS_VERSION = "b4ab6a2d996cb4c8ba0e30918fa4f4201dd2fa5ebfe3470b4ebede8e2db48f4e"
LLM_TEMPLATES_VERSION="b4ab6a2d996cb4c8ba0e30918fa4f4201dd2fa5ebfe3470b4ebede8e2db48f4e"
CONFIG_FILES = {
    "v1": "v1.yaml",
    "v2": "v2.yaml",
    "xl": "sd_xl_base.yaml",
    "xl_refiner": "sd_xl_refiner.yaml",
    "controlnet": "controlnet.yaml",
}
SCHEDULER_CLASSES = {
    Scheduler.EULER_ANCESTRAL.value: "EulerAncestralDiscreteScheduler",
    Scheduler.EULER.value: "EulerDiscreteScheduler",
    Scheduler.LMS.value: "LMSDiscreteScheduler",
    Scheduler.HEUN.value: "HeunDiscreteScheduler",
    Scheduler.DPM2.value: "DPMSolverSinglestepScheduler",
    Scheduler.DPM_PP_2M.value: "DPMSolverMultistepScheduler",
    Scheduler.DPM2_K.value: "KDPM2DiscreteScheduler",
    Scheduler.DPM2_A_K.value: "KDPM2AncestralDiscreteScheduler",
    Scheduler.DPM_PP_2M_K.value: "DPMSolverMultistepScheduler",
    Scheduler.DPM_PP_2M_SDE_K.value: "DPMSolverMultistepScheduler",
    Scheduler.DDIM.value: "DDIMScheduler",
    Scheduler.UNIPC.value: "UniPCMultistepScheduler",
    Scheduler.DDPM.value: "DDPMScheduler",
    Scheduler.DEIS.value: "DEISMultistepScheduler",
    Scheduler.DPM_2M_SDE_K.value: "DPMSolverMultistepScheduler",
    Scheduler.PLMS.value: "PNDMScheduler",
    Scheduler.DPM.value: "DPMSolverMultistepScheduler",
    # "DDIM Inverse": "DDIMInverseScheduler",
    # "IPNM": "IPNDMScheduler",
    # "RePaint": "RePaintScheduler",
    # "Karras Variance exploding": "KarrasVeScheduler",
    # "VE-SDE": "ScoreSdeVeScheduler",
    # "VP-SDE": "ScoreSdeVpScheduler",
    # "VQ Diffusion": " VQDiffusionScheduler",
}
MIN_SEED = 0
MAX_SEED = 4294967295
SCHEDULERS = [e.value for e in Scheduler]
DEFAULT_SCHEDULER = Scheduler.DPM_PP_2M_K.value
AVAILABLE_SCHEDULERS_BY_ACTION = {
    action: SCHEDULERS for action in [
        "txt2img", "img2img", "depth2img", "pix2pix", "vid2vid",
        "outpaint", "controlnet", "txt2vid"
    ]
}
AVAILABLE_SCHEDULERS_BY_ACTION.update({
    "upscale": [Scheduler.EULER.value],
    "superresolution": [Scheduler.DDIM.value, Scheduler.LMS.value, Scheduler.PLMS.value],
})
SERVER = {
    "host": "127.0.0.1",
    "port": 50006,
    "chunk_size": 1024,
}
DEFAULT_BRUSH_PRIMARY_COLOR = "#ffffff"
DEFAULT_BRUSH_SECONDARY_COLOR = "#000000"
AVAILABLE_DTYPES = ("2bit", "4bit", "8bit")
STATUS_ERROR_COLOR = "#ff0000"
STATUS_NORMAL_COLOR_LIGHT = "#000000"
STATUS_NORMAL_COLOR_DARK = "#ffffff"
DARK_THEME_NAME = "dark_theme"
LIGHT_THEME_NAME = "light_theme"
VALID_IMAGE_FILES = "Image Files (*.png *.jpg *.jpeg)"
NSFW_CONTENT_DETECTED_MESSAGE = "NSFW content detected"
SLEEP_TIME_IN_MS = 50
ORGANIZATION = "Capsize Games"
APPLICATION_NAME = "AI Runner"
DEFAULT_SHORTCUTS = {
    "Generate Image": {
        "text": "F5",
        "key": Qt.Key.Key_F5.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Generate key. Responsible for triggering the generation of a Stable Diffusion image.",
        "signal": SignalCode.SD_GENERATE_IMAGE_SIGNAL.value
    },
    "Brush Tool": {
        "text": "B",
        "key": Qt.Key.Key_B.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Brush tool key. Responsible for selecting the brush tool.",
        "signal": SignalCode.ENABLE_BRUSH_TOOL_SIGNAL.value
    },
    "Eraser Tool": {
        "text": "E",
        "key": Qt.Key.Key_E.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Eraser tool key. Responsible for selecting the eraser tool.",
        "signal": SignalCode.ENABLE_ERASER_TOOL_SIGNAL.value
    },
    "Move Tool": {
        "text": "V",
        "key": Qt.Key.Key_V.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Move tool key. Responsible for selecting the move tool.",
        "signal": SignalCode.ENABLE_MOVE_TOOL_SIGNAL.value
    },
    "Select Tool": {
        "text": "S",
        "key": Qt.Key.Key_S.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Select tool key. Responsible for selecting the select tool.",
        "signal": SignalCode.ENABLE_SELECTION_TOOL_SIGNAL.value
    },
    "Interrupt": {
        "text": "Shift+Ctrl+I",
        "key": Qt.Key.Key_I.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "Interrupt key. Responsible for interrupting the current process.",
        "signal": SignalCode.INTERRUPT_PROCESS_SIGNAL.value
    },
    "Quit": {
        "text": "Ctrl+Q",
        "key": Qt.Key.Key_Q.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "Quit key. Responsible for quitting the application.",
        "signal": SignalCode.QUIT_APPLICATION.value
    },
}
ESPEAK_SETTINGS = {
    "voices": {
        "male": [
            "m1", "m2", "m3",
        ],
        "female": [
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
MIN_NUM_INFERENCE_STEPS_IMG2IMG = 3
SD_GUARDRAILS_KEY = b'hRn5d-cm2ow_lbGJjYoQgXsmzbWa0XGfHDAv-qu91F4='
SD_GUARDRAILS = b'gAAAAABmACEW3HIFcd-f_dqgImUzesVq4aNDdLc0rkiLw_X0gX_hv_eoDUhaPU8g03NtDVnXWY7nPNhtAWNhhhgTxux2Ws2ZQXYXFf2MUFWIwTzr88-kpMY='