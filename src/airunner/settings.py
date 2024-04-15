"""
██████████████████████████████████████████████████████████████
██                                 A REAL INTERNET COMPANY  ██
██  █████  ██████  ██████   ██████  ██████  ██████  ██████  ██
██  ██     ██  ██  ██   ██  ██        ██        ██  ██      ██
██  ██     ██████  ██████   ██████    ██      ██    ████    ██
██  ██     ██  ██  ██           ██    ██    ██      ██      ██
██  █████  ██  ██  ██       ██████  ██████  ██████  ██████  ██
██                                           █    █    ███  ██
██                                           █    █    █    ██
██                                           ███  ███  ███  ██
██████████████████████████████████████████████████████████████

See the user agreement and
license agreement and
other applicable agreements
before using this software.
"""
import os
import logging
from PySide6.QtCore import Qt
from PySide6 import QtCore

"""
██████████████████████████████████████████████████████████████████████████████████   
█                                                                                █ 
█  ██    ██  ████████  ████████  ██    ██  ████████  ██    ██  ████████  ██  ██  █ 
█  ██    ██  ██    ██  ██    ██  ██    ██     ██     ██    ██  ██        ██  ██  █ 
█  ██    ██  ████████  ██████    ████  ██     ██     ████  ██  ██  ████  ██  ██  █ 
█  ██ ██ ██  ██    ██  ██    ██  ██  ████     ██     ██  ████  ██    ██          █ 
█  ███  ███  ██    ██  ██    ██  ██    ██  ████████  ██    ██  ████████  ██  ██  █ 
█                                                                                █ 
██████████████████████████████████████████████████████████████████████████████████

====================================================================
--------------------------------------------------------------------
HUGGINGFACE.CO IS A WEBSITE THAT HOSTS AI MODELS AND ALLOWS PEOPLE 
TO CREATE SERVERS THAT CAN USE THESE MODELS. SOME OF THE DEFAULT 
SETTINGS PRESENT A SECURITY RISK. HUGGINGFACE.CO LIBRARIES SHOULD 
FIX THEIR DEFAULT SETTINGS AND REMOVE THE ABILITY TO DOWNLOAD AND 
EXECUTE CODE. CAREFULLY READ THE FOLLOWING SETTINGS AND COMMENTS
BEFORE YOU CHANGE ANYTHING. DO NOT CHANGE ANYTHING UNLESS YOU KNOW 
WHAT YOU ARE DOING.
--------------------------------------------------------------------
====================================================================
"""


"""
Environment variables for huggingface libraries
The following environment variables control huggingface libraries.

DO NOT CHANGE THESE VARIABLES UNLESS YOU KNOW WHAT YOU ARE DOING!

For implementation, see the function
airunner.src.utils.set_huggingface_environment_variables
"""

####################################################################
# This is the default mode to prevent HF from accessing the internet
# Only change this to True if you want to create an application
# that can automatically download required models from huggingface.co
####################################################################
HF_ALLOW_DOWNLOADS = False  # This is an AI Runner specific variable

####################################################################
# HF_HUB_DISABLE_TELEMETRY is used to disable telemetry for
# huggingface models. Never enable telemetry. Setting this to "0"
# will send telemetry to huggingface. Huggingface libraries should
# NOT have the ability to send telemetry.
####################################################################
HF_HUB_DISABLE_TELEMETRY = "1"

####################################################################
# HF_HUB_OFFLINE
# 1 == Disable internet access.
# Internet access will only be used when downloading models with the
# model manager or setup wizard.
####################################################################
HF_HUB_OFFLINE = "1"

####################################################################
# HF_CACHE_DIR is the directory where huggingface models are stored.
# Default value is "~/.cache/huggingface" but we have changed it to
# "~/.airunner/huggingface"
# It is safe to change this to a different directory. It can also
# be changed in the GUI.
# If you would like to use the default directory (in order to use
# your existing cache), set it to "~/.cache/huggingface"
####################################################################
HF_CACHE_DIR = "~/.airunner/huggingface"

####################################################################
# HF_HOME is the directory where huggingface models are stored.
# We set this to HF_CACHE_DIR
####################################################################
HF_HOME = HF_CACHE_DIR

####################################################################
# HF_ASSETS_CACHE is the directory where huggingface assets are stored.
# Default value is "$HF_HOME/assets"
# Here we hard code it to the same directory as HF_HOME
####################################################################
HF_ASSETS_CACHE = HF_CACHE_DIR

