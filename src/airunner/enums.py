from enum import Enum


class WorkerState(Enum):
    RUNNING = 100
    PAUSED = 200
    HALTED = 300


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


class ServiceCode(Enum):
    CURRENT_LAYER = "current_layer"
    CURRENT_DRAGGABLE_PIXMAP = "current_draggable_pixmap"
    CURRENT_ACTIVE_IMAGE = "current_active_image"
    GET_IMAGE_FROM_LAYER = "get_image_from_layer"
    GET_EMBEDDINGS = "get_embeddings"
    DELETE_MISSING_EMBEDDINGS = "delete_missing_embeddings"
    SCAN_FOR_EMBEDDINGS = "scan_for_embeddings"
    GET_SETTINGS = "get_settings"
    SET_SETTINGS = "set_settings"
    GET_PIPELINE_CLASSNAME = "get_pipeline_classname"
    PIPELINE_ACTIONS = "pipeline_actions"
    GET_PIPELINES = "get_pipelines"
    LAYER_WIDGET = "layer_widget"
    GET_LLM_WIDGET = "get_llm_widget"
    DISPLAY_IMPORT_IMAGE_DIALOG = "display_import_image_dialog"
    IS_WINDOWS = "is_windows"
    GET_SETTINGS_VALUE = "get_settings_value"
    GET_CALLBACK_FOR_SLIDER = "get_callback_for_slider"


