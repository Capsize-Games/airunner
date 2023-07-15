import logging
import os
import platform
from enum import Enum

PLATFORM = platform.system()
try:
    USER = os.environ['USER']
except KeyError:
    USER = None

if not USER:
    try:
        USER = os.environ['USERNAME']
    except KeyError:
        USER = None
HOME = os.path.expanduser("~")

if not USER:
    HOME = os.path.join("/app")

SD_DIR = os.path.join(HOME, "stablediffusion")
STABILITYAI_DIR = os.path.join("stabilityai")
RUNWAYML_DIR = os.path.join("runwayml")
V1_DIR = os.path.join(SD_DIR, "v1")
APPLICATION_ID = "runai"

# SCHEDULERS
EULER_ANCESTRAL = "Euler a"
EULER = "Euler"
LMS = "LMS"
HEUN = "Heun"
DPM2 = "DPM2"
DPM_PP_2M = "DPM++ 2M"
DPM2_K = "DPM2 Karras"
DPM2_A_K = "DPM2 a Karras"
DPM_PP_2M_K = "DPM++ 2M Karras"
DPM_PP_2M_SDE_K = "DPM++ 2M SDE Karras"
DDIM = "DDIM"
UNIPC = "UniPC"
DDPM = "DDPM"
DEIS = "DEIS"
DPM_2M_SDE_K = "DPM 2M SDE Karras"
PLMS = "PLMS"

DDIMInverse = "DDIM Inverse"
IPNM = "IPNM"
REPAINT = "RePaint"
KVE = "Karras Variance exploding"
VESDE = "VE-SDE"
VPSDE = "VP-SDE"
VQDIFFUSION = "VQ Diffusion"

