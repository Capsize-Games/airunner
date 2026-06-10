"""Service-owned enum definitions."""

from __future__ import annotations

from enum import Enum


class SignalCode(Enum):
    """Cross-process and cross-layer signal identifiers."""

    APPLICATION_SETTINGS_CHANGED_SIGNAL = "application_settings_changed_signal"
    APPLICATION_STATUS_INFO_SIGNAL = "status_info_signal"
    APPLICATION_STATUS_ERROR_SIGNAL = "status_error_signal"
    APPLICATION_ERROR_SIGNAL = "status_error_signal"
    APPLICATION_QUIT_SIGNAL = "application_quit_signal"
    AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL = "AudioCaptureWorker_response_signal"
    AUDIO_PROCESSOR_RESPONSE_SIGNAL = "audio_processor_response_signal"
    BOT_MOOD_UPDATED = "bot_mood_updated_signal"
    CANVAS_CLEAR_LINES_SIGNAL = "canvas_clear_lines_signal"
    CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL = "load_image_from_path_signal"
    CONVERSATION_DELETED = "conversation_deleted_signal"
    CONVERSATION_TITLE_UPDATED = "conversation_title_updated_signal"
    DO_GENERATE_SIGNAL = "do_generate_signal"
    ENABLE_BRUSH_TOOL_SIGNAL = "enable_brush_tool_signal"
    ENABLE_ERASER_TOOL_SIGNAL = "enable_eraser_tool_signal"
    ENABLE_MOVE_TOOL_SIGNAL = "enable_move_tool_signal"
    ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL = (
        "EngineResponseWorker_response_signal"
    )
    HUGGINGFACE_DOWNLOAD_COMPLETE = "huggingface_download_complete"
    HUGGINGFACE_DOWNLOAD_FAILED = "huggingface_download_failed"
    INTERRUPT_IMAGE_GENERATION_SIGNAL = "interrupt_image_generation_signal"
    INTERRUPT_PROCESS_SIGNAL = "interrupt_process_signal"
    LLM_CLEAR_HISTORY_SIGNAL = "llm_clear_history_signal"
    LLM_LOAD_SIGNAL = "llm_load_signal"
    LLM_TEXT_GENERATE_REQUEST_SIGNAL = "llm_text_generate_request_signal"
    LLM_TEXT_STREAMED_SIGNAL = "llm_text_streamed_signal"
    LLM_THINKING_SIGNAL = "llm_thinking_signal"
    LLM_TOOL_STATUS_SIGNAL = "llm_tool_status_signal"
    LLM_UNLOAD_SIGNAL = "llm_unload_signal"
    AI_MODELS_SAVE_OR_UPDATE_SIGNAL = "ai_models_save_or_update_signal"
    APPLICATION_ACTIVE_GRID_AREA_UPDATED = "active_grid_area_updated"
    APPLICATION_SETTINGS_ERROR = "application_settings_error"
    APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL = (
        "stop_image_generator_progress_bar_signal"
    )
    ART_MODEL_DOWNLOAD_REQUIRED = "art_model_download_required"
    CANCEL_HUGGINGFACE_DOWNLOAD = "cancel_huggingface_download"
    CHANGE_SCHEDULER_SIGNAL = "change_scheduler_signal"
    CHATBOT_CHANGED = "chatbot_changed_signal"
    DELETE_MESSAGES_AFTER_ID = "delete_messages_after_id"
    DOCUMENT_COLLECTION_CHANGED = "document_collection_changed_signal"
    DOCUMENT_INDEXED = "document_indexed_signal"
    DOCUMENT_INDEX_FAILED = "document_index_failed_signal"
    GENERATOR_FORM_UPDATE_VALUES_SIGNAL = "generator_form_update_values"
    IMAGE_EXPORTED = "image_exported_signal"
    KNOWLEDGE_FACT_ADDED = "knowledge_fact_added_signal"
    KNOWLEDGE_FACT_DELETED = "knowledge_fact_deleted_signal"
    KNOWLEDGE_FACT_UPDATED = "knowledge_fact_updated_signal"
    LAYERS_SHOW_SIGNAL = "show_layers_signal"
    LLM_CONVERT_TO_GGUF_SIGNAL = "llm_convert_to_gguf_signal"
    LLM_IMAGE_PROMPT_GENERATED_SIGNAL = "llm_image_prompt_generated_signal"
    LLM_MODEL_CHANGED = "llm_model_changed_signal"
    LLM_MODEL_DOWNLOAD_REQUIRED = "llm_model_download_required"
    LLM_QUANTIZATION_COMPLETE = "llm_quantization_complete"
    LLM_QUANTIZATION_FAILED = "llm_quantization_failed"
    LLM_QUANTIZATION_PROGRESS = "llm_quantization_progress"
    LLM_TEXT_STREAM_PROCESS_SIGNAL = "llm_text_stream_process_signal"
    MISSING_REQUIRED_MODELS = "missing_required_models"
    MOOD_SUMMARY_UPDATE_STARTED = "mood_summary_update_started_signal"
    QUEUE_LOAD_CONVERSATION = "queue_load_conversation_signal"
    RAG_DOCUMENT_ADDED = "rag_document_added_signal"
    RAG_INDEX_ALL_DOCUMENTS = "rag_index_all_documents_signal"
    RAG_INDEX_CANCEL = "rag_index_cancel_signal"
    RAG_INDEXING_COMPLETE = "rag_indexing_complete_signal"
    RAG_INDEXING_PROGRESS = "rag_indexing_progress_signal"
    RAG_INDEX_SELECTED_DOCUMENTS = "rag_index_selected_documents_signal"
    RAG_RELOAD_INDEX_SIGNAL = "rag_reload_index_signal"
    SAFETY_CHECKER_FILTER_COMPLETE = "safety_checker_filter_complete"
    SAFETY_CHECKER_FILTER_REQUEST = "safety_checker_filter_request"
    SAFETY_CHECKER_UNLOAD_SIGNAL = "safety_checker_unload_signal"
    SD_GENERATE_SIGNAL = "sd_generate_signal"
    SD_LOAD_PROMPT_SIGNAL = "load_saved_stablediffuion_prompt_signal"
    SD_PIPELINE_LOADED_SIGNAL = "sd_pipeline_loaded_signal"
    SD_SAVE_PROMPT_SIGNAL = "save_stablediffusion_prompt_signal"
    SD_UPDATE_BATCH_IMAGES_SIGNAL = "sd_update_batch_images_signal"
    SD_UPSCALE_SIGNAL = "sd_upscale_signal"
    START_HUGGINGFACE_DOWNLOAD = "start_huggingface_download"
    STT_START_CAPTURE_SIGNAL = "stt_start_capture"
    STT_STOP_CAPTURE_SIGNAL = "stt_stop_capture"
    TOGGLE_LLM_SIGNAL = "toggle_llm_signal"
    TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL = (
        "tts_generator_worker_add_to_stream"
    )
    UPSCALE_COMPLETED = "upscale_completed_signal"
    UPSCALE_FAILED = "upscale_failed_signal"
    UPSCALE_PROGRESS = "upscale_progress_signal"
    LOAD_CONVERSATION_SIGNAL = "load_conversation_signal"
    MODEL_STATUS_CHANGED_SIGNAL = "model_status_changed_signal"
    NEW_CONVERSATION_SIGNAL = "new_conversation_signal"
    OPEN_CODE_EDITOR = "open_code_editor_signal"
    QUIT_APPLICATION = "quit"
    RAG_LOAD_DOCUMENTS = "rag_load_documents_signal"
    REDO_SIGNAL = "redo_signal"
    REFRESH_STYLESHEET_SIGNAL = "refresh_stylesheet_signal"
    REQUEST_USER_INPUT_SIGNAL = "request_user_input_signal"
    SCHEDULE_TASK_SIGNAL = "schedule_task_signal"
    SD_ART_MODEL_CHANGED = "reload_stablediffusion_signal"
    SD_GENERATE_IMAGE_SIGNAL = "generate_image_signal"
    SD_IMAGE_GENERATED_SIGNAL = "image_generated_signal"
    SD_LOAD_SIGNAL = "load_stablediffusion_signal"
    SD_PROGRESS_SIGNAL = "progress_signal"
    SD_UNLOAD_SIGNAL = "unload_stablediffusion_signal"
    SET_APPLICATION_MODE_SIGNAL = "set_application_mode_signal"
    START_OPENVOICE_BATCH_DOWNLOAD = "start_openvoice_batch_download"
    STT_CHUNK_SIGNAL = "stt_chunk_signal"
    STT_DISABLE_SIGNAL = "stt_disable_signal"
    STT_LOAD_SIGNAL = "stt_load_signal"
    STT_TRANSCRIBE_CHUNK_SIGNAL = "stt_transcribe_chunk_signal"
    STT_UNLOAD_SIGNAL = "stt_unload_signal"
    TOGGLE_TTS_SIGNAL = "toggle_tts_signal"
    TTS_DISABLE_SIGNAL = "tts_disable_signal"
    TTS_ENABLE_SIGNAL = "tts_enable_signal"
    TTS_QUEUE_SIGNAL = "tts_queue_signal"
    UNDO_SIGNAL = "undo_signal"
    AGENT_ACTION_PROPOSAL_SIGNAL = "agent_action_proposal_signal"
    UPDATE_DOWNLOAD_LOG = "update_download_log"
    UPDATE_DOWNLOAD_PROGRESS = "update_download_progress"
    UPDATE_FILE_DOWNLOAD_PROGRESS = "update_file_download_progress"


