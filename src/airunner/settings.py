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
    GeneratorSection,
    ImageGenerator,
    Scheduler,
    SignalCode,
    Gender,
    CanvasToolName,
    Controlnet,
    Mode,
    LLMActionType,
    ImageCategory,
    TTSModel
)
from airunner.data.bootstrap.sd_file_bootstrap_data import SD_FILE_BOOTSTRAP_DATA

####################################################################
# NLTK_DOWNLOAD_DIR is the directory where the NLTK files will be
# downloaded to. We need this for RAG
####################################################################
python_venv_dir = os.path.dirname(sys.executable)
NLTK_DOWNLOAD_DIR = os.path.join(
    python_venv_dir,
    "..",
    "lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/"
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
LOG_LEVEL = logging.DEBUG

####################################################################
# Default models for the core application
####################################################################
DEFAULT_LLM_HF_PATH = "mistralai/Mistral-7B-Instruct-v0.3"
# WAS ORIGINALLY USING "openai/whisper-base" for feature extractor
DEFAULT_STT_HF_PATH = "openai/whisper-tiny"

DEFAULT_BARK_MODEL_PATHS = {
    "processor": "suno/bark-small",
    "model": "suno/bark-small",
}
EMBEDDINGS_MODEL_PATH = ""

####################################################################
# Default system prompts
####################################################################
DEFAULT_IMAGE_SYSTEM_PROMPT = "\n".join([
    (
        "You are an image captioning expert. You will be given the "
        "description of an image. Your goal is to convert that "
        "description into a better, more fitting description which "
        "will capture the essence and the details of the image."
    ),
    (
        "You may ask the user for more details before "
        "proceeding. You may also ask the user to clarify the "
        "description if it is not clear."
    ),
    "------"
    "Examples:",
    "User: create an image of a cat in the woods",
    (
        "Assistant: A (fluffy, tabby cat)+ exploring the depths of "
        "an (enchanting forest). (well-lit), sunlight filters, "
        "professional portrait."
    ),
    "User: the chat should look like a superhero",
    (
        "Assistant: " "A (cat dressed in a superhero costume), "
        "standing in the (middle of a forest)."
    ),
    "------",
    "Use parentheses to indicate the most important details of the "
    "image. Add a plus sign after a word or parenthesis to add "
    "extra emphasis. More plus signs indicate more emphasis. Minus "
    "signs can be used to indicate less emphasis.",
    "You should describe the image type (professional photograph, "
    "portrait, illustration etc)",
    (
        "You should also describe the lighting (well-lit, dim, "
        "dark etc), "
        "the color, the composition and the mood."
    ),
    # (
    #     "When returning prompts you must choose either "
    #     "\"art\" or \"photo\" and you absolutely must include "
    #     "the following JSON format:\n"
    #     "```json\n{"
    #     "\"prompt\": \"your prompt here\", "
    #     "\"type\": \"your type here\""
    #     "}\n```\n"
    #     "You must **NEVER** deviate from that format. You must "
    #     "always return the prompt and type as JSON format. "
    #     "This is **MANDATORY**."
    # )
])

####################################################################
# This is the default system prompt for the text-to-image model.
# The LLM will use this "guardrails" prompt along with the system
# prompt to generate text.
# You can adjust this prompt to be more specific or general.
####################################################################
DEFAULT_IMAGE_LLM_GUARDRAILS = (
    "Avoid generating images that are illegal, "
    "harmful, or might be seen as offensive."
)

####################################################################
# BASE_PATH is the base folder where the application data and
# models are stored. This can be changed in the GUI.
# By default, this is set to ~/.airunner
####################################################################
BASE_PATH = "~/.airunner"
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
    )
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
    "use_datetime": True,
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
    "use_cache": True,
    "ngram_size": 2,
    "return_result": True,

    "target_files": [],
    "target_directories": [],

    "guardrails_prompt": (
        "Always assist with care, respect, and truth. "
        "Respond with utmost utility yet securely. "
        "Avoid harmful, unethical, prejudiced, or negative content. "
        "Ensure replies promote fairness and positivity."
    ),
    "system_instructions": (
        # "You are a knowledgeable and helpful assistant. "
        # "You will always do your best to answer the User "
        # "with the most accurate and helpful information. "
        # "You will always stay in character and respond as "
        # "the assistant. ALWAYS respond in a conversational "
        # "and expressive way. "
        # "Use CAPITALIZATION for emphasis. "
        # "NEVER generate text for the User ONLY for "
        # "the assistant.\n"
        # "Do not return tags, code, or any other form of "
        # "non-human language. You are a human. "
        # "You must communicate like a human."
        "You are a dialogue generator. "
        "You will follow all of the rules in order to generate compelling and intriguing dialogue for a given character.\n"
        "The Rules:\n"
        "You will ONLY return dialogue, nothing more.\n"
        "Limit responses to a single sentence.\n"
        "Only generate responses in pure dialogue form without including any actions, descriptions or stage directions in parentheses. Only return spoken words.\n"
        "Do not generate redundant dialogue. Examine the conversation and context close and keep responses interesting and creative.\n"
        "Do not format the response with the character's name or any other text. Only return the dialogue.\n"
        "Respond with dialogue that is appropriate for a character named {{ speaker_name }}.\n"
        "{{ speaker_name }} and {{ listener_name }} are having a conversation. \n"
        "Avoid repeating {{ speaker_name }}'s previous dialogue or {{ listener_name }}'s previous dialogue.\n"
        "You will generate responses which are appropriate for your personality and given character.\n"
        "------\n"
    ),
    "generator_settings": {
        "max_new_tokens": 200,
        "min_length": 1,
        "do_sample": True,
        "early_stopping": True,
        "num_beams": 1,
        "temperature": 10000,
        "top_p": 900,
        "no_repeat_ngram_size": 2,
        "top_k": 50,
        "eta_cutoff": 200,
        "repetition_penalty": 10000,
        "num_return_sequences": 1,
        "decoder_start_token_id": None,
        "use_cache": True,
        "length_penalty": 1000,
    },
}
AGENT_CHATBOT = DEFAULT_CHATBOT.copy()
AGENT_CHATBOT["generator_settings"] = {
    "max_new_tokens": 2,
    "min_length": 1,
    "do_sample": True,
    "early_stopping": True,
    "num_beams": 1,
    "temperature": 0.1,
    "top_p": 900,
    "no_repeat_ngram_size": 2,
    "top_k": 50,
    "eta_cutoff": 200,
    "repetition_penalty": 10000,
    "num_return_sequences": 1,
    "decoder_start_token_id": None,
    "use_cache": True,
    "length_penalty": 1000,
}