SCHEDULERS = [
    EULER_ANCESTRAL,
    EULER,
    LMS,
    HEUN,
    DPM2,
    DPM_PP_2M,
    DPM2_K,
    DPM2_A_K,
    DPM_PP_2M_K,
    DPM_PP_2M_SDE_K,
    DDIM,
    PLMS,
    UNIPC,
    DDPM,
    DEIS,
    DPM_2M_SDE_K,

    # DDIMInverse,
    # IPNM,
    # REPAINT,
    # KVE,
    # VESDE,
    # VPSDE,
    # VQDIFFUSION,
]
AVAILABLE_SCHEDULERS_BY_ACTION = {
    "txt2img": SCHEDULERS,
    "img2img": SCHEDULERS,
    "depth2img": SCHEDULERS,
    "pix2pix": SCHEDULERS,
    "vid2vid": SCHEDULERS,
    "outpaint": SCHEDULERS,
    "upscale": [EULER],
    "superresolution": [
        DDIM,
        LMS,
        PLMS
    ],
    "controlnet": SCHEDULERS,
    "txt2vid": SCHEDULERS,
    "kandinsky_txt2img": [
        EULER_ANCESTRAL,
        DPM2_A_K,
        DDPM,
        DPM_PP_2M,
        DPM_PP_2M_K,
        DPM_2M_SDE_K,
        DPM_PP_2M_SDE_K,
        DDIM,
    ],
    "kandinsky_img2img": [
        DDPM,
        DPM_PP_2M,
        DPM_PP_2M_K,
        DPM_2M_SDE_K,
        DPM_PP_2M_SDE_K,
        DDIM,
    ],
    "kandinsky_outpaint": [
        EULER_ANCESTRAL,
        DPM2_A_K,
        DDPM,
        DPM_PP_2M,
        DPM_PP_2M_K,
        DPM_2M_SDE_K,
        DPM_PP_2M_SDE_K,
        DDIM,
    ],
    "shapegif_txt2img": [
        HEUN,
    ],
    "shapegif_img2img": [
        HEUN,
    ]
}
UPSCALERS = ["None", "Lanczos"]
MODELS = {
    "stablediffusion_generate": {
        "Stable Diffusion V2.1 512": {
            "path": "stabilityai/stable-diffusion-2",
            "branch": "fp16",
        },
        "Stable Diffusion V2.1 768": {
            "path": "stabilityai/stable-diffusion-2-1",
            "branch": "fp16",
        },
        "Stable Diffusion V1.5": {
            "path": "runwayml/stable-diffusion-v1-5",
            "branch": "fp16",
        },
        "All In One Pixel Model": {
            "path": "PublicPrompts/All-In-One-Pixel-Model",
            "branch": "main",
            "triggers": [
                "pixelsprite",
                "16bitscene"
            ]
        },
        "SD PixelArt SpriteSheet Generator": {
            "path": "Onodofthenorth/SD_PixelArt_SpriteSheet_Generator",
            "branch": "main",
            "triggers": [
                "PixelartFSS",
                "PixelartRSS",
                "PixelartBSS",
                "PixelartLSS"
            ]
        },
        "Openjourney v4": {
            "path": "prompthero/openjourney-v4",
            "branch": "main"
        },
        "SynthwavePunk-v2": {
            "path": "ItsJayQz/SynthwavePunk-v2",
            "branch": "main",
            "triggers": [
                "snthwve style",
                "nvinkpunk"
            ]
        },
        "Inkpunk Diffusion": {
          "path": "Envvi/Inkpunk-Diffusion",
            "branch": "main",
            "triggers": [
                "nvinkpunk",
            ]
        },
        "Anything v3": {
            "path": "Linaqruf/anything-v3.0",
            "branch": "main"
        },
        "Stable Diuffions XL 0.9":
        {
            "path": "stabilityai/stable-diffusion-xl-base-0.9",
            "branch": "fp16"
        },
    },
    "stablediffusion_outpaint": {
        "Stable Diffusion Inpaint V2": {
            "path": "stabilityai/stable-diffusion-2-inpainting",
            "branch": "fp16",
        },
        "Stable Diffusion Inpaint V1": {
            "path": "runwayml/stable-diffusion-inpainting",
            "branch": "fp16",
        },
    },
    "stablediffusion_depth2img": {
        "Stable Diffusion Depth2Img": {
            "path": "stabilityai/stable-diffusion-2-depth",
            "branch": "fp16",
        },
    },
    "stablediffusion_ksuperresolution": {
        "Keras Super Resolution": {
            "path": "keras-io/super-resolution",
            "branch": "main",
        },
    },
    "stablediffusion_controlnet": {
        "Stable Diffusion V1": {
            "path": "runwayml/stable-diffusion-v1-5",
            "branch": "fp16",
        },
        "All In One Pixel Model": {
            "path": "PublicPrompts/All-In-One-Pixel-Model",
            "branch": "main",
            "triggers": [
                "pixelsprite",
                "16bitscene"
            ]
        },
        "SD PixelArt SpriteSheet Generator": {
            "path": "Onodofthenorth/SD_PixelArt_SpriteSheet_Generator",
            "branch": "main",
            "triggers": [
                "PixelartFSS",
                "PixelartRSS",
                "PixelartBSS",
                "PixelartLSS"
            ]
        },
        "SynthwavePunk-v2": {
            "path": "ItsJayQz/SynthwavePunk-v2",
            "branch": "main",
            "triggers": [
                "snthwve style",
                "nvinkpunk"
            ]
        },
        "Inkpunk Diffusion": {
          "path": "Envvi/Inkpunk-Diffusion",
            "branch": "main",
            "triggers": [
                "nvinkpunk",
            ]
        },
        "Anything v3": {
            "path": "Linaqruf/anything-v3.0",
            "branch": "main"
        },
    },
    "stablediffusion_superresolution": {
        "Stability AI 4x resolution": {
            "path": "stabilityai/stable-diffusion-x4-upscaler",
            "branch": "fp16",
        },
    },
    "stablediffusion_pix2pix": {
        "Instruct pix2pix": {
            "path": "timbrooks/instruct-pix2pix",
            "branch": "fp16",
        },
    },
    "stablediffusion_riffusion": {
        "Riffusion": {
            "path": "riffusion/riffusion-model-v1",
            "branch": "main",
        }
    },
    "stablediffusion_vid2vid": {
        "SD Image Variations": {
            "path": "lambdalabs/sd-image-variations-diffusers",
            "branch": "v2.0",
        }
    },
    "stablediffusion_txt2vid":  {
        "Zeroscope v2": {
            "path": "cerspense/zeroscope_v2_576w",
            "branch": "fp16",
        },
        "Zeroscope v2 XL": {
            "path": "cerspense/zeroscope_v2_XL",
            "branch": "fp16",
        },
        "damo-vilab": {
            "path": "damo-vilab/text-to-video-ms-1.7b",
            "branch": "fp16",
        }
    },
    "stablediffusion_upscale": {
        "sd-x2-latent-upscaler": {
            "path": "stabilityai/sd-x2-latent-upscaler",
            "branch": "fp16",
        }
    },
    "kandinsky_generate": {
        "Kandinsky V2.1": {
            "path": "kandinsky-community/kandinsky-2-1",
            "branch": "fp16",
        },
    },
    "kandinsky_outpaint": {
        "Kandinsky Inpaint V2.1": {
            "path": "kandinsky-community/kandinsky-2-1-inpaint",
            "branch": "fp16",
        },
    },
    "shapegif_generate": {
        "shap-e": {
            "path": "openai/shap-e",
            "branch": "fp16",
        },
        "shap-e-img2img": {
            "path": "openai/shap-e-img2img",
            "branch": "fp16",
        }
    }
}
TEXT_MODELS = {
    "flan-t5-xxl": {
        "path": "google/flan-t5-xxl",
        "class": "AutoModelForSeq2SeqLM",
        "tokenizer": "AutoTokenizer",
    },
    "flan-t5-xl": {
        "path": "google/flan-t5-xl",
        "class": "AutoModelForSeq2SeqLM",
        "tokenizer": "AutoTokenizer",
    },
    "flan-t5-large": {
        "path": "google/flan-t5-large",
        "class": "AutoModelForSeq2SeqLM",
        "tokenizer": "AutoTokenizer",
    },
    "flan-t5-small": {
        "path": "google/flan-t5-small",
        "class": "AutoModelForSeq2SeqLM",
        "tokenizer": "AutoTokenizer",
    },
    "flan-t5-base": {
        "path": "google/flan-t5-base",
        "class": "AutoModelForSeq2SeqLM",
        "tokenizer": "AutoTokenizer",
    },
    "DialoGPT-large": {
        "path": "microsoft/DialoGPT-large",
        "class": "AutoModelForCausalLM",
        "tokenizer": "AutoTokenizer",
    }
}
KERAS_MODELS = {
    "superresolution": "keras-io/super-resolution",
}
DEFAULT_MODEL = "Stable Diffusion V2"
DEFAULT_SCHEDULER = SCHEDULERS[0]
MIN_SEED = 0
MAX_SEED = 4294967295
CHUNK_SIZE = 1024
DEFAULT_PORT=50006
DEFAULT_HOST="localhost"
# get platform
try:
    HOME=os.environ['HOME']