class EngineResponseCode(Enum):
    """Worker response payload codes."""

    NONE = 0
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
    INSUFFICIENT_GPU_MEMORY = 1200
    INTERRUPTED = 1300


class Scheduler(Enum):
    """Supported image-generation schedulers."""

    EULER_ANCESTRAL = "Euler a"
    EULER = "Euler"
    LMS = "LMS"
    HEUN = "Heun"
    DPM = "DPM"
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
    FLOW_MATCH_EULER = "Flow Match Euler"
    FLOW_MATCH_LCM = "Flow Match LCM"


class Mode(Enum):
    """Top-level application modes."""

    IMAGE = "Image Generation"
    LANGUAGE_PROCESSOR = "Language Processing"
    MODEL_MANAGER = "Model Manager"


class LLMActionType(Enum):
    """LLM action types used by service and GUI workflows."""

    NONE = "None"
    CHAT = "RESPOND: Choose this action if you want to respond to the user."
    GENERATE_IMAGE = (
        "GENERATE IMAGE: Choose this action if you want to generate an "
        "image."
    )
    APPLICATION_COMMAND = "APPLICATION_COMMAND"
    UPDATE_MOOD = "UPDATE_MOOD"
    QUIT_APPLICATION = (
        "QUIT APPLICATION: If the users requests that you quit the "
        "application, choose this action."
    )
    TOGGLE_FULLSCREEN = (
        "TOGGLE FULLSCREEN: If the user requests to toggle fullscreen "
        "mode, choose this action."
    )
    TOGGLE_TTS = (
        "TOGGLE TEXT-TO-SPEECH: If the user requests that you turn on or "
        "off or toggle text-to-speech, choose this action."
    )
    PERFORM_RAG_SEARCH = (
        "SEARCH: If the user requests that you search for information, "
        "choose this action."
    )
    SUMMARIZE = "SUMMARIZE"
    DO_NOTHING = (
        "DO NOTHING: If the user's request is unclear or you are unable "
        "to determine the user's intent, choose this action."
    )
    GET_WEATHER = "get_weather"
    STORE_DATA = "store_data"
    SEARCH = "search"
    DECISION = "decision"
    CODE = "code"
    WORKFLOW = "workflow"
    FILE_INTERACTION = "file_interaction"
    WORKFLOW_INTERACTION = "workflow_interaction"
    DEEP_RESEARCH = "deep_research"


