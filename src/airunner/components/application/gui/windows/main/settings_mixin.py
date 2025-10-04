import os
from typing import List, Type, Optional, Dict, Any

from sqlalchemy.orm import joinedload
from airunner.components.data.session_manager import session_scope
from sqlalchemy.orm import joinedload
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import make_transient

from PySide6.QtWidgets import QApplication

from airunner.components.application.data import ShortcutKeys, table_to_class
from airunner.components.art.data.active_grid_settings import (
    ActiveGridSettings,
)
from airunner.components.art.data.ai_models import AIModels
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.controlnet_model import ControlnetModel
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.embedding import Embedding
from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.components.art.data.grid_settings import GridSettings
from airunner.components.art.data.image_filter_value import ImageFilterValue
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.memory_settings import MemorySettings
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.data.saved_prompt import SavedPrompt
from airunner.components.art.data.schedulers import Schedulers
from airunner.components.art.utils.layer_compositor import layer_compositor
from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.llm.data.prompt_template import PromptTemplate
from airunner.components.llm.data.target_files import TargetFiles
from airunner.components.models.data.pipeline_model import PipelineModel
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.components.settings.data.font_setting import FontSetting
from airunner.components.settings.data.language_settings import (
    LanguageSettings,
)
from airunner.components.llm.data.rag_settings import RAGSettings
from airunner.components.settings.data.path_settings import PathSettings
from airunner.components.settings.data.sound_settings import SoundSettings
from airunner.components.settings.data.voice_settings import VoiceSettings
from airunner.components.stt.data.stt_settings import STTSettings
from airunner.components.stt.data.whisper_settings import WhisperSettings
from airunner.components.tts.data.models.espeak_settings import EspeakSettings
from airunner.components.tts.data.models.openvoice_settings import (
    OpenVoiceSettings,
)
from airunner.components.tts.data.models.speech_t5_settings import (
    SpeechT5Settings,
)
from airunner.components.user.data.user import User
from airunner.enums import ModelService, TTSModel, SignalCode
from airunner.utils.image import convert_binary_to_image
from airunner.components.data.session_manager import session_scope
from airunner.components.llm.utils import get_chatbot
from airunner.utils.settings import get_qsettings
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL

from airunner.components.settings.data.window_settings import WindowSettings


class SettingsMixinSharedInstance:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsMixinSharedInstance, cls).__new__(
                cls, *args, **kwargs
            )
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = get_logger("AI Runner", AIRUNNER_LOG_LEVEL)

        self._initialized = True
        self.chatbot: Optional[Chatbot] = None
        # Cache for settings instances keyed by model class to avoid repeated DB reads
        self._settings_cache: Dict[Type[Any], Any] = {}
        # Cache for layer-specific settings instances keyed by string keys
        self._settings_cache_by_key: Dict[str, Any] = {}
        self._cached_send_image_to_canvas: List[Dict] = []

    @property
    def cached_send_image_to_canvas(self) -> List[Dict]:
        return self._cached_send_image_to_canvas

    @cached_send_image_to_canvas.setter
    def cached_send_image_to_canvas(self, value: List[Dict]) -> None:
        self._cached_send_image_to_canvas = value

    def get_cached_setting(self, model_class: Type[Any]) -> Optional[Any]:
        """Return a cached settings instance if present."""
        return self._settings_cache.get(model_class)

    def set_cached_setting(
        self, model_class: Type[Any], instance: Any
    ) -> None:
        """Store a settings instance in cache."""
        self._settings_cache[model_class] = instance

    def get_cached_setting_by_key(self, key: str) -> Optional[Any]:
        """Return a cached settings instance by string key if present."""
        return self._settings_cache_by_key.get(key)

    def set_cached_setting_by_key(self, key: str, instance: Any) -> None:
        """Store a settings instance in cache by string key."""
        self._settings_cache_by_key[key] = instance

    def invalidate_cached_setting(self, model_class: Type[Any]) -> None:
        """Remove a settings instance from cache."""
        self._settings_cache.pop(model_class, None)

    def on_settings_updated(
        self, setting_name: Optional[str], column_name: Optional[str], val: Any
    ) -> None:
        """Update or invalidate cache when settings change.

        Args:
            setting_name: Table name for the setting (SQLAlchemy __tablename__).
            column_name: Column updated, if any.
            val: New value for the column if column_name is provided.
        """
        if not setting_name:
            return

        model_class = table_to_class.get(setting_name)
        if not model_class:
            # Fallback: attempt to find matching class by __tablename__ within cached classes
            for cls in list(self._settings_cache.keys()):
                try:
                    if getattr(cls, "__tablename__", None) == setting_name:
                        model_class = cls
                        break
                except Exception:
                    continue
            if not model_class:
                return

        cached = self.get_cached_setting(model_class)
        if cached is None:
            return

        if column_name:
            try:
                setattr(cached, column_name, val)
            except Exception:
                # If direct assignment fails for any reason, drop cache
                self.invalidate_cached_setting(model_class)
        else:
            # Unknown change scope; safest is to drop cache to force reload on next access
            self.invalidate_cached_setting(model_class)