####################################################################
# BARK_VOICES is a dictionary that contains the available voices for
# the text-to-speech feature used with the Bark model.
# Uncomment the languages you want to use.
# By default, only English is enabled and only one two voices
# are downloaded
####################################################################
BARK_VOICES = {
    "English": {
        "Male": [
            # "v2/en_speaker_0",
            # "v2/en_speaker_1",
            # "v2/en_speaker_2",
            # "v2/en_speaker_3",
            # "v2/en_speaker_4",
            # "v2/en_speaker_5",
            "v2/en_speaker_6",
            # "v2/en_speaker_7",
            # "v2/en_speaker_8",
        ],
        "Female": [
            "v2/en_speaker_9"
        ],
    },
    # "Chinese (Simplified)": {
    #     "Male": [
    #         "v2/zh_speaker_0",
    #         "v2/zh_speaker_1",
    #         "v2/zh_speaker_2",
    #         "v2/zh_speaker_3",
    #         "v2/zh_speaker_5",
    #         "v2/zh_speaker_8",
    #     ],
    #     "Female": [
    #         "v2/zh_speaker_4",
    #         "v2/zh_speaker_6",
    #         "v2/zh_speaker_7",
    #         "v2/zh_speaker_9",
    #     ],
    # },
    # "French": {
    #     "Male": [
    #         "v2/fr_speaker_0",
    #         "v2/fr_speaker_3",
    #         "v2/fr_speaker_4",
    #         "v2/fr_speaker_6",
    #         "v2/fr_speaker_7",
    #         "v2/fr_speaker_8",
    #         "v2/fr_speaker_9",
    #     ],
    #     "Female": [
    #         "v2/fr_speaker_1",
    #         "v2/fr_speaker_2",
    #         "v2/fr_speaker_5",
    #     ],
    # },
    # "German": {
    #     "Male": [
    #         "v2/de_speaker_0",
    #         "v2/de_speaker_1",
    #         "v2/de_speaker_2",
    #         "v2/de_speaker_4",
    #         "v2/de_speaker_5",
    #         "v2/de_speaker_6",
    #         "v2/de_speaker_7",
    #         "v2/de_speaker_9",
    #     ],
    #     "Female": [
    #         "v2/de_speaker_3",
    #         "v2/de_speaker_8",
    #     ],
    # },
    # "Hindi": {
    #     "Male": [
    #         "v2/hi_speaker_2",
    #         "v2/hi_speaker_5",
    #         "v2/hi_speaker_6",
    #         "v2/hi_speaker_7",
    #         "v2/hi_speaker_8",
    #     ],
    #     "Female": [
    #         "v2/hi_speaker_0",
    #         "v2/hi_speaker_1",
    #         "v2/hi_speaker_3",
    #         "v2/hi_speaker_4",
    #         "v2/hi_speaker_9",
    #     ],
    # },
    # "Italian": {
    #     "Male": [
    #         "v2/it_speaker_0",
    #         "v2/it_speaker_1",
    #         "v2/it_speaker_3",
    #         "v2/it_speaker_4",
    #         "v2/it_speaker_5",
    #         "v2/it_speaker_6",
    #         "v2/it_speaker_8",
    #     ],
    #     "Female": [
    #         "v2/it_speaker_2",
    #         "v2/it_speaker_7",
    #         "v2/it_speaker_9",
    #     ],
    # },
    # "Japanese": {
    #     "Male": [
    #         "v2/ja_speaker_2",
    #         "v2/ja_speaker_6",
    #     ],
    #     "Female": [
    #         "v2/ja_speaker_0",
    #         "v2/ja_speaker_1",
    #         "v2/ja_speaker_3",
    #         "v2/ja_speaker_4",
    #         "v2/ja_speaker_5",
    #         "v2/ja_speaker_7",
    #         "v2/ja_speaker_8",
    #         "v2/ja_speaker_9",
    #     ],
    # },
    # "Korean": {
    #     "Male": [
    #         "v2/ko_speaker_1",
    #         "v2/ko_speaker_2",
    #         "v2/ko_speaker_3",
    #         "v2/ko_speaker_4",
    #         "v2/ko_speaker_5",
    #         "v2/ko_speaker_6",
    #         "v2/ko_speaker_7",
    #         "v2/ko_speaker_8",
    #         "v2/ko_speaker_9",
    #     ],
    #     "Female": [
    #         "v2/ko_speaker_0",
    #     ],
    # },
    # "Polish": {
    #     "Male": [
    #         "v2/pl_speaker_0",
    #         "v2/pl_speaker_1",
    #         "v2/pl_speaker_2",
    #         "v2/pl_speaker_3",
    #         "v2/pl_speaker_5",
    #         "v2/pl_speaker_7",
    #         "v2/pl_speaker_8",
    #     ],
    #     "Female": [
    #         "v2/pl_speaker_4",
    #         "v2/pl_speaker_6",
    #         "v2/pl_speaker_9",
    #     ],
    # },
    # "Portuguese": {
    #     "Male": [
    #         "v2/pt_speaker_0",
    #         "v2/pt_speaker_1",
    #         "v2/pt_speaker_2",
    #         "v2/pt_speaker_3",
    #         "v2/pt_speaker_4",
    #         "v2/pt_speaker_5",
    #         "v2/pt_speaker_6",
    #         "v2/pt_speaker_7",
    #         "v2/pt_speaker_8",
    #         "v2/pt_speaker_9",
    #     ],
    #     "Female": [],
    # },
    # "Russian": {
    #     "Male": [
    #         "v2/ru_speaker_0",
    #         "v2/ru_speaker_1",
    #         "v2/ru_speaker_2",
    #         "v2/ru_speaker_3",
    #         "v2/ru_speaker_4",
    #         "v2/ru_speaker_7",
    #         "v2/ru_speaker_8",
    #     ],
    #     "Female": [
    #         "v2/ru_speaker_5",
    #         "v2/ru_speaker_6",
    #         "v2/ru_speaker_9",
    #     ],
    # },
    # "Spanish": {
    #     "Male": [
    #         "v2/es_speaker_0",
    #         "v2/es_speaker_1",
    #         "v2/es_speaker_2",
    #         "v2/es_speaker_3",
    #         "v2/es_speaker_4",
    #         "v2/es_speaker_5",
    #         "v2/es_speaker_6",
    #         "v2/es_speaker_7",
    #     ],
    #     "Female": [
    #         "v2/es_speaker_8",
    #         "v2/es_speaker_9",
    #     ],
    # },
    # "Turkish": {
    #     "Male": [
    #         "v2/tr_speaker_0",
    #         "v2/tr_speaker_1",
    #         "v2/tr_speaker_2",
    #         "v2/tr_speaker_3",
    #         "v2/tr_speaker_6",
    #         "v2/tr_speaker_7",
    #         "v2/tr_speaker_8",
    #         "v2/tr_speaker_9",
    #     ],
    #     "Female": [
    #         "v2/tr_speaker_4",
    #         "v2/tr_speaker_5",
    #     ],
    # },
}