class CanvasToolName(Enum):
    """Available canvas tools."""

    ACTIVE_GRID_AREA = "active_grid_area"
    BRUSH = "brush"
    ERASER = "eraser"
    SELECTION = "selection"
    GRID = "grid"
    MOVE = "move"
    NONE = "none"


class ImageGenerator(Enum):
    """Supported image generators."""

    STABLEDIFFUSION = "stablediffusion"
    ZIMAGE = "zimage"


class GeneratorSection(Enum):
    """Supported art generator sections."""

    TXT2IMG = "txt2img"
    IMG2IMG = "img2img"
    INPAINT = "inpaint"
    OUTPAINT = "outpaint"
    UPSCALER = "x4-upscaler"


class ArtVersion(Enum):
    """Supported art model versions available for inference."""

    NONE = "None"
    SDXL1_0 = "SDXL 1.0"
    SDXL_LIGHTNING = "SDXL Lightning"
    SDXL_HYPER = "SDXL Hyper"
    X4_UPSCALER = "x4-upscaler"
    Z_IMAGE_TURBO = "Z-Image Turbo"


# Keep legacy alias so any external code importing StableDiffusionVersion still works.
StableDiffusionVersion = ArtVersion

DEFAULT_IMAGE_GENERATOR = ImageGenerator.ZIMAGE
DEFAULT_ART_VERSION = ArtVersion.Z_IMAGE_TURBO


