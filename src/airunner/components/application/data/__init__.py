from airunner.components.settings.data.voice_settings import VoiceSettings
from airunner.components.settings.data.sound_settings import SoundSettings
from airunner.components.tts.data.models.openvoice_settings import (
    OpenVoiceSettings,
)
from airunner.components.art.data.active_grid_settings import (
    ActiveGridSettings,
)
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.llm.data.chatstore import Chatstore
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.tts.data.models.espeak_settings import EspeakSettings
from airunner.components.stt.data.stt_settings import STTSettings
from airunner.components.art.data.schedulers import Schedulers
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.grid_settings import GridSettings
from airunner.components.settings.data.path_settings import PathSettings
from airunner.components.art.data.memory_settings import MemorySettings
from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.user.data.user import User
from airunner.components.llm.data.target_files import TargetFiles
from airunner.components.llm.data.target_directories import TargetDirectories
from airunner.components.art.data.ai_models import AIModels
from airunner.components.application.data.shortcut_keys import ShortcutKeys
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.saved_prompt import SavedPrompt
from airunner.components.art.data.embedding import Embedding
from airunner.components.llm.data.prompt_template import PromptTemplate
from airunner.components.art.data.controlnet_model import ControlnetModel
from airunner.components.settings.data.font_setting import FontSetting
from airunner.components.models.data.pipeline_model import PipelineModel
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.data.summary import Summary
from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.data.image_filter_value import ImageFilterValue
from airunner.components.stt.data.whisper_settings import WhisperSettings
from airunner.components.news.data.news import RSSFeed, Category, Article
from airunner.components.nodegraph.data.workflow import Workflow
from airunner.components.nodegraph.data.workflow_node import WorkflowNode
from airunner.components.nodegraph.data.workflow_connection import (
    WorkflowConnection,
)
from airunner.components.llm.data.rag_settings import RAGSettings
from airunner.components.settings.data.language_settings import (
    LanguageSettings,
)
from airunner.components.settings.data.airunner_settings import (
    AIRunnerSettings,
)
from airunner.components.documents.data.models.document import Document
from airunner.components.documents.data.models.zimfile import ZimFile


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
    ZimFile,
]

class_names = []
table_to_class = {}
for cls in classes:
    table_to_class[cls.__tablename__] = cls
    class_names.append(cls.__name__)

__all__ = class_names