except KeyError:
    HOME = None
if PLATFORM == "Windows":
    try:
        WINEHOMEDIR = os.environ['WINEHOMEDIR']
    except KeyError:
        WINEHOMEDIR = None

    if not HOME:
        try:
            WINE_HOMEDRIVE = os.environ['WINE_HOMEDRIVE']
            WINE_HOMEPATH = os.environ['WINE_HOMEPATH']
        except KeyError:
            WINE_HOMEDRIVE = None
            WINE_HOMEPATH = None

        WINE_HOMEDRIVE = f"{WINE_HOMEDRIVE}:\\" if WINE_HOMEDRIVE else None
        HOMEDRIVE = WINE_HOMEDRIVE or os.environ['HOMEDRIVE']
        HOMEPATH = WINE_HOMEPATH or os.environ['HOMEPATH']
        # get HOME from %HOMEDRIVE%%HOMEPATH% on windows machine
        HOME = HOMEDRIVE + HOMEPATH

AIRUNNER_DIR = os.path.join(HOME, ".airunner")
if not os.path.exists(AIRUNNER_DIR):
    os.mkdir(AIRUNNER_DIR)
CACHE_DIR = os.path.join(AIRUNNER_DIR, "cache")
DEFAULT_GRID_COLOR = "#111111"
DEFAULT_CANVAS_COLOR = "#000000"
DEFAULT_BRUSH_PRIMARY_COLOR = "#ffffff"
DEFAULT_BRUSH_SECONDARY_COLOR = "#000000"
DEFAULT_WORKING_SIZE = (512, 512)
STYLES = {
    "button": {
        "standard": {
            "bg": "#f0f0f0",
            "fg": "#000000",
            "relief": "raised"
        },
        "active": {
            "bg": "#e0e0e0",
            "fg": "#000000",
            "relief": "sunken"
        }
    },
}
FONT_STYLES = {
    "bold": ("TkDefaultFont", 10, "bold"),
    "normal": ("TkDefaultFont", 10, "normal"),
    "subtext": ("TkDefaultFont", 8, "normal"),
}
AIRUNNER_ENVIRONMENT = os.environ.get("AIRUNNER_ENVIRONMENT", "dev")  # dev or prod
AIRUNNER_OS = platform.system()  # Windows or linux
LARGEST_WORKING_SIZE=2048
SMALLEST_WORKING_SIZE=8
BRUSH_INC_SIZE=8
LOG_LEVEL = logging.FATAL if AIRUNNER_ENVIRONMENT == "prod" else logging.DEBUG


class MessageCode(Enum):
    STATUS = 100
    ERROR = 200
    WARNING = 300
    PROGRESS = 400
    IMAGE_GENERATED = 500
    EMBEDDING_LOAD_FAILED = 600
