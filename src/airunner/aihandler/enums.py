from enum import Enum


class WorkerState(Enum):
    RUNNING = 1
    PAUSED = 2
    HALTED = 3


class QueueType(Enum):
    GET_LAST_ITEM = 100
    GET_NEXT_ITEM = 200
    NONE = 300


class WorkerCode(Enum):
    START_VISION_CAPTURE = 100
    STOP_VISION_CAPTURE = 200
    UNPAUSE_VISION_CAPTURE = 300


class HandlerType(Enum):
    TRANSFORMER = 100
    DIFFUSER = 200


class FilterType(Enum):
    PIXEL_ART = "pixelart"


class SignalCode(Enum):
    START_VISION_CAPTURE = "start_vision_capture"
    STOP_VISION_CAPTURE = "stop_vision_capture"
    VISION_CAPTURE_UNPAUSE_SIGNAL = "unpause_vision_capture"
    VISION_CAPTURE_PROCESS_SIGNAL = "vision_capture_process_signal"
    VISION_CAPTURED_SIGNAL = "vision_captured_signal"
    VISION_PROCESSED_SIGNAL = "vision_processed_signal"


class EngineResponseCode(Enum):
    STATUS = 100
    ERROR = 200
    WARNING = 300
    PROGRESS = 400
    IMAGE_GENERATED = 500
    CONTROLNET_IMAGE_GENERATED = 501
    MASK_IMAGE_GENERATED = 502
    EMBEDDING_LOAD_FAILED = 600
    TEXT_GENERATED = 700
    TEXT_STREAMED = 701
    CAPTION_GENERATED = 800
    ADD_TO_CONVERSATION = 900
    CLEAR_MEMORY = 1000
    NSFW_CONTENT_DETECTED = 1100


class EngineRequestCode(Enum):
    GENERATE_IMAGE = 100
    GENERATE_TEXT = 200
    GENERATE_CAPTION = 300


class Scheduler(Enum):
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
    # DDIMInverse = "DDIM Inverse"
    # IPNM = "IPNM"
    # REPAINT = "RePaint"
    # KVE = "Karras Variance exploding"
    # VESDE = "VE-SDE"
    # VPSDE = "VP-SDE"
    # VQDIFFUSION = "VQ Diffusion"


class Mode(Enum):
    IMAGE = "Image Generation"
    LANGUAGE_PROCESSOR = "Language Processing"
    MODEL_MANAGER = "Model Manager"


class GeneratorSection(Enum):
    TXT2IMG = "txt2img"
    IMG2IMG = "img2img"
    INPAINT = "inpaint"
    OUTPAINT = "outpaint"
    DEPTH2IMG = "depth2img"
    PIX2PIX = "pix2pix"
    SUPERRESOLUTION = "superresolution"
    UPSCALE = "upscale"
    VID2VID = "vid2vid"
    TXT2VID = "txt2vid"
    PROMPT_BUILDER = "prompt_builder"