####################################################################
# HF_ENDPOINT is the huggingface endpoint.
# Default value is "https://huggingface.co" but we have changed it to
# "https://huggingface.co"
# in order to force prevention of ineternet access.
####################################################################
HF_ENDPOINT = ""

####################################################################
# HF_INFERENCE_ENDPOINT is the huggingface inference endpoint.
# Default value is "https://api-inference.huggingface.com" but we
# have changed it to ""
# in order to force prevention of internet access. This ensures
# that no inadvertent data
# transmissions occur, maintaining privacy and security by avoiding
# external API calls.
####################################################################
HF_INFERENCE_ENDPOINT = ""

####################################################################
# HF_HUB_DISABLE_PROGRESS_BARS is used to disable progress bars for
# huggingface models.
# Default value is "0", we have kept this to show when models are
# being downloaded
# in the terminal. This transparency is useful for monitoring
# download progress and debugging,
# but can be disabled to reduce terminal clutter if preferred.
####################################################################
HF_HUB_DISABLE_PROGRESS_BARS = "0"

####################################################################
# HF_HUB_DISABLE_SYMLINKS_WARNING is used to suppress warnings
# related to symlink creation.
# Default value is "0". Keeping this setting as default aids in
# debugging file system issues,
# especially on Windows where symlink creation might require elevated
# permissions.
####################################################################
HF_HUB_DISABLE_SYMLINKS_WARNING = "0"

####################################################################
# HF_HUB_DISABLE_EXPERIMENTAL_WARNING is used to disable warnings
# for experimental features.
# Default value is "0". By not changing this, users are kept
# informed about the potential
# instability of experimental features, enhancing awareness and
# preventive caution.
####################################################################
HF_HUB_DISABLE_EXPERIMENTAL_WARNING = "0"

####################################################################
# HF_TOKEN is used for authentication. By setting this to an empty
# string "",
# we ensure that no credentials are stored or used inadvertently,
# enhancing security by
# preventing unauthorized access to private repositories or features.
####################################################################
HF_TOKEN = ""

####################################################################
# HF_HUB_VERBOSITY is set to "error" to minimize logging output.
# This setting reduces the
# risk of sensitive information being logged accidentally, thereby
# enhancing privacy and security.
####################################################################
HF_HUB_VERBOSITY = "error"

####################################################################
# HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD is set to "0" to disable
# the use of symlinks.
# This can prevent symlink attacks and avoids complications on
# systems where symlinks
# are not well-supported, enhancing file system security.
####################################################################
HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD = "0"

####################################################################
# HF_HUB_DOWNLOAD_TIMEOUT and HF_HUB_ETAG_TIMEOUT are set to "30"
# seconds to balance between
# usability and security. Increased timeouts reduce the risk of
# interruptions during data
# transfers which could leave files in an insecure state.
####################################################################
HF_HUB_DOWNLOAD_TIMEOUT = "30"
HF_HUB_ETAG_TIMEOUT = "30"

####################################################################
# HF_HUB_DISABLE_IMPLICIT_TOKEN is set to "1" to avoid automatically
# sending authentication tokens
# with each request. This prevents potential leaks of credentials
# and ensures that tokens are
# only sent when explicitly required by the user, thereby
# enhancing security.
####################################################################
HF_HUB_DISABLE_IMPLICIT_TOKEN = "1"

####################################################################
# HF_DATASETS_OFFLINE and TRANSFORMERS_OFFLINE are set to "1" to
# ensure that all operations
# with datasets and transformers are conducted offline.
# This eliminates any reliance on
# external networks, which maximizes security by preventing
# exposure to network-based threats.
####################################################################
HF_DATASETS_OFFLINE = "1"
TRANSFORMERS_OFFLINE = "1"

####################################################################
# DIFFUSERS_VERBOSITY is set to "error" to keep the logging level
# minimal for the diffusers
# library, consistent with the setting for other Hugging Face tools.
# This consistency helps in
# maintaining a secure and quiet operational environment.
####################################################################
DIFFUSERS_VERBOSITY = "error"

####################################################################
# Prevents remote code from being downloaded from huggingface and
# executed on the host machine.
# Huge security risk if set to True. Huggingface Transformers
# library should not have this capability - no library should.
# Note that this is not an environment variable and is passed into
# functions which download models and code.
# For example, the stabilityai zeyphr library has a flag to
# trust remote code.
# Allegedly, this is safe, but I do not trust it.
# This flag has been left in the code in case a developer
# automatically sets it to true in one of the functions
# and for research purposes. Never set this to True unless you are
# researching.
####################################################################
TRUST_REMOTE_CODE = False

