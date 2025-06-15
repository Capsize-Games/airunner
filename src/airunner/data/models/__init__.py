from airunner.data.models.voice_settings import VoiceSettings
from airunner.data.models.sound_settings import SoundSettings
from airunner.data.models.openvoice_settings import OpenVoiceSettings
from airunner.components.art.data.active_grid_settings import (
    ActiveGridSettings,
)
from airunner.data.models.application_settings import ApplicationSettings
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.llm.data.chatstore import Chatstore
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
from airunner.components.tts.data.models.speech_t5_settings import SpeechT5Settings
from airunner.data.models.espeak_settings import EspeakSettings
from airunner.components.stt.data.stt_settings import STTSettings
from airunner.data.models.schedulers import Schedulers
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.grid_settings import GridSettings
from airunner.data.models.path_settings import PathSettings
from airunner.components.art.data.memory_settings import MemorySettings
from airunner.components.llm.data.chatbot import Chatbot
from airunner.data.models.user import User
from airunner.data.models.target_files import TargetFiles
from airunner.data.models.target_directories import TargetDirectories
from airunner.data.models.ai_models import AIModels
from airunner.data.models.shortcut_keys import ShortcutKeys
from airunner.components.art.data.lora import Lora
from airunner.data.models.saved_prompt import SavedPrompt
from airunner.components.art.data.embedding import Embedding
from airunner.data.models.prompt_template import PromptTemplate
from airunner.components.art.data.controlnet_model import ControlnetModel
from airunner.data.models.font_setting import FontSetting
from airunner.data.models.pipeline_model import PipelineModel
from airunner.components.llm.data.conversation import Conversation
from airunner.data.models.summary import Summary
from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.data.image_filter_value import ImageFilterValue
from airunner.components.stt.data.whisper_settings import WhisperSettings
from airunner.data.models.news import RSSFeed, Category, Article
from airunner.data.models.tab import Tab
from airunner.data.models.workflow import Workflow
from airunner.data.models.workflow_node import WorkflowNode
from airunner.data.models.workflow_connection import WorkflowConnection
from airunner.components.llm.data.rag_settings import RAGSettings
from airunner.data.models.language_settings import LanguageSettings
from airunner.data.models.airunner_settings import AIRunnerSettings
from airunner.components.documents.data.models.document import Document
from airunner.data.models.base import Base


classes = [
    ActiveGridSettings,
    ApplicationSettings,
    ControlnetSettings,
    ImageToImageSettings,
    OutpaintSettings,
    Chatstore,
    DrawingPadSettings,
    MetadataSettings,
    GeneratorSettings,
    LLMGeneratorSettings,
    SpeechT5Settings,
    EspeakSettings,
    STTSettings,
    Schedulers,
    BrushSettings,
    GridSettings,
    PathSettings,
    MemorySettings,
    Chatbot,
    User,
    TargetFiles,
    TargetDirectories,
    AIModels,
    ShortcutKeys,
    Lora,
    SavedPrompt,
    Embedding,
    PromptTemplate,
    ControlnetModel,
    FontSetting,
    PipelineModel,
    Conversation,
    Summary,
    ImageFilter,
    ImageFilterValue,
    WhisperSettings,
    RSSFeed,
    Category,
    Article,
    Tab,
    VoiceSettings,
    OpenVoiceSettings,
    Workflow,
    WorkflowNode,
    WorkflowConnection,
    RAGSettings,
    LanguageSettings,
    AIRunnerSettings,
    SoundSettings,
    Document,
    Base,
]

class_names = []
table_to_class = {}
for cls in classes:
    if cls is not Base:
        table_to_class[cls.__tablename__] = cls
    class_names.append(cls.__name__)

__all__ = class_names
