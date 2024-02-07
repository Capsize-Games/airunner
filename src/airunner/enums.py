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
    GET_LLM_WIDGET = "get_llm_widget"
    DISPLAY_IMPORT_IMAGE_DIALOG = "display_import_image_dialog"
    GET_SETTINGS_VALUE = "get_settings_value"
    GET_CALLBACK_FOR_SLIDER = "get_callback_for_slider"


class SignalCode(Enum):
    AI_MODELS_REFRESH_SIGNAL = "refresh_ai_models_signal"
    AI_MODELS_SAVE_OR_UPDATE_SIGNAL = "ai_models_save_or_update_signal"
    AI_MODEL_DELETE_SIGNAL = "ai_model_delete_signal"
    AI_MODELS_CREATE_SIGNAL = "ai_models_create_signal"

    APPLICATION_MAIN_WINDOW_LOADED_SIGNAL = "main_window_loaded_signal"
    APPLICATION_ADD_BOT_MESSAGE_TO_CONVERSATION = "add_bot_message_to_conversation"
    APPLICATION_MODELS_CHANGED_SIGNAL = "models_changed_signal"
    APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL = "clear_status_message_signal"
    APPLICATION_RESET_SETTINGS_SIGNAL = "reset_settings_signal"
    APPLICATION_RESET_PATHS_SIGNAL = "reset_paths_signal"
    APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL = "stop_image_generator_progress_bar_signal"
    APPLICATION_SETTINGS_CHANGED_SIGNAL = "application_settings_changed_signal"
    APPLICATION_STATUS_INFO_SIGNAL = "status_info_signal"
    APPLICATION_STATUS_ERROR_SIGNAL = "status_error_signal"

    AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL = "AudioCaptureWorker_response_signal"
    AUDIO_PROCESSOR_WORKER_PROCESSED_SIGNAL = "AudioProcessorWorker_processed_audio"
    AUDIO_PROCESSOR_RESPONSE_SIGNAL = "audio_processor_response_signal"
    AUDIO_PROCESSOR_PROCESSED_AUDIO = "audio_processor_processed_audio"

    PRESET_IMAGE_GENERATOR_DISPLAY_ITEM_MENU_SIGNAL = "preset_image_generator_display_menu_signal"
    PRESET_IMAGE_GENERATOR_ACTIVATE_BRUSH_SIGNAL = "activate_brush"

    CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL = "load_image_from_path_signal"
    CANVAS_DO_DRAW_SIGNAL = "canvas_do_draw_signal"
    CANVAS_CLEAR_LINES_SIGNAL = "canvas_clear_lines_signal"
    CANVAS_RESIZE_WORKER_RESPONSE_SIGNAL = "CanvasResizeWorker_response_signal"
    CANVAS_HANDLE_LAYER_CLICK_SIGNAL = "canvas_handle_layer_click_signal"
    CANVAS_UPDATE_SIGNAL = "update_canvas_signal"
    CANVAS_RESIZE_SIGNAL = "canvas_resize_signal"
    CANVAS_UPDATE_CURSOR = "canvas_update_cursor"
    CANVAS_ZOOM_LEVEL_CHANGED = "zoom_level_changed"
    CANVAS_CLEAR = "clear_canvas"
    CANVAS_PASTE_IMAGE_SIGNAL = "canvas_paste_image_signal"
    CANVAS_COPY_IMAGE_SIGNAL = "canvas_copy_image_signal"
    CANVAS_CUT_IMAGE_SIGNAL = "canvas_cut_image_signal"
    CANVAS_ROTATE_90_CLOCKWISE_SIGNAL = "canvas_rotate_90_clockwise_signal"
    CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL = "canvas_rotate_90_counter_clockwise_signal"
    CANVAS_PREVIEW_FILTER_SIGNAL = "canvas_preview_filter_signal"
    CANVAS_CANCEL_FILTER_SIGNAL = "canvas_cancel_filter_signal"
    CANVAS_APPLY_FILTER_SIGNAL = "canvas_apply_filter_signal"

    CLEAR_MEMORY_SIGNAL = "clear_memory_signal"
    CONTROLNET_IMAGE_GENERATED_SIGNAL = "controlnet_image_generated_signal"
    EMBEDDING_LOAD_FAILED_SIGNAL = "embedding_load_failed_signal"

    ENGINE_CANCEL_SIGNAL = "engine_cancel_signal"
    ENGINE_STOP_PROCESSING_QUEUE_SIGNAL = "engine_stop_processing_queue_signal"
    ENGINE_START_PROCESSING_QUEUE_SIGNAL = "engine_start_processing_queue_signal"
    ENGINE_DO_RESPONSE_SIGNAL = "engine_do_response_signal"
    ENGINE_DO_REQUEST_SIGNAL = "engine_do_request_signal"
    ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL = "EngineResponseWorker_response_signal"

    LAYER_SWITCH_SIGNAL = "switch_layer_signal"
    LAYER_ADD_SIGNAL = "add_layer_signal"
    LAYER_CREATE_SIGNAL = "create_layer_signal"
    LAYER_UPDATE_CURRENT_SIGNAL = "update_current_layer_signal"
    LAYER_UPDATE_SIGNAL = "update_layer_signal"
    LAYER_DELETE_CURRENT_SIGNAL = "delete_current_layer_signal"
    LAYER_DELETE_SIGNAL = "delete_layer_signal"
    LAYER_CLEAR_LAYERS_SIGNAL = "clear_layers_signal"
    LAYER_SET_CURRENT_SIGNAL = "set_current_layer_signal"
    LAYER_MOVE_UP_SIGNAL = "move_layer_up_signal"
    LAYER_MOVE_DOWN_SIGNAL = "move_layer_down_signal"
    LAYERS_SHOW_SIGNAL = "show_layers_signal"
    LAYER_OPACITY_CHANGED_SIGNAL = "layers_layer_opacity_changed_signal"

    # TODO: combine clear history signals - we have two by mistake
    LLM_CLEAR_HISTORY = "llm_clear_history"
    LLM_CLEAR_HISTORY_SIGNAL = "llm_clear_history_signal"
    LLM_RESPONSE_SIGNAL = "llm_response_signal"
    LLM_TEXT_STREAMED_SIGNAL = "llm_text_streamed_signal"
    LLM_REQUEST_WORKER_RESPONSE_SIGNAL = "LLMRequestWorker_response_signal"
    LLM_UNLOAD_SIGNAL = "llm_unload_signal"
    LLM_REQUEST_SIGNAL = "llm_request_signal"
    LLM_TEXT_GENERATE_REQUEST_SIGNAL = "llm_text_generate_request_signal"
    LLM_TOKEN_SIGNAL = "llm_token_signal"
    LLM_RESPOND_TO_USER_SIGNAL = "llm_respond_to_user_signal"
    LLM_PROCESS_STT_AUDIO_SIGNAL = "llm_process_stt_audio"

    LOG_ERROR_SIGNAL = "error_signal"
    LOG_WARNING_SIGNAL = "warning_signal"
    LOG_STATUS_SIGNAL = "status_signal"

    LORA_ADD_SIGNAL = "add_lora_signal"
    LORA_UPDATE_SIGNAL = "update_lora_signal"

    SD_IMAGE_GENERATE_REQUEST_SIGNAL = "image_generate_request_signal"
    SD_PROGRESS_SIGNAL = "progress_signal"
    SD_REQUEST_SIGNAL = "sd_request_signal"
    SD_MERGE_MODELS_SIGNAL = "sd_merge_models_signal"
    SD_CANCEL_SIGNAL = "sd_cancel_signal"
    SD_UNLOAD_SIGNAL = "unload_stablediffusion_signal"
    SD_UPDATE_SAVED_PROMPT_SIGNAL = "update_saved_stablediffusion_prompt_signal"
    SD_SAVE_PROMPT_SIGNAL = "save_stablediffusion_prompt_signal"
    SD_LOAD_PROMPT_SIGNAL = "load_saved_stablediffuion_prompt_signal"
    SD_ADD_RESPONSE_TO_QUEUE_SIGNAL = "add_sd_response_to_queue_signal"
    SD_MOVE_TO_CPU_SIGNAL = "move_to_cpu_signal"
    SD_IMAGE_DATA_WORKER_RESPONSE_SIGNAL = "ImageDataWorker_response_signal"
    SD_GENERATE_IMAGE_SIGNAL = "generate_image_signal"
    SD_IMAGE_GENERATED_SIGNAL = "image_generated_signal"
    SD_NSFW_CONTENT_DETECTED_SIGNAL = "nsfw_content_detected_signal"

    STT_HEAR_SIGNAL = "hear_signal"
    STT_AUDIO_PROCESSED = "stt_audio_processed_signal"
    STT_PROCESS_AUDIO_SIGNAL = "stt_process_audio"
    STT_START_CAPTURE_SIGNAL = "stt_start_capture"
    STT_STOP_CAPTURE_SIGNAL = "stt_stop_capture"

    TTS_REQUEST = "tts_request"
    TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL = "TTSGeneratorWorker_add_to_stream_signal"
    TTS_ENABLE_SIGNAL = "tts_enable_signal"
    TTS_DISABLE_SIGNAL = "tts_disable_signal"

    VISION_START_CAPTURE = "start_vision_capture"
    VISION_STOP_CAPTURE = "stop_vision_capture"
    VISION_CAPTURE_UNPAUSE_SIGNAL = "unpause_vision_capture"
    VISION_CAPTURE_PROCESS_SIGNAL = "vision_capture_process_signal"
    VISION_CAPTURED_SIGNAL = "vision_captured_signal"
    VISION_PROCESSED_SIGNAL = "vision_processed_signal"
    VISION_CAPTION_GENERATED_SIGNAL = "caption_generated_signal"
    VISION_DESCRIBE_IMAGE_SIGNAL = "describe_image_signal"
    VISION_PROCESS_IMAGES = "process_images"


    QUIT_APPLICATION = "quit"


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


