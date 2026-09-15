"""Service-owned application model registry."""

from airunner_services.database.models import ActiveGridSettings
from airunner_services.database.models import AIModels
from airunner_services.database.models import AIRunnerSettings
from airunner_services.database.models import ApplicationSettings
from airunner_services.database.models import BrushSettings
from airunner_services.database.models import CanvasLayer
from airunner_services.database.models import Chatbot
from airunner_services.database.models import Chatstore
from airunner_services.database.models import ControlnetModel
from airunner_services.database.models import ControlnetSettings
from airunner_services.database.models import Conversation
from airunner_services.database.models import Document
from airunner_services.database.models import DrawingPadSettings
from airunner_services.database.models import EspeakSettings
from airunner_services.database.models import FontSetting
from airunner_services.database.models import GeneratorSettings
from airunner_services.database.models import GridSettings
from airunner_services.database.models import ImageFilter
from airunner_services.database.models import ImageFilterValue
from airunner_services.database.models import ImageToImageSettings
from airunner_services.database.models import LanguageSettings
from airunner_services.database.models import LLMGeneratorSettings
from airunner_services.database.models import MemorySettings
from airunner_services.database.models import MetadataSettings
from airunner_services.database.models import OpenVoiceSettings
from airunner_services.database.models import OutpaintSettings
from airunner_services.database.models import PathSettings
from airunner_services.database.models import PipelineModel
from airunner_services.database.models import PromptTemplate
from airunner_services.database.models import RAGSettings
from airunner_services.database.models import SavedPrompt
from airunner_services.database.models import Schedulers
from airunner_services.database.models import ShortcutKeys
from airunner_services.database.models import SoundSettings
from airunner_services.database.models import STTSettings
from airunner_services.database.models import Summary
from airunner_services.database.models import TargetDirectories
from airunner_services.database.models import TargetFiles
from airunner_services.database.models import User
from airunner_services.database.models import VoiceSettings
from airunner_services.database.models import WhisperSettings
from airunner_services.database.models import ZimFile


classes = [
	ActiveGridSettings,
	ApplicationSettings,
	CanvasLayer,
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
	SavedPrompt,
	PromptTemplate,
	ControlnetModel,
	FontSetting,
	PipelineModel,
	Conversation,
	Summary,
	ImageFilter,
	ImageFilterValue,
	WhisperSettings,
	VoiceSettings,
	OpenVoiceSettings,
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