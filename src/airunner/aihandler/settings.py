import logging
import os
import platform

from airunner.enums import Scheduler

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

SCHEDULERS = [e.value for e in Scheduler]

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
DEFAULT_SCHEDULER = SCHEDULERS[0]
DEFAULT_MODEL = "Stable Diffusion V2"
MIN_SEED = 0
MAX_SEED = 4294967295
SERVER = {
    "host": "127.0.0.1",
    "port": 50006,
    "chunk_size": 1024,
}
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
LARGEST_WORKING_SIZE = 2048
SMALLEST_WORKING_SIZE = 8
BRUSH_INC_SIZE = 8
LOG_LEVEL = logging.FATAL if AIRUNNER_ENVIRONMENT == "prod" else logging.INFO
AVAILABLE_DTYPES = ("2bit", "4bit", "8bit")