class SignalCode(Enum):
    START_VISION_CAPTURE = "start_vision_capture"
    STOP_VISION_CAPTURE = "stop_vision_capture"
    VISION_CAPTURE_UNPAUSE_SIGNAL = "unpause_vision_capture"
    VISION_CAPTURE_PROCESS_SIGNAL = "vision_capture_process_signal"
    VISION_CAPTURED_SIGNAL = "vision_captured_signal"
    VISION_PROCESSED_SIGNAL = "vision_processed_signal"
    EMBEDDING_LOAD_FAILED_SIGNAL = "embedding_load_failed_signal"
    ERROR_SIGNAL = "error_signal"
    WARNING_SIGNAL = "warning_signal"
    STATUS_SIGNAL = "status_signal"
    SD_REQUEST_SIGNAL = "sd_request_signal"
    AUDIO_PROCESSOR_RESPONSE_SIGNAL = "audio_processor_response_signal"
    AUDIO_PROCESSOR_PROCESSED_AUDIO = "audio_processor_processed_audio"
    LLM_RESPONSE_SIGNAL = "llm_response_signal"
    HEAR_SIGNAL = "hear_signal"
    ENGINE_CANCEL_SIGNAL = "engine_cancel_signal"
    ENGINE_STOP_PROCESSING_QUEUE_SIGNAL = "engine_stop_processing_queue_signal"
    ENGINE_START_PROCESSING_QUEUE_SIGNAL = "engine_start_processing_queue_signal"
    CLEAR_LLM_HISTORY_SIGNAL = "clear_llm_history_signal"
    CLEAR_MEMORY_SIGNAL = "clear_memory_signal"
    CAPTION_GENERATED_SIGNAL = "caption_generated_signal"
    ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL = "EngineResponseWorker_response_signal"
    TEXT_GENERATE_REQUEST_SIGNAL = "text_generate_request_signal"
    IMAGE_GENERATE_REQUEST_SIGNAL = "image_generate_request_signal"
    LLM_TEXT_STREAMED_SIGNAL = "llm_text_streamed_signal"
    AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL = "AudioCaptureWorker_response_signal"
    AUDIO_PROCESSOR_WORKER_PROCESSED_SIGNAL = "AudioProcessorWorker_processed_audio"
    CONTROLNET_IMAGE_GENERATED_SIGNAL = "controlnet_image_generated_signal"
    SD_PROGRESS_SIGNAL = "progress_signal"
    APPLICATION_SETTINGS_CHANGED_SIGNAL = "application_settings_changed_signal"
    UPDATE_LORA_SIGNAL = "update_lora_signal"
    GENERATE_IMAGE_SIGNAL = "generate_image_signal"
    STOP_IMAGE_GENERATOR_PROGRESS_BAR_SIGNAL = "stop_image_generator_progress_bar_signal"
    SET_STATUS_LABEL_SIGNAL = "set_status_label_signal"
    SWITCH_LAYER_SIGNAL = "switch_layer_signal"
    ADD_LAYER_SIGNAL = "add_layer_signal"
    CREATE_LAYER_SIGNAL = "create_layer_signal"
    UPDATE_CURRENT_LAYER_SIGNAL = "update_current_layer_signal"
    UPDATE_LAYER_SIGNAL = "update_layer_signal"
    DELETE_CURRENT_LAYER_SIGNAL = "delete_current_layer_signal"
    DELETE_LAYER_SIGNAL = "delete_layer_signal"
    MOVE_LAYER_UP_SIGNAL = "move_layer_up_signal"
    MOVE_LAYER_DOWN_SIGNAL = "move_layer_down_signal"
    CLEAR_LAYERS_SIGNAL = "clear_layers_signal"
    SET_CURRENT_LAYER_SIGNAL = "set_current_layer_signal"
    CANVAS_DO_DRAW_SIGNAL = "canvas_do_draw_signal"
    CANVAS_CLEAR_LINES_SIGNAL = "canvas_clear_lines_signal"
    IMAGE_DATA_WORKER_RESPONSE_SIGNAL = "ImageDataWorker_response_signal"
    CANVAS_RESIZE_WORKER_RESPONSE_SIGNAL = "CanvasResizeWorker_response_signal"
    IMAGE_GENERATED_SIGNAL = "image_generated_signal"
    LOAD_IMAGE_FROM_PATH_SIGNAL = "load_image_from_path_signal"
    CANVAS_HANDLE_LAYER_CLICK_SIGNAL = "canvas_handle_layer_click_signal"
    UPDATE_CANVAS_SIGNAL = "update_canvas_signal"
    SD_MERGE_MODELS_SIGNAL = "sd_merge_models_signal"
    MAIN_WINDOW_LOADED_SIGNAL = "main_window_loaded_signal"
    SD_CANCEL_SIGNAL = "sd_cancel_signal"
    UNLOAD_SD_SIGNAL = "unload_stablediffusion_signal"
    MOVE_TO_CPU_SIGNAL = "move_to_cpu_signal"
    PROCESS_AUDIO_SIGNAL = "process_audio"
    REFRESH_AI_MODELS_SIGNAL = "refresh_ai_models_signal"
    SHOW_LAYERS_SIGNAL = "show_layers_signal"
    TOKEN_SIGNAL = "token_signal"
    ADD_BOT_MESSAGE_TO_CONVERSATION = "add_bot_message_to_conversation"
    MODELS_CHANGED_SIGNAL = "models_changed_signal"
    AI_MODELS_SAVE_OR_UPDATE_SIGNAL = "ai_models_save_or_update_signal"
    AI_MODEL_DELETE_SIGNAL = "ai_model_delete_signal"
    AI_MODELS_CREATE_SIGNAL = "ai_models_create_signal"
    CLEAR_STATUS_MESSAGE_SIGNAL = "clear_status_message_signal"
    DESCRIBE_IMAGE_SIGNAL = "describe_image_signal"
    SAVE_SD_PROMPT_SIGNAL = "save_stablediffusion_prompt_signal"
    LOAD_SD_PROMPT_SIGNAL = "load_saved_stablediffuion_prompt_signal"
    UPDATE_SAVED_SD_PROMPT_SIGNAL = "update_saved_stablediffusion_prompt_signal"
    ADD_LORA_SIGNAL = "add_lora_signal"
    TTS_REQUEST = "tts_request"
    RESET_SETTINGS_SIGNAL = "reset_settings_signal"
    STT_AUDIO_PROCESSED = "stt_audio_processed_signal"
    CANVAS_RESIZE_SIGNAL = "canvas_resize_signal"
    ENGINE_DO_RESPONSE_SIGNAL = "engine_do_response_signal"
    ENGINE_DO_REQUEST_SIGNAL = "engine_do_request_signal"
    LLM_REQUEST_WORKER_RESPONSE_SIGNAL = "LLMRequestWorker_response_signal"
    UNLOAD_LLM_SIGNAL = "unload_llm_signal"
    CLEAR_HISTORY = "clear_history"
    LLM_REQUEST_SIGNAL = "llm_request_signal"
    TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL = "TTSGeneratorWorker_add_to_stream_signal"
    ADD_SD_RESPONSE_TO_QUEUE_SIGNAL = "add_sd_response_to_queue_signal"
    RESET_PATHS_SIGNAL = "reset_paths_signal"
    NSFW_CONTENT_DETECTED_SIGNAL = "nsfw_content_detected_signal"
    ZOOM_LEVEL_CHANGED = "zoom_level_changed"
    CANVAS_UPDATE_CURSOR = "canvas_update_cursor"


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