class LLMAction(Enum):
    CHAT = "chat"
    RAG = "rag"
    UPDATE_BOT_MOOD = "summary"
    EVALUATE_USER = "user_evaluation"


class LLMChatRole(Enum):
    ASSISTANT = "assistant"
    HUMAN = "user"
    SYSTEM = "system"


class LLMToolName(Enum):
    COMMENT_ON_IMAGE = "comment_on_image"
    DESCRIBE_IMAGE = "describe_image"
    GENERATE_IMAGE = "generate_image"
    DEFAULT_TOOL = "default_response_tool"
    LLM_PROCESS_STT_AUDIO = "llm_process_stt_audio"
    RAG_SEARCH = "llm_rag_search"
    QUIT_APPLICATION = "quit_application"
    STT_START_CAPTURE = "stt_start_audio_capture"
    STT_STOP_CAPTURE = "stt_stop_audio_capture"
    TTS_ENABLE = "tts_enable"
    TTS_DISABLE = "tts_disable"
    VISION_PROCESS_IMAGES = "vision_process_images"
    VISION_START_CAPTURE = "vision_start_capture"
    VISION_STOP_CAPTURE = "vision_stop_capture"


class CanvasToolName(Enum):
    ACTIVE_GRID_AREA = "active_grid_area"
    BRUSH = "brush"
    ERASER = "eraser"


class WindowSection(Enum):
    CONTROLNET = "controlnet"
    EMBEDDINGS = "Embeddings"
    LORA = "LoRA"
    PEN = "Pen"
    ACTIVE_GRID = "Active Grid"