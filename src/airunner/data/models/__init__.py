from airunner.data.models.voice_settings import VoiceSettings
from airunner.data.models.sound_settings import SoundSettings
from airunner.data.models.openvoice_settings import OpenVoiceSettings
from airunner.data.models.active_grid_settings import ActiveGridSettings
from airunner.data.models.application_settings import ApplicationSettings
from airunner.data.models.controlnet_settings import ControlnetSettings
from airunner.data.models.image_to_image_settings import ImageToImageSettings
from airunner.data.models.outpaint_settings import OutpaintSettings
from airunner.data.models.chatstore import Chatstore
from airunner.data.models.drawingpad_settings import DrawingPadSettings
from airunner.data.models.metadata_settings import MetadataSettings
from airunner.data.models.generator_settings import GeneratorSettings
from airunner.data.models.llm_generator_settings import LLMGeneratorSettings
from airunner.data.models.speech_t5_settings import SpeechT5Settings
from airunner.data.models.espeak_settings import EspeakSettings
from airunner.data.models.stt_settings import STTSettings
from airunner.data.models.schedulers import Schedulers
from airunner.data.models.brush_settings import BrushSettings
from airunner.data.models.grid_settings import GridSettings
from airunner.data.models.path_settings import PathSettings
from airunner.data.models.memory_settings import MemorySettings
from airunner.data.models.chatbot import Chatbot
from airunner.data.models.user import User
from airunner.data.models.target_files import TargetFiles
from airunner.data.models.target_directories import TargetDirectories
from airunner.data.models.ai_models import AIModels
from airunner.data.models.shortcut_keys import ShortcutKeys
from airunner.data.models.lora import Lora
from airunner.data.models.saved_prompt import SavedPrompt
from airunner.data.models.embedding import Embedding
from airunner.data.models.prompt_template import PromptTemplate
from airunner.data.models.controlnet_model import ControlnetModel
from airunner.data.models.font_setting import FontSetting
from airunner.data.models.pipeline_model import PipelineModel
from airunner.data.models.conversation import Conversation
from airunner.data.models.summary import Summary
from airunner.data.models.image_filter import ImageFilter
from airunner.data.models.image_filter_value import ImageFilterValue
from airunner.data.models.whisper_settings import WhisperSettings
from airunner.data.models.news import RSSFeed, Category, Article
from airunner.data.models.tab import Tab
from airunner.data.models.workflow import Workflow
from airunner.data.models.workflow_node import WorkflowNode
from airunner.data.models.workflow_connection import WorkflowConnection
from airunner.data.models.rag_settings import RAGSettings
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
    Base,
]

class_names = []
table_to_class = {}
for cls in classes:
    if cls is not Base:
        table_to_class[cls.__tablename__] = cls
    class_names.append(cls.__name__)

__all__ = class_names