def normalize_image_generator_name(value: str | None) -> str:
    """Return a supported image generator name string."""
    if value in {item.value for item in ImageGenerator}:
        return str(value)
    return DEFAULT_IMAGE_GENERATOR.value


def normalize_art_version(value: str | None) -> str:
    """Return a supported art version string."""
    if value in {item.value for item in ArtVersion}:
        return str(value)
    return DEFAULT_ART_VERSION.value


class Gender(Enum):
    """Supported chatbot voice genders."""

    MALE = "Male"
    FEMALE = "Female"


class ModelStatus(Enum):
    """Lifecycle states for managed models."""

    UNLOADED = "Unloaded"
    LOADED = "Loaded"
    READY = "Ready"
    LOADING = "Loading"
    UNLOADING = "Unloading"
    FAILED = "Failed"


class ModelType(Enum):
    """Model categories used by shared workers."""

    LORA = "Lora"
    EMBEDDINGS = "Embeddings"
    SD = "SD Model"
    RMBG = "RMBG Model"
    SD_VAE = "SD VAE"
    SD_UNET = "SD UNet"
    SD_TOKENIZER = "SD Tokenizer"
    SD_TEXT_ENCODER = "SD Text Encoder"
    SAFETY_CHECKER = "Safety Checker"
    FEATURE_EXTRACTOR = "Feature Extractor"
    TTS = "TTS Model"
    TTS_PROCESSOR = "TTS Processor"
    TTS_FEATURE_EXTRACTOR = "TTS Feature Extractor"
    TTS_VOCODER = "TTS Vocoder"
    TTS_SPEAKER_EMBEDDINGS = "TTS Speaker Embeddings"
    TTS_TOKENIZER = "TTS Tokenizer"
    TTS_DATASET = "TTS Dataset"
    STT = "STT Model"
    STT_PROCESSOR = "STT Processor"
    STT_FEATURE_EXTRACTOR = "STT Feature Extractor"
    CONTROLNET = "SD Controlnet"
    CONTROLNET_PROCESSOR = "SD Controlnet Processor"
    UPSCALER = "Upscaler"
    SCHEDULER = "SD Scheduler"
    LLM = "LLM Model"
    LLM_TOKENIZER = "LLM Tokenizer"


class TTSModel(Enum):
    """Supported text-to-speech backends."""

    ESPEAK = "Espeak"
    OPENVOICE = "OpenVoice"


class AvailableLanguage(Enum):
    """Languages supported by OpenVoice and Melo runtimes."""

    AUTO = "Automatic"
    EN = "EN"
    ES = "ES"
    FR = "FR"
    ZH = "ZH"
    ZH_MIX_EN = "ZH_MIX_EN"
    JP = "JP"
    KR = "KR"
    SP = "SP"


class ModelService(Enum):
    """LLM service backends persisted in settings."""

    LOCAL = "local"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    OPENAI = "openai"


__all__ = [
    "AvailableLanguage",
    "CanvasToolName",
    "DEFAULT_ART_VERSION",
    "DEFAULT_IMAGE_GENERATOR",
    "EngineResponseCode",
    "Gender",
    "GeneratorSection",
    "ImageGenerator",
    "LLMActionType",
    "Mode",
    "ModelService",
    "ModelStatus",
    "ModelType",
    "Scheduler",
    "SignalCode",
    "ArtVersion",
    "StableDiffusionVersion",
    "TTSModel",
    "normalize_art_version",
    "normalize_image_generator_name",
]
