"""Service-owned database model compatibility surface."""

from airunner_services.database.models.active_grid_settings import (
    ActiveGridSettings,
)
from airunner_services.database.models.ai_models import AIModels
from airunner_services.database.models.agent_config import AgentConfig
from airunner_services.database.models.airunner_settings import AIRunnerSettings
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.models.brush_settings import BrushSettings
from airunner_services.database.models.canvas_layer import CanvasLayer
from airunner_services.database.models.chatstore import Chatstore
from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.controlnet_model import ControlnetModel
from airunner_services.database.models.controlnet_settings import (
    ControlnetSettings,
)
from airunner_services.database.models.conversation import Conversation
from airunner_services.database.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_services.database.models.document import Document
from airunner_services.database.models.espeak_settings import EspeakSettings
from airunner_services.database.models.font_setting import FontSetting
from airunner_services.database.models.generator_settings import (
    GeneratorSettings,
)
from airunner_services.database.models.grid_settings import GridSettings
from airunner_services.database.models.image_filter import ImageFilter
from airunner_services.database.models.image_filter_value import (
    ImageFilterValue,
)
from airunner_services.database.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_services.database.models.language_settings import (
    LanguageSettings,
)
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.models.memory_settings import MemorySettings
from airunner_services.database.models.llm_tool import LLMTool
from airunner_services.database.models.metadata_settings import (
    MetadataSettings,
)
from airunner_services.database.models.openvoice_settings import (
    OpenVoiceSettings,
)
from airunner_services.database.models.outpaint_settings import (
    OutpaintSettings,
)
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.database.models.pipeline_model import PipelineModel
from airunner_services.database.models.prompt_template import PromptTemplate
from airunner_services.database.models.project_state import DecisionMemory
from airunner_services.database.models.project_state import DecisionOutcome
from airunner_services.database.models.project_state import FeatureCategory
from airunner_services.database.models.project_state import FeatureStatus
from airunner_services.database.models.project_state import ProgressEntry
from airunner_services.database.models.project_state import ProjectFeature
from airunner_services.database.models.project_state import ProjectState
from airunner_services.database.models.project_state import ProjectStatus
from airunner_services.database.models.project_state import SessionState
from airunner_services.database.models.rag_settings import RAGSettings
from airunner_services.database.models.saved_prompt import SavedPrompt
from airunner_services.database.models.schedulers import Schedulers
from airunner_services.database.models.shortcut_keys import ShortcutKeys
from airunner_services.database.models.sound_settings import SoundSettings
from airunner_services.database.models.stt_settings import STTSettings
from airunner_services.database.models.summary import Summary
from airunner_services.database.models.target_directories import (
    TargetDirectories,
)
from airunner_services.database.models.target_files import TargetFiles
from airunner_services.database.models.user import User
from airunner_services.database.models.voice_settings import VoiceSettings
from airunner_services.database.models.whisper_settings import (
    WhisperSettings,
)
from airunner_services.database.models.zimfile import ZimFile
from airunner_services.database.models.lora import Lora
from airunner_services.database.models.embedding import Embedding
from airunner_services.database.models.fine_tuned_model import FineTunedModel

__all__ = [
    "ActiveGridSettings",
    "AIModels",
    "AgentConfig",
    "AIRunnerSettings",
    "ApplicationSettings",
    "BrushSettings",
    "CanvasLayer",
    "Chatstore",
    "Chatbot",
    "ControlnetModel",
    "ControlnetSettings",
    "Conversation",
    "DecisionMemory",
    "DecisionOutcome",
    "DrawingPadSettings",
    "Document",
    "Embedding",
    "EspeakSettings",
    "FeatureCategory",
    "FeatureStatus",
    "FineTunedModel",
    "FontSetting",
    "GeneratorSettings",
    "GridSettings",
    "ImageFilter",
    "ImageFilterValue",
    "ImageToImageSettings",
    "LanguageSettings",
    "LLMTool",
    "LLMGeneratorSettings",
    "Lora",
    "MemorySettings",
    "MetadataSettings",
    "OpenVoiceSettings",
    "OutpaintSettings",
    "PathSettings",
    "PipelineModel",
    "ProgressEntry",
    "ProjectFeature",
    "ProjectState",
    "ProjectStatus",
    "PromptTemplate",
    "RAGSettings",
    "SavedPrompt",
    "Schedulers",
    "SessionState",
    "ShortcutKeys",
    "SoundSettings",
    "STTSettings",
    "Summary",
    "TargetDirectories",
    "TargetFiles",
    "User",
    "VoiceSettings",
    "WhisperSettings",
    "ZimFile",
]