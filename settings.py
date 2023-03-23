import os
import platform

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
EULER = "Euler"
EULER_ANCESTRAL = "Euler a"
LMS = "LMS"
PNDM = "PNDM"
HEUN = "Heun"
DDIM = "DDIM"
DDPM = "DDPM"
DPM_SINGLESTEP = "DPM singlestep"
DPM_MULTISTEP = "DPM multistep"
DPMPP_SINGLESTEP = "DPM++ singlestep"
DPMPP_MULTISTEP = "DPM++ multistep"
DPM2_K = "DPM2 k"
DPM2_A_K = "DPM2 a k"
DEIS = "DEIS"
SCHEDULERS = [
    EULER,
    EULER_ANCESTRAL,
    LMS,
    PNDM,
    HEUN,
    DDIM,
    DDPM,
    DPM_SINGLESTEP,
    DPM_MULTISTEP,
    DPMPP_SINGLESTEP,
    DPMPP_MULTISTEP,
    DPM2_K,
    DPM2_A_K,
    DEIS,
]
AVAILABLE_SCHEDULERS_BY_ACTION = {
    "txt2img": SCHEDULERS,
    "img2img": SCHEDULERS,
    "depth2img": SCHEDULERS,
    "pix2pix": SCHEDULERS,
    "vid2vid": SCHEDULERS,
    "outpaint": SCHEDULERS,
    "superresolution": [DDIM, LMS, PNDM],
    "controlnet": SCHEDULERS,
}
UPSCALERS = ["None", "Lanczos"]

MODELS = {
    "generate": {
        "Stable Diffusion V2": {
            "path": "stabilityai/stable-diffusion-2-1-base",
            "branch": "fp16",
        },
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
    "outpaint": {
        "Stable Diffusion Inpaint V2": {
            "path": "stabilityai/stable-diffusion-2-inpainting",
            "branch": "fp16",
        },
        "Stable Diffusion Inpaint V1": {
            "path": "runwayml/stable-diffusion-inpainting",
            "branch": "fp16",
        },
    },
    "depth2img": {
        "Stable Diffusion Depth2Img": {
            "path": "stabilityai/stable-diffusion-2-depth",
            "branch": "fp16",
        },
    },
    "ksuperresolution": {
        "Keras Super Resolution": {
            "path": "keras-io/super-resolution",
            "branch": "main",
        },
    },
    "controlnet": {
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
    "superresolution": {
        "Stability AI 4x resolution": {
            "path": "stabilityai/stable-diffusion-x4-upscaler",
            "branch": "fp16",
        },
    },
    "pix2pix": {
        "Instruct pix2pix": {
            "path": "timbrooks/instruct-pix2pix",
            "branch": "fp16",
        },
    },
    "riffusion": {
        "Riffusion": {
            "path": "riffusion/riffusion-model-v1",
            "branch": "main",
        }
    },
    "vid2vid": {
        "SD Image Variations": {
            "path": "lambdalabs/sd-image-variations-diffusers",
            "branch": "v2.0",
        }
    }
}

KERAS_MODELS = {
    "super_resolution": "keras-io/super-resolution",
}

DEFAULT_MODEL = "Stable Diffusion V2"
DEFAULT_SCHEDULER = SCHEDULERS[0]
MIN_SEED = 0
MAX_SEED = 4294967295
CHUNK_SIZE = 1024
DEFAULT_PORT=50006
DEFAULT_HOST="localhost"
VERSION="1.8.9"
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
AIRUNNER_ENVIRONMENT = os.environ.get("AIRUNNER_ENVIRONMENT", "prod")  # dev or prod
AIRUNNER_OS = platform.system()  # Windows or linux
LARGEST_WORKING_SIZE=2048
SMALLEST_WORKING_SIZE=8
BRUSH_INC_SIZE=8