class SettingsMixin:
    _chatbot: Optional[Chatbot] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize layer selection tracking
        self._selected_layer_ids = set()

        # Add layer selection signal handler if signal_handlers exists
        if (
            hasattr(self, "signal_handlers")
            and self.signal_handlers is not None
        ):
            self.signal_handlers[SignalCode.LAYER_SELECTION_CHANGED] = (
                self._on_layer_selection_changed
            )
        else:
            self.signal_handlers = {
                SignalCode.LAYER_SELECTION_CHANGED: self._on_layer_selection_changed
            }

        app = QApplication.instance()
        if app:
            self.api = getattr(app, "api", None)

    @property
    def cached_send_image_to_canvas(self) -> List[Dict]:
        return self.settings_mixin_shared_instance._cached_send_image_to_canvas

    @cached_send_image_to_canvas.setter
    def cached_send_image_to_canvas(self, value: List[Dict]) -> None:
        self.settings_mixin_shared_instance._cached_send_image_to_canvas = (
            value
        )

    @property
    def user_web_dir(self) -> str:
        """Return the user web directory."""
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path), "web"
        )

    @property
    def session_manager(self):
        return self.settings_mixin_shared_instance.session_manager

    @property
    def settings_mixin_shared_instance(self):
        return SettingsMixinSharedInstance()

    @property
    def logger(self):
        return self.settings_mixin_shared_instance.logger

    def clear_cache_settings(self):
        """Clear all cached settings instances."""
        self.settings_mixin_shared_instance._settings_cache.clear()
        self.settings_mixin_shared_instance._settings_cache_by_key.clear()

    def _get_or_cache_settings(
        self, model_class_: Type[Any], eager_load: Optional[List[str]] = None
    ) -> Any:
        """Get a settings instance from cache or load and cache it.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model.
        """
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            model_class_
        )
        if cached is not None:
            return cached
        instance = self.load_settings_from_db(
            model_class_, eager_load=eager_load
        )
        self.settings_mixin_shared_instance.set_cached_setting(
            model_class_, instance
        )
        return instance

    def _get_layer_specific_settings(
        self,
        model_class_: Type[Any],
        layer_id: Optional[int] = None,
        eager_load: Optional[List[str]] = None,
    ) -> Any:
        """Get layer-specific settings instance.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            layer_id: Layer ID to get settings for. If None, gets settings for first selected layer.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model for the specified layer.
        """
        # If no layer_id provided, try to get the first selected layer
        if layer_id is None:
            layer_id = self._get_current_selected_layer_id()

        # If still no layer_id, fall back to global settings (for backwards compatibility)
        if layer_id is None:
            return self._get_or_cache_settings(
                model_class_, eager_load=eager_load
            )

        # Check cache first with layer-specific key
        cache_key = f"{model_class_.__name__}_layer_{layer_id}"
        cached = self.settings_mixin_shared_instance.get_cached_setting_by_key(
            cache_key
        )
        if cached is not None:
            return cached

        # Load layer-specific settings from database
        instance = self._load_layer_settings_from_db(
            model_class_, layer_id, eager_load=eager_load
        )

        # Cache the result
        self.settings_mixin_shared_instance.set_cached_setting_by_key(
            cache_key, instance
        )
        return instance

    def _on_layer_selection_changed(self, data: Dict[str, Any]):
        """Handle layer selection changes from the canvas layer container."""
        selected_layer_ids = data.get("selected_layer_ids", [])
        self._selected_layer_ids = set(selected_layer_ids)

    def _get_current_selected_layer_id(self) -> Optional[int]:
        """Get the first selected layer ID from the current UI state.

        Returns:
            The first selected layer ID, or None if no layers are selected.
        """
        # Return the first selected layer ID, or None if no selection
        if self._selected_layer_ids:
            return min(
                self._selected_layer_ids
            )  # Use the lowest ID for consistency
        default_layer_id = self._get_first_layer_id()
        if default_layer_id is not None:
            self._selected_layer_ids.add(default_layer_id)
        return default_layer_id

    def _get_first_layer_id(self) -> Optional[int]:
        """Return the ID for the first persisted layer ordered by `order`."""
        try:
            primary_layer = CanvasLayer.objects.filter_first(
                CanvasLayer.order == 0
            )
            if primary_layer is None:
                primary_layer = CanvasLayer.objects.first()
            return primary_layer.id if primary_layer else None
        except Exception as exc:
            self.logger.warning(
                "Unable to determine default layer id: %s", exc
            )
        return None

    def _load_layer_settings_from_db(
        self,
        model_class_: Type[Any],
        layer_id: int,
        eager_load: Optional[List[str]] = None,
    ) -> Any:
        """Load layer-specific settings from database, creating if not exists.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            layer_id: Layer ID to get settings for.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model for the specified layer.
        """
        try:
            with session_scope() as session:
                query = session.query(model_class_).filter(
                    model_class_.layer_id == layer_id
                )

                if eager_load:
                    for relation in eager_load:
                        try:
                            relation_attr = getattr(
                                model_class_, relation, None
                            )
                            if relation_attr is not None:
                                query = query.options(
                                    joinedload(relation_attr)
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"Could not eager load {relation} for {model_class_.__name__}: {e}"
                            )

                settings_instance = query.first()

                if settings_instance is None:
                    # Create new settings instance for this layer
                    self.logger.info(
                        f"No layer-specific settings found for {model_class_.__name__} layer {layer_id}, creating new entry."
                    )
                    settings_instance = model_class_(layer_id=layer_id)
                    session.add(settings_instance)
                    session.commit()

                    # Refresh to get the full instance with relationships if needed
                    if eager_load:
                        query_after_create = session.query(
                            model_class_
                        ).filter(model_class_.layer_id == layer_id)
                        for relation in eager_load:
                            try:
                                relation_attr = getattr(
                                    model_class_, relation, None
                                )
                                if relation_attr is not None:
                                    query_after_create = (
                                        query_after_create.options(
                                            joinedload(relation_attr)
                                        )
                                    )
                            except Exception:
                                pass
                        settings_instance = query_after_create.first()

                # Create a detached copy with all the attributes we need
                # to avoid DetachedInstanceError when accessed later
                if settings_instance:
                    # Make sure all commonly used attributes are loaded before session closes
                    try:
                        # Access key attributes to ensure they're loaded
                        _ = (
                            settings_instance.x_pos
                            if hasattr(settings_instance, "x_pos")
                            else None
                        )
                        _ = (
                            settings_instance.y_pos
                            if hasattr(settings_instance, "y_pos")
                            else None
                        )
                        _ = (
                            settings_instance.strength
                            if hasattr(settings_instance, "strength")
                            else None
                        )
                        _ = (
                            settings_instance.scale
                            if hasattr(settings_instance, "scale")
                            else None
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Could not pre-load attributes for {model_class_.__name__}: {e}"
                        )

                # Use expunge to detach from session to prevent DetachedInstanceError
                if settings_instance:
                    session.expunge(settings_instance)

                return settings_instance

        except Exception as e:
            self.logger.error(
                f"Error loading layer-specific settings for {model_class_.__name__} layer {layer_id}: {e}"
            )
            # Fall back to creating a default instance
            return model_class_(layer_id=layer_id)

    def _get_target_image_size(self) -> Optional[tuple]:
        """Get target image size for layer composition based on generator settings.

        Returns:
            Tuple of (width, height) if available, None otherwise.
        """
        try:
            gen_settings = self.generator_settings
            if (
                gen_settings
                and hasattr(gen_settings, "width")
                and hasattr(gen_settings, "height")
            ):
                return (gen_settings.width, gen_settings.height)
        except Exception as e:
            self.logger.debug(
                f"Could not get target image size from generator settings: {e}"
            )

        # Default size if generator settings not available
        return (512, 512)

    @property
    def stt_settings(self) -> STTSettings:
        return self._get_or_cache_settings(STTSettings)

    @property
    def application_settings(self) -> ApplicationSettings:
        return self._get_or_cache_settings(ApplicationSettings)

    @property
    def language_settings(self) -> LanguageSettings:
        return self._get_or_cache_settings(LanguageSettings)

    @property
    def sound_settings(self) -> SoundSettings:
        return self._get_or_cache_settings(SoundSettings)

    @property
    def whisper_settings(self) -> WhisperSettings:
        return self._get_or_cache_settings(WhisperSettings)

    @property
    def window_settings(self) -> WindowSettings:
        settings = get_qsettings()
        settings.beginGroup("window_settings")
        window_settings = WindowSettings(
            is_maximized=settings.value("is_maximized", False, type=bool),
            is_fullscreen=settings.value("is_fullscreen", False, type=bool),
            width=settings.value("width", 800, type=int),
            height=settings.value("height", 600, type=int),
            x_pos=settings.value("x_pos", 0, type=int),
            y_pos=settings.value("y_pos", 0, type=int),
            active_main_tab_index=settings.value(
                "active_main_tab_index", 0, type=int
            ),
        )
        settings.endGroup()
        return window_settings

    @window_settings.setter
    def window_settings(self, settings_dict: Dict[str, Any]):
        """Update window settings in QSettings."""
        settings = get_qsettings()
        settings.beginGroup("window_settings")
        for key, value in settings_dict.items():
            if key in ["is_maximized", "is_fullscreen"]:
                value = bool(value)
            else:
                value = int(value)
            settings.setValue(key, value)
        settings.endGroup()
        settings.sync()
        self.__settings_updated(
            setting_name="window_settings", column_name=None, val=None
        )

    @property
    def rag_settings(self) -> RAGSettings:
        rag_settings = RAGSettings.objects.first()
        if rag_settings is None:
            RAGSettings.objects.create(
                enabled=False,
                model_service=ModelService.LOCAL.value,
                model_path="",
            )
            rag_settings = RAGSettings.objects.first()
        return rag_settings

    @property
    def llm_generator_settings(self) -> LLMGeneratorSettings:
        """Return the LLMGeneratorSettings instance from the database, creating it if necessary.
        No longer manages current_chatbot; current chatbot is determined via Chatbot.objects.filter_by(current=True).
        """
        return self._get_or_cache_settings(LLMGeneratorSettings)

    @property
    def generator_settings(self) -> GeneratorSettings:
        return self._get_or_cache_settings(
            GeneratorSettings, eager_load=["aimodel"]
        )

    @property
    def controlnet_settings(self) -> ControlnetSettings:
        return self._get_layer_specific_settings(ControlnetSettings)

    @property
    def image_to_image_settings(self) -> ImageToImageSettings:
        return self._get_layer_specific_settings(ImageToImageSettings)

    @property
    def outpaint_settings(self) -> OutpaintSettings:
        return self._get_layer_specific_settings(OutpaintSettings)

    @property
    def drawing_pad_settings(self) -> DrawingPadSettings:
        return self._get_layer_specific_settings(DrawingPadSettings)

    @property
    def brush_settings(self) -> BrushSettings:
        return self._get_or_cache_settings(BrushSettings)

    @property
    def metadata_settings(self) -> MetadataSettings:
        return self._get_or_cache_settings(MetadataSettings)

    @property
    def grid_settings(self) -> GridSettings:
        return self._get_or_cache_settings(GridSettings)

    @property
    def active_grid_settings(self) -> ActiveGridSettings:
        return self._get_or_cache_settings(ActiveGridSettings)

    @property
    def path_settings(self) -> PathSettings:
        return self._get_or_cache_settings(PathSettings)

    @property
    def memory_settings(self) -> MemorySettings:
        return self._get_or_cache_settings(MemorySettings)

    @property
    def chatbots(self) -> List[Type[Chatbot]]:
        return self.load_chatbots()

    @property
    def ai_models(self) -> List[Type[AIModels]]:
        return self.load_ai_models()

    @property
    def schedulers(self) -> List[Type[Schedulers]]:
        return self.load_schedulers()

    @property
    def shortcut_keys(self) -> List[Type[ShortcutKeys]]:
        return self.load_shortcut_keys()

    @property
    def chatbot_voice_settings(self) -> VoiceSettings:
        if self.chatbot.voice_id is None:
            voice_settings = VoiceSettings.objects.first()
            if voice_settings is None:
                settings = self._get_settings_for_voice_settings(
                    TTSModel.ESPEAK
                )
                voice_settings = VoiceSettings.objects.create(
                    name="Default Voice",
                    model_type=TTSModel.ESPEAK.value,
                    settings_id=settings.id,
                )
            Chatbot.objects.update(
                self.chatbot.id,
                voice_id=voice_settings.id,
            )
            self.chatbot.voice_id = voice_settings.id

        voice_settings = VoiceSettings.objects.get(pk=self.chatbot.voice_id)

        if voice_settings is None:
            raise ValueError(
                "Chatbot voice settings not found. Please check the database."
            )

        return voice_settings

    @property
    def chatbot_voice_model_type(self) -> TTSModel:
        return TTSModel(self.chatbot_voice_settings.model_type)

    @property
    def speech_t5_settings(self) -> SpeechT5Settings:
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            SpeechT5Settings
        )
        if cached is not None:
            return cached
        settings = SpeechT5Settings.objects.first()
        if settings is None:
            settings = SpeechT5Settings.objects.create()
        self.settings_mixin_shared_instance.set_cached_setting(
            SpeechT5Settings, settings
        )
        return settings

    @property
    def espeak_settings(self) -> Optional[object]:
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            EspeakSettings
        )
        if cached is not None:
            return cached
        settings = EspeakSettings.objects.first()
        if settings is None:
            settings = EspeakSettings.objects.create()
        self.settings_mixin_shared_instance.set_cached_setting(
            EspeakSettings, settings
        )
        return settings

    @property
    def openvoice_settings(self) -> OpenVoiceSettings:
        cached = self.settings_mixin_shared_instance.get_cached_setting(
            OpenVoiceSettings
        )
        if cached is not None:
            return cached
        settings = OpenVoiceSettings.objects.first()
        if settings is None:
            settings = OpenVoiceSettings.objects.create()
        self.settings_mixin_shared_instance.set_cached_setting(
            OpenVoiceSettings, settings
        )
        return settings

    @property
    def metadata_settings(self) -> MetadataSettings:
        return self._get_or_cache_settings(MetadataSettings)

    @property
    def prompt_templates(self) -> List[Type[PromptTemplate]]:
        return self.load_prompt_templates()

    @property
    def controlnet_models(self):
        return self.load_controlnet_models()

    @property
    def saved_prompts(self) -> List[Type[SavedPrompt]]:
        return self.load_saved_prompts()

    @property
    def font_settings(self) -> List[Type[FontSetting]]:
        return self.load_font_settings()

    @property
    def pipelines(self) -> List[Type[PipelineModel]]:
        return self.load_pipelines()

    @property
    def drawing_pad_image(self):
        """Get composed image from all visible layers for drawing pad operations.

        Returns:
            PIL Image composed from all visible layers, or fallback to single layer image.
        """
        # Try to compose visible layers first
        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )

        if composed_image is not None:
            return composed_image.convert("RGB")

        # Fallback to original single-layer behavior
        base_64_image = self.drawing_pad_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def drawing_pad_mask(self):
        base_64_image = self.drawing_pad_settings.mask
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def img2img_image(self):
        """Get composed image from all visible layers for image-to-image operations.

        Returns:
            PIL Image composed from all visible layers, or fallback to single layer image.
        """
        # Try to compose visible layers first
        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )

        if composed_image is not None:
            return composed_image.convert("RGB")

        # Fallback to original single-layer behavior
        base_64_image = self.image_to_image_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_image(self):
        """Get composed image from all visible layers for controlnet operations.

        Returns:
            PIL Image composed from all visible layers, or fallback to single layer image.
        """
        # Try to compose visible layers first
        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )

        if composed_image is not None:
            return composed_image.convert("RGB")

        # Fallback to original single-layer behavior
        base_64_image = self.controlnet_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_generated_image(self):
        base_64_image = self.controlnet_settings.imported_image_base64
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def outpaint_mask(self):
        base_64_image = self.drawing_pad_settings.mask
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def outpaint_image(self):
        """Get composed image from all visible layers for outpaint operations.

        Returns:
            PIL Image composed from all visible layers, or fallback to single layer image.
        """
        # Try to compose visible layers first
        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )

        if composed_image is not None:
            return composed_image.convert("RGB")

        # Fallback to original single-layer behavior
        base_64_image = self.outpaint_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def image_filter_values(self) -> Optional[List[ImageFilterValue]]:
        return ImageFilterValue.objects.all()

    @property
    def chatbot(self) -> Optional[Chatbot]:
        return get_chatbot()

    def _get_settings_for_voice_settings(self, model_type: TTSModel):
        if model_type is TTSModel.SPEECHT5:
            return self.speech_t5_settings
        elif model_type is TTSModel.OPENVOICE:
            return self.openvoice_settings
        else:
            return self.espeak_settings

    @property
    def user(self) -> Type[User]:
        user = User.objects.first()
        if user is None:
            user = User()
            user.username = "User"
            user.save()
            user = User.objects.first()
        return user

    @staticmethod
    def add_chatbot_document_to_chatbot(chatbot, file_path):
        document = TargetFiles.objects.filter_by_first(
            chatbot_id=chatbot.id, file_path=file_path
        )
        if document is None:
            document = TargetFiles(file_path=file_path, chatbot_id=chatbot.id)
        TargetFiles.objects.merge(document)

    def update_application_settings(self, **settings_dict):
        self.update_settings(ApplicationSettings, settings_dict)

    def update_espeak_settings(self, **settings_dict):
        self.update_settings(EspeakSettings, settings_dict)

    def update_speech_t5_settings(self, **settings_dict):
        self.update_settings(SpeechT5Settings, settings_dict)

    def update_controlnet_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ):
        self.update_layer_settings(ControlnetSettings, settings_dict, layer_id)

    def update_brush_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ):
        self.update_layer_settings(BrushSettings, settings_dict, layer_id)

    def update_image_to_image_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ):
        self.update_layer_settings(
            ImageToImageSettings, settings_dict, layer_id
        )

    def update_outpaint_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ):
        self.update_layer_settings(OutpaintSettings, settings_dict, layer_id)

    def update_drawing_pad_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ):
        self.update_layer_settings(DrawingPadSettings, settings_dict, layer_id)

    def update_metadata_settings(
        self, layer_id: Optional[int] = None, **settings_dict
    ):
        self.update_layer_settings(MetadataSettings, settings_dict, layer_id)

    def update_grid_settings(self, **settings_dict):
        self.update_settings(GridSettings, settings_dict)

    def update_active_grid_settings(self, **settings_dict):
        self.update_settings(ActiveGridSettings, settings_dict)

    def update_path_settings(self, **settings_dict):
        self.update_settings(PathSettings, settings_dict)

    def update_memory_settings(self, **settings_dict):
        self.update_settings(MemorySettings, settings_dict)

    def update_metadata_settings(self, **settings_dict):
        self.update_settings(MetadataSettings, settings_dict)

    def update_llm_generator_settings(self, **settings_dict):
        self.update_settings(LLMGeneratorSettings, settings_dict)

    def update_whisper_settings(self, **settings_dict):
        self.update_settings(WhisperSettings, settings_dict)

    def update_generator_settings(self, **settings_dict):
        self.update_settings(GeneratorSettings, settings_dict)

    def update_controlnet_image_settings(self, **settings_dict):
        self.update_settings(ControlnetSettings, settings_dict)

    def update_ai_models(self, models: List[AIModels]):
        for model in models:
            self.update_ai_model(model)
        self.__settings_updated()

    def update_ai_model(self, model: AIModels):
        # Check if model exists in DB
        existing_dataclass = AIModels.objects.filter_by_first(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action,
            enabled=model.enabled,
            model_type=model.model_type,
            is_default=model.is_default,
        )

        if existing_dataclass:
            # Get the actual ORM instance using the primary key from the dataclass
            with session_scope() as session:
                orm_instance = (
                    session.query(AIModels)
                    .filter(AIModels.id == existing_dataclass.id)
                    .first()
                )
                if orm_instance:
                    # Update the ORM instance
                    for key in model.__dict__.keys():
                        if key not in ("_sa_instance_state", "id"):
                            setattr(orm_instance, key, getattr(model, key))
                    session.commit()
                else:
                    # Create new if we can't find the ORM instance
                    new_model = AIModels(
                        name=model.name,
                        path=model.path,
                        branch=model.branch,
                        version=model.version,
                        category=model.category,
                        pipeline_action=model.pipeline_action,
                        enabled=model.enabled,
                        model_type=model.model_type,
                        is_default=model.is_default,
                    )
                    session.add(new_model)
                    session.commit()
        else:
            # Create a new SQLAlchemy model instance
            new_model = AIModels(
                name=model.name,
                path=model.path,
                branch=model.branch,
                version=model.version,
                category=model.category,
                pipeline_action=model.pipeline_action,
                enabled=model.enabled,
                model_type=model.model_type,
                is_default=model.is_default,
            )
            new_model.save()
        self.__settings_updated()

    def update_setting_by_table_name(self, table_name, column_name, val):
        model_class_ = table_to_class.get(table_name)
        if model_class_ is None:
            self.logger.error(f"Model class for {table_name} not found")
            return
        setting = model_class_.objects.order_by(model_class_.id.desc()).first()
        if setting:
            model_class_.objects.update(setting.id, **{column_name: val})
            self.__settings_updated(table_name, column_name, val)
        else:
            self.logger.error("Failed to update settings: No setting found")

    @staticmethod
    def load_schedulers() -> List[Schedulers]:
        return Schedulers.objects.all()

    @staticmethod
    def load_settings_from_db(
        model_class_, eager_load: Optional[List[str]] = None
    ) -> Type:
        settings_instance = None
        try:
            with session_scope() as session:
                query = session.query(model_class_)
                if eager_load:
                    for relation in eager_load:
                        try:
                            relation_attr = getattr(
                                model_class_, relation, None
                            )
                            if relation_attr is not None:
                                query = query.options(
                                    joinedload(relation_attr)
                                )
                        except Exception as e:
                            # Use a local logger instance to avoid issues with shared state during initialization
                            local_logger = get_logger(
                                "AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL
                            )
                            local_logger.warning(
                                f"Could not eager load {relation} for {model_class_.__name__}: {e}"
                            )

                settings_instance = query.first()

                if settings_instance is None:
                    local_logger = get_logger(
                        "AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL
                    )
                    local_logger.info(
                        f"No settings found for {model_class_.__name__}, creating new entry."
                    )
                    settings_instance = model_class_()
                    session.add(settings_instance)
                    session.commit()
                    if settings_instance.id is not None:
                        query_after_create = session.query(model_class_)
                        if eager_load:
                            for relation in eager_load:
                                try:
                                    relation_attr = getattr(
                                        model_class_, relation, None
                                    )
                                    if relation_attr is not None:
                                        query_after_create = (
                                            query_after_create.options(
                                                joinedload(relation_attr)
                                            )
                                        )
                                except Exception:
                                    pass
                        settings_instance = query_after_create.filter(
                            model_class_.id == settings_instance.id
                        ).first()
                    else:
                        local_logger.error(
                            f"Failed to get ID for new {model_class_.__name__} instance after commit."
                        )
                        settings_instance = None

                if settings_instance:
                    # Force-load all scalar attributes and make the instance transient
                    try:
                        mapper = sa_inspect(model_class_)
                        for attr in mapper.column_attrs:
                            _ = getattr(settings_instance, attr.key)
                        # Optionally force-load requested relationships as well
                        if eager_load:
                            for relation in eager_load:
                                try:
                                    _ = getattr(settings_instance, relation)
                                except Exception:
                                    pass

                        # Make the instance transient to completely detach it from SQLAlchemy state tracking
                        make_transient(settings_instance)
                    except Exception:
                        # Fallback to expunge if make_transient fails
                        try:
                            session.expunge(settings_instance)
                        except Exception:
                            pass

                return settings_instance

        except Exception as e:
            local_logger = get_logger(
                "AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL
            )
            local_logger.error(
                f"Error loading settings for {model_class_.__name__}: {e}. Attempting to return a new transient default instance.",
                exc_info=True,
            )
            try:
                return model_class_()
            except Exception as e_create_fallback:
                local_logger.critical(
                    f"CRITICAL: Failed to create even a fallback default instance for {model_class_.__name__} "
                    f"during error handling for the original error ({e}). Fallback creation error: {e_create_fallback}",
                    exc_info=True,
                )
                raise RuntimeError(
                    f"Fatal error in settings: Could not instantiate default for {model_class_.__name__} after initial load failed. Original error: {e}"
                ) from e_create_fallback

        return settings_instance

    def update_settings(self, model_class_, updates: Dict[str, Any]):
        if model_class_.objects.first() is None:
            model_class_.objects.create()

        setting = model_class_.objects.order_by(model_class_.id.desc()).first()
        if setting:
            model_class_.objects.update(setting.id, **updates)
            for name, value in updates.items():
                self.__settings_updated(
                    model_class_.__tablename__, name, value
                )
        else:
            self.logger.error("Failed to update settings: No setting found")

    def update_layer_settings(
        self,
        model_class_,
        updates: Dict[str, Any],
        layer_id: Optional[int] = None,
    ):
        """Update settings for a specific layer.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            updates: Dictionary of field updates.
            layer_id: Layer ID to update settings for. If None, updates settings for first selected layer.
        """
        # Get layer_id if not provided
        if layer_id is None:
            layer_id = self._get_current_selected_layer_id()

        # If still no layer_id, fall back to global settings update
        if layer_id is None:
            self.logger.warning(
                f"No layer selected, falling back to global settings update for {model_class_.__name__}"
            )
            return self.update_settings(model_class_, updates)

        try:
            with session_scope() as session:
                # Find existing layer-specific settings
                setting = (
                    session.query(model_class_)
                    .filter(model_class_.layer_id == layer_id)
                    .first()
                )

                if setting is None:
                    # Create new layer-specific settings
                    self.logger.info(
                        f"Creating new layer-specific settings for {model_class_.__name__} layer {layer_id}"
                    )
                    setting = model_class_(layer_id=layer_id, **updates)
                    session.add(setting)
                else:
                    # Update existing settings
                    for key, value in updates.items():
                        if hasattr(setting, key):
                            setattr(setting, key, value)
                        else:
                            self.logger.warning(
                                f"Field {key} does not exist on {model_class_.__name__}"
                            )

                session.commit()

                # Clear cache for this layer-specific settings
                cache_key = f"{model_class_.__name__}_layer_{layer_id}"
                self.settings_mixin_shared_instance.set_cached_setting_by_key(
                    cache_key, None
                )

                # Notify of settings update
                for name, value in updates.items():
                    self.__settings_updated(
                        model_class_.__tablename__, name, value
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to update layer-specific settings for {model_class_.__name__} layer {layer_id}: {e}"
            )

    @staticmethod
    def reset_settings():
        """
        Reset all settings to their default values by deleting all
        settings from the database. When applications are
        accessed again, they will be recreated.
        """
        settings_models = [
            ApplicationSettings,
            ActiveGridSettings,
            ControlnetSettings,
            ImageToImageSettings,
            OutpaintSettings,
            DrawingPadSettings,
            MetadataSettings,
            GeneratorSettings,
            LLMGeneratorSettings,
            SpeechT5Settings,
            EspeakSettings,
            STTSettings,
            BrushSettings,
            GridSettings,
            PathSettings,
            MemorySettings,
        ]
        for cls in settings_models:
            cls.objects.delete_all()
        # Invalidate any cached settings after reset
        try:
            SettingsMixinSharedInstance()._settings_cache.clear()
        except Exception:
            pass

    @staticmethod
    def get_saved_prompt_by_id(prompt_id) -> Type[SavedPrompt]:
        return SavedPrompt.objects.filter_by_first(id=prompt_id)

    def update_saved_prompt(self, saved_prompt: SavedPrompt):
        new_saved_prompt = SavedPrompt.objects.filter_by_first(
            id=saved_prompt.id
        )
        if new_saved_prompt:
            for key in saved_prompt.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(new_saved_prompt, key, getattr(saved_prompt, key))
            new_saved_prompt.save()
        else:
            saved_prompt.save()
        self.__settings_updated()

    @staticmethod
    def create_saved_prompt(data: dict):
        new_saved_prompt = SavedPrompt(**data)
        new_saved_prompt.save()

    @staticmethod
    def load_saved_prompts() -> List[Type[SavedPrompt]]:
        return SavedPrompt.objects.all()

    @staticmethod
    def load_font_settings() -> List[Type[FontSetting]]:
        return FontSetting.objects.all()

    @staticmethod
    def get_font_setting_by_name(name) -> Type[FontSetting]:
        return FontSetting.objects.filter_by_first(name=name)

    def update_font_setting(self, font_setting: FontSetting):
        new_font_setting = FontSetting.objects.filter_by_first(
            name=font_setting.name
        )
        if new_font_setting:
            for key in font_setting.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(new_font_setting, key, getattr(font_setting, key))
            new_font_setting.save()
        else:
            font_setting.save()
        self.__settings_updated()

    @staticmethod
    def load_ai_models() -> List[Type[AIModels]]:
        models = AIModels.objects.all()
        return models

    @staticmethod
    def load_chatbots() -> List[Type[Chatbot]]:
        return Chatbot.objects.all()

    @staticmethod
    def delete_chatbot_by_name(chatbot_name):
        Chatbot.objects.delete_by(name=chatbot_name)

    @staticmethod
    def create_chatbot(chatbot_name) -> Chatbot:
        # Check for existing chatbot with this name before creating
        try:
            existing = Chatbot.objects.filter_by_first(name=chatbot_name)
            if existing:
                return existing
        except Exception:
            pass  # If query fails, proceed to create new one

        try:
            new_chatbot = Chatbot(name=chatbot_name)
            new_chatbot.save()
            return new_chatbot
        except Exception:
            # If save fails, try to get existing one again
            try:
                return (
                    Chatbot.objects.filter_by_first(name=chatbot_name)
                    or Chatbot.objects.first()
                )
            except Exception:
                # Create a minimal fallback chatbot in memory
                return Chatbot(name=chatbot_name, botname="Fallback")

    def reset_path_settings(self):
        PathSettings.objects.delete_all()
        self.set_default_values(PathSettings)

    @staticmethod
    def set_default_values(model_name_):
        with session_scope() as session:
            default_values = {}
            for column in model_name_.__table__.columns:
                if column.default is not None:
                    default_values[column.name] = column.default.arg
            session.execute(model_name_.__table__.insert(), [default_values])
            session.commit()

    @staticmethod
    def load_lora() -> List[Type[Lora]]:
        return Lora.objects.all()

    @staticmethod
    def get_lora_by_name(name):
        return Lora.objects.filter_by_first(name=name)

    @staticmethod
    def add_lora(lora: Lora):
        lora.save()

    @staticmethod
    def delete_lora(lora: Lora):
        loras = Lora.objects.filter_by(name=lora.name)
        for lora in loras:
            lora.delete()

    def update_lora(self, lora: Lora):
        new_lora = Lora.objects.filter_by_first(name=lora.name)
        if new_lora:
            for key in lora.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(new_lora, key, getattr(lora, key))
            Lora.objects.update(new_lora.id, **new_lora.__dict__)
        else:
            # Create a new SQLAlchemy model instance
            new_lora_instance = Lora(
                name=lora.name,
                path=getattr(lora, "path", ""),
                branch=getattr(lora, "branch", ""),
                version=getattr(lora, "version", ""),
                category=getattr(lora, "category", ""),
                pipeline_action=getattr(lora, "pipeline_action", ""),
                enabled=getattr(lora, "enabled", True),
                model_type=getattr(lora, "model_type", ""),
                is_default=getattr(lora, "is_default", False),
            )
            new_lora_instance.save()
        self.__settings_updated()

    def update_loras(self, loras: List[Lora]):
        for lora in loras:
            new_lora = Lora.objects.filter_by_first(name=lora.name)
            if new_lora:
                for key in lora.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(new_lora, key, getattr(lora, key))
                new_lora.save()
            else:
                # Create a new SQLAlchemy model instance
                new_lora_instance = Lora(
                    name=lora.name,
                    path=getattr(lora, "path", ""),
                    branch=getattr(lora, "branch", ""),
                    version=getattr(lora, "version", ""),
                    category=getattr(lora, "category", ""),
                    pipeline_action=getattr(lora, "pipeline_action", ""),
                    enabled=getattr(lora, "enabled", True),
                    model_type=getattr(lora, "model_type", ""),
                    is_default=getattr(lora, "is_default", False),
                )
                new_lora_instance.save()
        self.__settings_updated()

    @staticmethod
    def create_lora(lora: Lora):
        lora.save()

    @staticmethod
    def delete_lora_by_name(lora_name, version):
        loras = Lora.objects.filter_by(name=lora_name, version=version)
        for lora in loras:
            lora.delete()

    @staticmethod
    def delete_embedding(embedding: Embedding):
        Embedding.objects.delete_by(
            name=embedding.name,
            path=embedding.path,
            branch=embedding.branch,
            version=embedding.version,
            category=embedding.category,
            pipeline_action=embedding.pipeline_action,
            enabled=embedding.enabled,
            model_type=embedding.model_type,
            is_default=embedding.is_default,
        )

    def update_embeddings(self, embeddings: List[Embedding]):
        for embedding in embeddings:
            new_embedding = Embedding.objects.filter_by_first(
                name=embedding.name,
                path=embedding.path,
                branch=embedding.branch,
                version=embedding.version,
                category=embedding.category,
                pipeline_action=embedding.pipeline_action,
                enabled=embedding.enabled,
                model_type=embedding.model_type,
                is_default=embedding.is_default,
            )
            if new_embedding:
                for key in embedding.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(new_embedding, key, getattr(embedding, key))
                new_embedding.save()
            else:
                # Create a new SQLAlchemy model instance
                new_embedding_instance = Embedding(
                    name=embedding.name,
                    path=embedding.path,
                    branch=embedding.branch,
                    version=embedding.version,
                    category=embedding.category,
                    pipeline_action=embedding.pipeline_action,
                    enabled=embedding.enabled,
                    model_type=embedding.model_type,
                    is_default=embedding.is_default,
                )
                new_embedding_instance.save()
        self.__settings_updated()

    @staticmethod
    def get_embedding_by_name(name):
        return Embedding.objects.filter_by_first(name=name)

    @staticmethod
    def add_embedding(embedding: Embedding):
        embedding.save()

    @staticmethod
    def load_prompt_templates() -> List[Type[PromptTemplate]]:
        return PromptTemplate.objects.all()

    @staticmethod
    def get_prompt_template_by_name(name) -> Type[PromptTemplate]:
        return PromptTemplate.objects.filter_by_first(template_name=name)

    @staticmethod
    def load_controlnet_models() -> List[Type[ControlnetModel]]:
        return ControlnetModel.objects.all()

    @staticmethod
    def controlnet_model_by_name(name) -> Type[ControlnetModel]:
        return ControlnetModel.objects.filter_by_first(name=name)

    @staticmethod
    def load_pipelines() -> List[Type[PipelineModel]]:
        return PipelineModel.objects.all()

    @staticmethod
    def load_shortcut_keys() -> List[Type[ShortcutKeys]]:
        return ShortcutKeys.objects.all()

    def get_chatbot_by_id(self, chatbot_id) -> Chatbot:
        if not self.settings_mixin_shared_instance.chatbot:
            try:
                # Use string names for eager loading relationships
                chatbot = Chatbot.objects.get(
                    pk=chatbot_id,
                    eager_load=[
                        "target_files",
                        "target_directories",
                    ],
                )
                if chatbot is None:
                    chatbot = self.create_chatbot("Default")
                self.settings_mixin_shared_instance.chatbot = chatbot
            except Exception as e:
                self.logger.error(f"Error getting chatbot by id: {e}")
                chatbot = self.create_chatbot("Default")
                self.settings_mixin_shared_instance.chatbot = chatbot
        return self.settings_mixin_shared_instance.chatbot

    def __settings_updated(
        self, setting_name=None, column_name=None, val=None
    ):
        # Update/invalidate local settings cache first
        try:
            # Debug: log generator settings updates to trace unexpected overwrites
            try:
                if setting_name == "generator_settings":
                    self.logger.debug(
                        f"__settings_updated called for generator_settings: {column_name} = {val}"
                    )
            except Exception:
                pass
            self.settings_mixin_shared_instance.on_settings_updated(
                setting_name, column_name, val
            )
        except Exception:
            # Avoid breaking update flow due to cache issues
            pass
        if hasattr(self, "api") and self.api:
            self.api.application_settings_changed(
                setting_name=setting_name,
                column_name=column_name,
                val=val,
            )
        elif hasattr(self, "application_settings_changed"):
            self.application_settings_changed(
                setting_name=setting_name,
                column_name=column_name,
                val=val,
            )