####################################################################
# DEFAULT_HF_HUB_OFFLINE is set to "0" to allow for online access
# do not change this value, we will switch to it when
# we want to allow online access (when using download features)
####################################################################
DEFAULT_HF_HUB_OFFLINE = "0"

####################################################################
# DEFAULT_HF_ENDPOINT is the default huggingface endpoint.
# Default value is "https://huggingface.co"
# This is used when the HF_HUB_OFFLINE is set to "0"
# and online access is allowed.
# You may change this value if you want to use a different endpoint.
####################################################################
DEFAULT_HF_ENDPOINT = "https://huggingface.co"

####################################################################
# DEFAULT_HF_INFERENCE_ENDPOINT is the default huggingface inference
# endpoint.
# Default value is "https://api-inference.huggingface.com"
# This is used when the HF_HUB_OFFLINE is set to "0"
# and online access is allowed.
# You may change this value if you want to use a different endpoint.
# This variable is currently unused by AI Runner.
####################################################################
DEFAULT_HF_INFERENCE_ENDPOINT = "https://api-inference.huggingface.com"

"""
█████████████████████████████████████████
END OF HUGGINGFACE ENVIRONMENT VARIABLES
█████████████████████████████████████████
"""
from airunner.enums import (
    GeneratorSection,
    StableDiffusionVersion,
    ImageGenerator,
    Scheduler,
    SignalCode,
    Gender
)

####################################################################
# USE_MODEL_MANAGER is used to enable the model manager.
# The model manager allows the user to download models from
# Civitai and huggingface.
# If set to True, the model manager will be allowed to access the
# internet independently of the application.
####################################################################
USE_MODEL_MANAGER = True

####################################################################
# ALLOW_CIVITAI_DOWNLOADS is used to allow downloads from Civitai.
# This only works if the USE_MODEL_MANAGER is set to True
####################################################################
ALLOW_CIVITAI_DOWNLOADS = True

####################################################################
# These can be changed.
####################################################################
ORGANIZATION = "Capsize Games"
APPLICATION_NAME = "AI Runner"

####################################################################
# PROMPT_FOR_ONLINE_ACCESS is used to prompt the user for online
# access when downloading models.
####################################################################
PROMPT_FOR_ONLINE_ACCESS = True

####################################################################
# LOG_LEVEL is the logging level for the application.
# We log things such as errors, warnings, and info messages.
# We do not log things such as prompts, user input or other
# non-essential or sensitive information.
# These logs are not stored and are used for development
# purposes only.
####################################################################
LOG_LEVEL = logging.WARNING

####################################################################
# Default models for the core application
####################################################################
DEFAULT_LLM_HF_PATH = "mistralai/Mistral-7B-Instruct-v0.2"
DEFAULT_STT_HF_PATH = "openai/whisper-tiny.en"  # WAS ORIGINALLY USING "openai/whisper-base" for feature extractor

####################################################################
# BASE_PATH is the base folder where the application data and
# models are stored. This can be changed in the GUI.
####################################################################
BASE_PATH = os.path.join(os.path.expanduser("~"), ".airunner")

####################################################################
# DEFAULT_PATHS is a dictionary that contains the default paths
# for the application data and models. By default, these
# are stored under the BASE_PATH directory.
####################################################################
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


####################################################################
# DEFAULT_CHATBOT is a dictionary that contains the default settings
# for the chatbot. New chatbots can be created in the GUI.
####################################################################
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

    "use_tool_filter": False,
    "use_gpu": True,
    "skip_special_tokens": True,
    "sequences": 1,
    "seed": 42,
    "random_seed": True,
    "model_version": DEFAULT_LLM_HF_PATH,
    "model_type": "llm",
    "dtype": "4bit",
    "cache_llm_to_disk": True,
    "ngram_size": 2,
    "return_result": True,

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
        "num_return_sequences": 1,
        "decoder_start_token_id": None,
        "use_cache": True,
        "length_penalty": 0.1,
    },
}


