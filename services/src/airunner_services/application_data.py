"""Service-owned application model registry."""

from airunner_model.models import ActiveGridSettings
from airunner_model.models import AIModels
from airunner_model.models import AIRunnerSettings
from airunner_model.models import ApplicationSettings
from airunner_model.models import BrushSettings
from airunner_model.models import CanvasLayer
from airunner_model.models import Chatbot
from airunner_model.models import Chatstore
from airunner_model.models import ControlnetModel
from airunner_model.models import ControlnetSettings
from airunner_model.models import Conversation
from airunner_model.models import Document
from airunner_model.models import DrawingPadSettings
from airunner_model.models import EspeakSettings
from airunner_model.models import FontSetting
from airunner_model.models import GeneratorSettings
from airunner_model.models import GridSettings
from airunner_model.models import ImageFilter
from airunner_model.models import ImageFilterValue
from airunner_model.models import ImageToImageSettings
from airunner_model.models import LanguageSettings
from airunner_model.models import LLMGeneratorSettings
from airunner_model.models import MemorySettings
from airunner_model.models import MetadataSettings
from airunner_model.models import OpenVoiceSettings
from airunner_model.models import OutpaintSettings
from airunner_model.models import PathSettings
from airunner_model.models import PipelineModel
from airunner_model.models import PromptTemplate
from airunner_model.models import RAGSettings
from airunner_model.models import SavedPrompt
from airunner_model.models import Schedulers
from airunner_model.models import ShortcutKeys
from airunner_model.models import SoundSettings
from airunner_model.models import STTSettings
from airunner_model.models import Summary
from airunner_model.models import TargetDirectories
from airunner_model.models import TargetFiles
from airunner_model.models import User
from airunner_model.models import VoiceSettings
from airunner_model.models import WhisperSettings
from airunner_model.models import ZimFile


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