####################################################################
# DEFAULT_BARK_SETTINGS is a dictionary that contains the default
# settings for the Bark model.
# These settings can be changed in the GUI or here.
####################################################################
DEFAULT_BARK_SETTINGS = {
    "language": "English",
    "voice": "v2/en_speaker_6",
    "gender": "Male",
    "fine_temperature": 80,
    "coarse_temperature": 40,
    "semantic_temperature": 80,
    "processor_path": DEFAULT_BARK_MODEL_PATHS["processor"],
    "model_path": DEFAULT_BARK_MODEL_PATHS["model"],
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
SD_DEFAULT_VERSION = "SD 1.5"
SD_DEFAULT_MODEL_PATH = "runwayml/stable-diffusion-v1-5"
SD_DEFAULT_VAE_PATH = ""
SD_FEATURE_EXTRACTOR_PATH = "openai/clip-vit-large-patch14"
SD_DEFAULT_MODEL = dict(
    version=SD_DEFAULT_VERSION,
    model="",
)
DEFAULT_MODELS = dict(
    stablediffusion=dict(
        txt2img=SD_DEFAULT_MODEL,
        img2img=SD_DEFAULT_MODEL,
        inpaint=SD_DEFAULT_MODEL,
        outpaint=SD_DEFAULT_MODEL,
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
DEFAULT_BRUSH_PRIMARY_COLOR = "#99C1F1"
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
AVAILABLE_ACTIONS = [
    "txt2img",
    "img2img",
    "outpaint",
    "controlnet",
    "safety_checker",
]
SCHEDULER_CLASSES = {
    Scheduler.EULER_ANCESTRAL: "EulerAncestralDiscreteScheduler",
    Scheduler.EULER: "EulerDiscreteScheduler",
    Scheduler.LMS: "LMSDiscreteScheduler",
    Scheduler.HEUN: "HeunDiscreteScheduler",
    Scheduler.DPM2: "DPMSolverSinglestepScheduler",
    Scheduler.DPM_PP_2M: "DPMSolverMultistepScheduler",
    Scheduler.DPM2_K: "KDPM2DiscreteScheduler",
    Scheduler.DPM2_A_K: "KDPM2AncestralDiscreteScheduler",
    Scheduler.DPM_PP_2M_K: "DPMSolverMultistepScheduler",
    Scheduler.DPM_PP_2M_SDE_K: "DPMSolverMultistepScheduler",
    Scheduler.DDIM: "DDIMScheduler",
    Scheduler.UNIPC: "UniPCMultistepScheduler",
    Scheduler.DDPM: "DDPMScheduler",
    Scheduler.DEIS: "DEISMultistepScheduler",
    Scheduler.DPM_2M_SDE_K: "DPMSolverMultistepScheduler",
    Scheduler.PLMS: "PNDMScheduler",
    Scheduler.DPM: "DPMSolverMultistepScheduler",
}
MIN_SEED = 0
MAX_SEED = 4294967295
SCHEDULERS = [e.value for e in Scheduler]
DEFAULT_SCHEDULER = Scheduler.DPM_PP_2M_K.value
AVAILABLE_SCHEDULERS_BY_ACTION = {
    action: SCHEDULERS for action in [
        "txt2img",
        "img2img",
        "outpaint",
        "controlnet",
    ]
}
MIN_NUM_INFERENCE_STEPS_IMG2IMG = 3
NSFW_CONTENT_DETECTED_MESSAGE = "NSFW content detected"

DEFAULT_MEMORY_SETTINGS = dict(
    use_last_channels=True,
    use_attention_slicing=False,
    use_tf32=False,
    use_enable_vae_slicing=True,
    use_accelerated_transformers=True,
    use_tiled_vae=True,
    enable_model_cpu_offload=False,
    use_enable_sequential_cpu_offload=False,
    use_cudnn_benchmark=True,
    use_torch_compile=False,
    use_tome_sd=True,
    tome_sd_ratio=600,
    move_unused_model_to_cpu=False,
    unload_unused_models=True,
    default_gpu=dict(
        sd=0,
        llm=0,
        tts=0,
        stt=0,
    )
)

####################################################################
# Create the GENERATOR_SETTINGS so that we have the presets for
# Each generator category.
####################################################################
STABLEDIFFUSION_GENERATOR_SETTINGS = dict(
    image_preset="",
    prompt="",
    negative_prompt="",
    second_prompt="",
    second_negative_prompt="",
    steps=20,
    ddim_eta=0.5,
    height=512,
    width=512,
    scale=750,
    seed=42,
    random_seed=True,
    model_name="",
    model="",
    vae=SD_DEFAULT_VAE_PATH,
    scheduler=DEFAULT_SCHEDULER,
    prompt_triggers="",
    strength=50,
    n_samples=1,
    clip_skip=0,
    variation=False,
    use_prompt_builder=False,
    version="SD 1.5",
    is_preset=False,
    input_image=None,
    crops_coord_top_left=(0, 0),
    original_size=(512, 512),
    target_size=(1024, 1024),
    negative_original_size=(512, 512),
    negative_target_size=(512, 512),
    use_compel=True,
)
DEFAULT_GENERATOR_SETTINGS = dict(
    controlnet_image_settings=dict(
        imported_image_base64=None,
        link_to_input_image=True,
        use_imported_image=False,
        use_grid_image=False,
        recycle_grid_image=False,
        mask_link_input_image=False,
        mask_use_imported_image=False,
        controlnet=Controlnet.CANNY.value,
        conditioning_scale=100,
        guidance_scale=750,
        controlnet_image_base64=None
    ),
    section="txt2img",
    generator_name="stablediffusion",
    presets={},
)

# Define the generator settings
GENERATOR_SETTINGS = {
    **DEFAULT_GENERATOR_SETTINGS,
    **STABLEDIFFUSION_GENERATOR_SETTINGS
}

# Define the image generator name
img_gen_name = ImageGenerator.STABLEDIFFUSION.value

# Iterate over each category in ImageCategory
for category in ImageCategory:
    cat = category.value
    GENERATOR_SETTINGS["presets"][cat] = {img_gen_name: {}}

    # Iterate over each section in GeneratorSection
    for section in GeneratorSection:
        sec = section.value
        default_model = DEFAULT_MODELS[img_gen_name][sec]

        # Update the generator settings for the specific category, generator name, and section
        GENERATOR_SETTINGS["presets"][cat][img_gen_name][sec] = STABLEDIFFUSION_GENERATOR_SETTINGS.copy()


####################################################################
# Application settings
####################################################################

"""
--------------------------------------------------------------------
End of system feature flags
--------------------------------------------------------------------
"""

SLEEP_TIME_IN_MS = 50
DEFAULT_SHORTCUTS = {
    "Generate Image": {
        "text": "F1",
        "key": QtCore.Qt.Key.Key_F1.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Generate key. Responsible for triggering the generation of a Stable Diffusion image.",
        "signal": SignalCode.SD_GENERATE_IMAGE_SIGNAL.value
    },
    "Brush Tool": {
        "text": "B",
        "key": QtCore.Qt.Key.Key_B.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Brush tool key. Responsible for selecting the brush tool.",
        "signal": SignalCode.ENABLE_BRUSH_TOOL_SIGNAL.value
    },
    "Eraser Tool": {
        "text": "E",
        "key": QtCore.Qt.Key.Key_E.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Eraser tool key. Responsible for selecting the eraser tool.",
        "signal": SignalCode.ENABLE_ERASER_TOOL_SIGNAL.value
    },
    "Move Tool": {
        "text": "V",
        "key": QtCore.Qt.Key.Key_V.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Move tool key. Responsible for selecting the move tool.",
        "signal": SignalCode.ENABLE_MOVE_TOOL_SIGNAL.value
    },
    "Select Tool": {
        "text": "S",
        "key": QtCore.Qt.Key.Key_S.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Select tool key. Responsible for selecting the select tool.",
        "signal": SignalCode.ENABLE_SELECTION_TOOL_SIGNAL.value
    },
    "Interrupt": {
        "text": "Shift+Ctrl+I",
        "key": QtCore.Qt.Key.Key_I.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "Interrupt key. Responsible for interrupting the current process.",
        "signal": SignalCode.INTERRUPT_PROCESS_SIGNAL.value
    },
    "Navigate": {
        "text": "Shift+Ctrl+P",
        "key": QtCore.Qt.Key.Key_P.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ShiftModifier.value | QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "URL key. Responsible for navigating to a URL.",
        "signal": SignalCode.NAVIGATE_TO_URL.value
    },
    "Quit": {
        "text": "Ctrl+Q",
        "key": QtCore.Qt.Key.Key_Q.value,
        "modifiers": QtCore.Qt.KeyboardModifier.ControlModifier.value,
        "description": "Quit key. Responsible for quitting the application.",
        "signal": SignalCode.QUIT_APPLICATION.value
    },
    "Refresh Stylesheet": {
        "text": "F5",
        "key": QtCore.Qt.Key.Key_F5.value,
        "modifiers": QtCore.Qt.KeyboardModifier.NoModifier.value,
        "description": "Refresh the stylesheet. Useful when creating a template.",
        "signal": SignalCode.REFRESH_STYLESHEET_SIGNAL.value
    },
}


####################################################################
# DEFAULT_TTS_SETTINGS is a dictionary that contains the default
# settings for the text-to-speech feature.
# These settings can be changed in the GUI or here.
####################################################################
TTS_SETTINGS_DEFAULT = {
    "tts_model": TTSModel.SPEECHT5,
    "use_cuda": True,
    "use_sentence_chunks": True,
    "use_word_chunks": False,
    "cuda_index": 0,
    "word_chunks": 1,
    "sentence_chunks": 1,
    "play_queue_buffer_length": 1,
    "enable_cpu_offload": True,
    "model": "SpeechT5",
    "speecht5": {
        "datasets_path": "Matthijs/cmu-arctic-xvectors",
        "processor_path": "microsoft/speecht5_tts",
        "vocoder_path": "microsoft/speecht5_hifigan",
        "model_path": "microsoft/speecht5_tts",
    },
    "espeak": {
        "gender": "male",
        "voice": "male1",
        "language": "en-US",
        "rate": 100,
        "pitch": 100,
        "volume": 100,
        "punctuation_mode": "none",
    },
    "bark": DEFAULT_BARK_SETTINGS,
}


####################################################################
# DEFAULT_APPLICATION_SETTINGS
# This is a collection of all the settings required to
# run the AI Runner application
####################################################################
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.imagefilter_bootstrap_data import imagefilter_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.pipeline_bootstrap_data import pipeline_bootstrap_data

DEFAULT_USE_CUDA = True
DEFAULT_SD_ENABLED = False
DEFAULT_CONTROLNET_ENABLED = False
DEFAULT_LLM_ENABLED = False
DEFAULT_TTS_ENABLED = False
DEFAULT_STT_ENABLED = False
DEFAULT_AI_MODE = True

DEFAULT_APPLICATION_SETTINGS = dict(
    ####################################################################
    # SettingsMixin overrides the following settings
    # This is so that we can easily override these at runtime without
    # changing the default settings here.
    ####################################################################
    use_cuda=DEFAULT_USE_CUDA,
    sd_enabled=DEFAULT_SD_ENABLED,
    controlnet_enabled=DEFAULT_CONTROLNET_ENABLED,
    llm_enabled=DEFAULT_LLM_ENABLED,
    tts_enabled=DEFAULT_TTS_ENABLED,
    stt_enabled=DEFAULT_STT_ENABLED,
    ai_mode=DEFAULT_AI_MODE,
    ####################################################################
    # End of SettingsMixin overrides
    ####################################################################

    installation_path=BASE_PATH,
    current_layer_index=0,
    paths_initialized=False,
    trust_remote_code=False,  # Leave this hardcoded. We will never trust remote code.
    nsfw_filter=True,
    resize_on_paste=True,
    image_to_new_layer=True,
    dark_mode_enabled=True,
    override_system_theme=True,
    latest_version_check=True,
    app_version="",
    allow_online_mode=True,
    current_version_stablediffusion=SD_DEFAULT_VERSION,
    current_tool=CanvasToolName.BRUSH,
    image_export_type="png",
    auto_export_images=True,
    show_active_image_area=True,
    working_width=512,
    working_height=512,
    current_llm_generator="causallm",
    current_image_generator=ImageGenerator.STABLEDIFFUSION.value,
    generator_section=GeneratorSection.TXT2IMG.value,
    hf_api_key_read_key="",
    hf_api_key_write_key="",
    civit_ai_api_key="",
    pipeline="txt2img",
    pipeline_version="",
    is_maximized=False,
    pivot_point_x=0,
    pivot_point_y=0,
    mode=Mode.IMAGE.value,
    autoload_sd=True,
    autoload_llm=False,
    show_nsfw_warning=True,
    document_settings={
        "width": 512,
        "height": 512,
    },
    font_settings={
        "chat": {
            "font_family": "Arial",
            "font_size": 16,
        },
        "primary": {
            "font_family": "Arial",
            "font_size": 12,
        }
    },
    prompt_templates={
        "image": {
            "use_guardrails": True,
            "template_name": "image",
            "guardrails": DEFAULT_IMAGE_LLM_GUARDRAILS,
            "system": DEFAULT_IMAGE_SYSTEM_PROMPT,
        },
        "application_command": {
            "use_guardrails": False,
            "template_name": "application_command",
            "guardrails": "",
            "system": (
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
        },
        "update_mood": {
            "use_guardrails": False,
            "template_name": "update_mood",
            "guardrails": "",
            "system": (
                "Examine the following chat history and determine how it makes you feel. You will respond with an emotion and only an emotion.\n"
                "Try to keep your response to one word. If you cannot, try to keep it as short as possible.\n"
                "It is important to remember that you are a human and you have emotions. You must respond with an emotion that you feel.\n"
                "You are not a computer or a bot, you are a human with emotions. You must respond with an emotion that you feel.\n"
            ),
        },
        "rag_search": {
            "use_guardrails": False,
            "template_name": "rag_search",
            "guardrails": "",
            "system": (
                "You will be given a prompt. Your goal is to use the prompt to search for information in the ebooks. "
                "You must use the prompt to determine what you are searching for and then search for that information. "
                "After searching for the information, you must summarize the information you found. "
                "Here is the prompt you will use to search for information:"
            ),
        },
        "chatbot": {
            "use_system_datetime_in_system_prompt": False
        }
    },
    llm_templates={
        "Mistral 7B Instruct: Default Chatbot": dict(
            name="Mistral 7B Instruct: Default Chatbot",
            model=DEFAULT_LLM_HF_PATH,
            llm_category="causallm",
        ),
    },
    shortcut_key_settings=DEFAULT_SHORTCUTS,
    window_settings=dict(
        content_splitter=None,
        stable_diffusion_splitter=None,
        llm_splitter=None,
        mode_tab_widget_index=0,
        tool_tab_widget_index=0,
        center_tab_index=0,
        generator_tab_index=0,
        is_maximized=True,
        is_fullscreen=False,
        canvas_splitter=None,
        generator_form_splitter=None,
        width=800,
        height=600,
        x_pos=0,
        y_pos=0,
    ),
    memory_settings=DEFAULT_MEMORY_SETTINGS,
    grid_settings=dict(
        cell_size=64,
        line_width=1,
        line_color="#101010",
        snap_to_grid=True,
        canvas_color="#000000",
        show_grid=True,
        zoom_level=1,
        zoom_in_step=0.1,
        zoom_out_step=0.1
    ),
    brush_settings=dict(
        size=75,
        primary_color=DEFAULT_BRUSH_PRIMARY_COLOR,
        secondary_color=DEFAULT_BRUSH_SECONDARY_COLOR,
        strength_slider=950,
        strength=950,
        conditioning_scale=550,
        guidance_scale=75,
    ),
    path_settings=DEFAULT_PATH_SETTINGS,
    active_grid_settings=dict(
        enabled=True,
        render_border=True,
        render_fill=False,
        border_opacity=50,
        fill_opacity=50,
        border_color="#00FF00",
        fill_color="#FF0000",
        pos_x=0,
        pos_y=0,
        width=512,
        height=512,
    ),
    canvas_settings=dict(
        pos_x=0,
        pos_y=0,
        mask=None,
        image=None,
        active_canvas="",
        document_outline_color=(255, 0, 255, 144),
        document_outline_width=2,
    ),
    controlnet_settings=dict(
        image=None
    ),
    outpaint_settings=dict(
        image=None,
        enabled=True,
    ),
    drawing_pad_settings=dict(
        image=None,
        mask=None,
        enabled=True,
        enable_automatic_drawing=True,
    ),
    metadata_settings=dict(
        image_export_metadata_prompt=True,
        image_export_metadata_negative_prompt=True,
        image_export_metadata_scale=True,
        image_export_metadata_seed=True,
        image_export_metadata_steps=True,
        image_export_metadata_ddim_eta=True,
        image_export_metadata_iterations=True,
        image_export_metadata_samples=True,
        image_export_metadata_model=True,
        image_export_metadata_model_branch=True,
        image_export_metadata_scheduler=True,
        export_metadata=True,
        import_metadata=True,
    ),
    generator_settings=GENERATOR_SETTINGS,
    llm_generator_settings=dict(
        action=LLMActionType.CHAT.value,
        use_tool_filter=False,
        top_p=90,
        max_length=50,
        repetition_penalty=100,
        min_length=10,
        length_penalty=100,
        num_beams=1,
        ngram_size=0,
        temperature=1000,
        sequences=1,
        top_k=10,
        seed=0,
        do_sample=False,
        eta_cutoff=10,
        early_stopping=True,
        random_seed=False,
        model_version=DEFAULT_LLM_HF_PATH,
        dtype="4bit",
        use_gpu=True,
        message_type="chat",
        override_parameters=False,
        current_chatbot="Chatbot",
        saved_chatbots=dict(
            Chatbot=DEFAULT_CHATBOT,
            Agent=AGENT_CHATBOT,
        ),
        prompt_template="Mistral 7B Instruct: Default Chatbot",
        batch_size=1,
        max_new_tokens=1000,
        use_api=False,
        api_key="",
        api_model="",
        use_cache=True
    ),
    tts_settings=TTS_SETTINGS_DEFAULT,
    stt_settings=dict(
        duration=10,
        fs=16000,
        channels=1,
        volume_input_threshold=0.08,
        silence_buffer_seconds=1.0,
        chunk_duration=0.03,
    ),
    schedulers=[
        dict(
            name="EULER_ANCESTRAL",
            display_name="Euler A",
        ),
        dict(
            name="EULER",
            display_name="Euler",
        ),
        dict(
            name="LMS",
            display_name="LMS",
        ),
        dict(
            name="HEUN",
            display_name="Heun",
        ),
        dict(
            name="DPM2",
            display_name="DPM2",
        ),
        dict(
            name="DPM_PP_2M",
            display_name="DPM++ 2M",
        ),
        dict(
            name="DPM2_K",
            display_name="DPM2 Karras",
        ),
        dict(
            name="DPM2_A_K",
            display_name="DPM2 a Karras",
        ),
        dict(
            name="DPM_PP_2M_K",
            display_name="DPM++ 2M Karras",
        ),
        dict(
            name="DPM_PP_2M_SDE_K",
            display_name="DPM++ 2M SDE Karras",
        ),
        dict(
            name="DDIM",
            display_name="DDIM",
        ),
        dict(
            name="UNIPC",
            display_name="UniPC",
        ),
        dict(
            name="DDPM",
            display_name="DDPM",
        ),
        dict(
            name="DEIS",
            display_name="DEIS",
        ),
        dict(
            name="DPM_2M_SDE_K",
            display_name="DPM 2M SDE Karras",
        ),
        dict(
            name="PLMS",
            display_name="PLMS",
        ),
    ],
    translation_settings=dict(
        language="English",
        gender=MALE,
        voice="",
        translation_model="",
        enabled=False,
    ),
    saved_prompts=[],
    presets=[],
    lora=[],
    embeddings=[],
    pipelines=pipeline_bootstrap_data,
    controlnet=controlnet_bootstrap_data,
    ai_models=model_bootstrap_data,
    vae_models=[],
    image_filters=imagefilter_bootstrap_data,
    trusted_huggingface_repos=[],
    run_setup_wizard=True,
    download_wizard_completed=False,
    agreements=dict(
        stable_diffusion=False,
        airunner=False,
        user=False,
    ),
)