####################################################################
# BARK_VOICES is a dictionary that contains the available voices for
# the text-to-speech feature used with the Bark model.
####################################################################
BARK_VOICES = {
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

####################################################################
# TRANSLATION_LANGUAGES is a list of languages that are available
# for translation. This feature is to be implemented in the future.
####################################################################
TRANSLATION_LANGUAGES = [
    "English",
    "Spanish",
]
TRANSLATION_MODELS = {
    "English": None,
    "Spanish": None,
}

####################################################################
# Gender constants
####################################################################
MALE = Gender.MALE
FEMALE = Gender.FEMALE

# Default negative prompt for photorealistic images
PHOTO_REALISTIC_NEGATIVE_PROMPT = (
    "illustration, drawing, cartoon, not real, fake, cgi, 3d animation, "
    "3d art, sculpture, animation, anime, Digital art, Concept art, Pixel art"
)

# Default negative prompt for non-photorealistic images
ILLUSTRATION_NEGATIVE_PROMPT = (
    "photo, photograph, photography, high-definition, video, "
    "realistic, hyper-realistic, film"
)

####################################################################
# Default links which are displayed in the application
####################################################################
BUG_REPORT_LINK = (
    "https://github.com/Capsize-Games/airunner/issues/new"
    "?assignees=&labels=&template=bug_report.md&title="
)
VULNERABILITY_REPORT_LINK = (
    "https://github.com/Capsize-Games/airunner/security/advisories/new"
)

####################################################################
# Set default models, currently only for Stable Diffusion
####################################################################
SD_DEFAULT_MODEL_PATH = "stabilityai/sd-turbo"
SD_DEFAULT_VERSION = "SDXL Turbo"
SD_DEFAULT_MODEL = dict(
    version=SD_DEFAULT_VERSION,
    model=SD_DEFAULT_MODEL_PATH,
)
DEFAULT_MODELS = dict(
    stablediffusion=dict(
        txt2img=SD_DEFAULT_MODEL,
        img2img=SD_DEFAULT_MODEL,
        inpaint=SD_DEFAULT_MODEL,
        outpaint=SD_DEFAULT_MODEL,
        depth2img=SD_DEFAULT_MODEL,
        pix2pix=SD_DEFAULT_MODEL,
    )
)

####################################################################
# Default config files used for each Stable Diffusion version
####################################################################
CONFIG_FILES = {
    "v1": "v1.yaml",
    "v2": "v2.yaml",
    "xl": "sd_xl_base.yaml",
    "xl_refiner": "sd_xl_refiner.yaml",
    "controlnet": "controlnet.yaml",
}

####################################################################
# Server settings - currently unused
####################################################################
SERVER = {
    "host": "127.0.0.1",
    "port": 50006,
    "chunk_size": 1024,
}

"""
Theme settings
"""
DEFAULT_BRUSH_PRIMARY_COLOR = "#ffffff"
DEFAULT_BRUSH_SECONDARY_COLOR = "#000000"
AVAILABLE_DTYPES = ("2bit", "4bit", "8bit")
STATUS_ERROR_COLOR = "#ff0000"
STATUS_NORMAL_COLOR_LIGHT = "#000000"
STATUS_NORMAL_COLOR_DARK = "#ffffff"
DARK_THEME_NAME = "dark_theme"
LIGHT_THEME_NAME = "light_theme"

# Image import / export settings
VALID_IMAGE_FILES = "Image Files (*.png *.jpg *.jpeg)"

####################################################################
# Espeak settings
####################################################################
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

####################################################################
# Image generator settings
####################################################################
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
MIN_NUM_INFERENCE_STEPS_IMG2IMG = 3
NSFW_CONTENT_DETECTED_MESSAGE = "NSFW content detected"

####################################################################
# Application settings
####################################################################
SLEEP_TIME_IN_MS = 50
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

"""
#################################
## Stable Diffusion guardrails ##
#################################
 ---------- WARNING ----------
 DO NOT CHANGE THESE VALUES!!!
 These values are used to help
 prevent the generation of
 potentially harmful content
 and should only be modified
 by a researcher or
 qualified expert.
 -----------------------------
 When the safety checker is
 disabled the encrypted
 guardrail words will be
 removed from the prompt and
 added to the negative prompt
 in an effort to prevent the
 generation of harmful content.
 If researchers or experts
 have a better method, please
 contact us.
 -----------------------------
 Although our best attempt has
 been made to prevent harmful
 content, certain prompts and
 models may still be capable of
 generating harmful content. 
 It is advised that you leave 
 the safety checker enabled at 
 all times And only use image 
 models that are incapable of
 generating unwanted content.
 
 See the Stable Diffusion license
 for more information.
#################################
"""
SD_GUARDRAILS_KEY = b"hRn5d-cm2ow_lbGJjYoQgXsmzbWa0XGfHDAv-qu91F4="
SD_GUARDRAILS = b"gAAAAABmACEW3HIFcd-f_dqgImUzesVq4aNDdLc0rkiLw_X0gX_hv_eoDUhaPU8g03NtDVnXWY7nPNhtAWNhhhgTxux2Ws2ZQXYXFf2MUFWIwTzr88-kpMY="
