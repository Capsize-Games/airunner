import os
import logging
from typing import List, Type, Optional, Dict, Any

from sqlalchemy.orm import joinedload

from airunner.data.models import (
    Chatbot, 
    AIModels, 
    Schedulers, 
    Lora, 
    PathSettings, 
    SavedPrompt,
    Embedding, 
    PromptTemplate, 
    ControlnetModel, 
    FontSetting, 
    PipelineModel, 
    ShortcutKeys,
    GeneratorSettings, 
    ApplicationSettings, 
    ActiveGridSettings, 
    ControlnetSettings,
    ImageToImageSettings, 
    OutpaintSettings, 
    DrawingPadSettings, 
    MetadataSettings,
    LLMGeneratorSettings,
    TTSSettings, 
    SpeechT5Settings, 
    EspeakSettings, 
    STTSettings, 
    BrushSettings, 
    GridSettings,
    MemorySettings, 
    ImageFilterValue, 
    TargetFiles, 
    WhisperSettings, 
    User
)
from airunner.enums import SignalCode
from airunner.utils.image import convert_binary_to_image
from airunner.data.session_manager import session_scope
from airunner.utils.settings import get_qsettings
from airunner.utils.get_logger import get_logger


class SettingsMixinSharedInstance:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SettingsMixinSharedInstance, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = get_logger("AI Runner", logging.DEBUG)

        self._initialized = True
        self.chatbot: Optional[Chatbot] = None


class SettingsMixin:
    _chatbot: Optional[Chatbot] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    @property
    def session_manager(self):
        return self.settings_mixin_shared_instance.session_manager

    @property
    def settings_mixin_shared_instance(self):
        return SettingsMixinSharedInstance()

    @property
    def logger(self):
        return self.settings_mixin_shared_instance.logger

    @property
    def stt_settings(self) -> STTSettings:
        return self.load_settings_from_db(STTSettings)

    @property
    def application_settings(self) -> ApplicationSettings:
        return self.load_settings_from_db(ApplicationSettings)

    @property
    def whisper_settings(self) -> WhisperSettings:
        return self.load_settings_from_db(WhisperSettings)
    
    @property
    def window_settings(self) -> Dict[str, Any]:
        settings = get_qsettings()
        settings.beginGroup("window_settings")
        window_settings = {
            "is_maximized": settings.value("is_maximized", False, type=bool),
            "is_fullscreen": settings.value("is_fullscreen", False, type=bool),
            "width": settings.value("width", 800, type=int),
            "height": settings.value("height", 600, type=int),
            "x_pos": settings.value("x_pos", 0, type=int),
            "y_pos": settings.value("y_pos", 0, type=int),
            "mode_tab_widget_index": settings.value("mode_tab_widget_index", 0, type=int),
        }
        settings.endGroup()
        return window_settings
        

    @property
    def llm_generator_settings(self) -> LLMGeneratorSettings:
        settings = self.load_settings_from_db(LLMGeneratorSettings)
        if settings.current_chatbot == 0:
            chatbots = self.chatbots
            if len(chatbots) > 0:
                settings.current_chatbot = self.chatbots[0].id
                self.update_llm_generator_settings(
                    "current_chatbot", 
                    settings.current_chatbot
                )
        return settings

    @property
    def generator_settings(self) -> GeneratorSettings:
        return self.load_settings_from_db(GeneratorSettings)

    @property
    def controlnet_settings(self) -> ControlnetSettings:
        return self.load_settings_from_db(ControlnetSettings)

    @property
    def image_to_image_settings(self) -> ImageToImageSettings:
        return self.load_settings_from_db(ImageToImageSettings)

    @property
    def outpaint_settings(self) -> OutpaintSettings:
        return self.load_settings_from_db(OutpaintSettings)

    @property
    def drawing_pad_settings(self) -> DrawingPadSettings:
        return self.load_settings_from_db(DrawingPadSettings)

    @property
    def brush_settings(self) -> BrushSettings:
        return self.load_settings_from_db(BrushSettings)

    @property
    def grid_settings(self) -> GridSettings:
        return self.load_settings_from_db(GridSettings)

    @property
    def active_grid_settings(self) -> ActiveGridSettings:
        return self.load_settings_from_db(ActiveGridSettings)

    @property
    def path_settings(self) -> PathSettings:
        return self.load_settings_from_db(PathSettings)

    @property
    def memory_settings(self) -> MemorySettings:
        return self.load_settings_from_db(MemorySettings)

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
    def lora(self) -> List[Type[Lora]]:
        return self.load_lora()

    @property
    def shortcut_keys(self) -> List[Type[ShortcutKeys]]:
        return self.load_shortcut_keys()

    @property
    def speech_t5_settings(self) -> SpeechT5Settings:
        return self.load_settings_from_db(SpeechT5Settings)

    @property
    def tts_settings(self) -> TTSSettings:
        return self.load_settings_from_db(TTSSettings)

    @property
    def espeak_settings(self) -> EspeakSettings:
        return self.load_settings_from_db(EspeakSettings)

    @property
    def metadata_settings(self) -> MetadataSettings:
        return self.load_settings_from_db(MetadataSettings)

    @property
    def embeddings(self) -> List[Type[Embedding]]:
        return Embedding.objects.all()

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
        base_64_image = self.image_to_image_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_image(self):
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
        base_64_image = self.outpaint_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def image_filter_values(self) -> Optional[List[ImageFilterValue]]:
        return ImageFilterValue.objects.all()

    @staticmethod
    def get_lora_by_version(version) -> Optional[List[Lora]]:
        return Lora.objects.filter_by(version=version)

    def get_embeddings_by_version(self, version) -> Optional[List[Type[Embedding]]]:
        return [
            embedding for embedding in self.embeddings if embedding.version == version
        ]

    @property
    def chatbot(self) -> Optional[Chatbot]:
        current_chatbot_id = self.llm_generator_settings.current_chatbot
        
        chatbot = Chatbot.objects.options(
            joinedload(Chatbot.target_files),
        ).get(current_chatbot_id)
        
        if chatbot is None:
            chatbot = Chatbot.objects.options(
                joinedload(Chatbot.target_files),
            ).first()
        
        if chatbot is None:
            chatbot = Chatbot()
            chatbot.save()
            chatbot = Chatbot.objects.options(
                joinedload(Chatbot.target_files),
            ).first()

        return chatbot

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

    def update_application_settings(self, column_name, val):
        self.update_setting(ApplicationSettings, column_name, val)

    def update_espeak_settings(self, column_name, val):
        self.update_setting(EspeakSettings, column_name, val)

    def update_tts_settings(self, column_name, val):
        self.update_setting(TTSSettings, column_name, val)

    def update_speech_t5_settings(self, column_name, val):
        self.update_setting(SpeechT5Settings, column_name, val)

    def update_controlnet_settings(self, column_name, val):
        self.update_setting(ControlnetSettings, column_name, val)

    def update_brush_settings(self, column_name, val):
        self.update_setting(BrushSettings, column_name, val)

    def update_image_to_image_settings(self, column_name, val):
        self.update_setting(ImageToImageSettings, column_name, val)

    def update_outpaint_settings(self, column_name, val):
        self.update_setting(OutpaintSettings, column_name, val)

    def update_drawing_pad_settings(self, column_name, val):
        self.update_setting(DrawingPadSettings, column_name, val)

    def update_grid_settings(self, column_name, val):
        self.update_setting(GridSettings, column_name, val)

    def update_active_grid_settings(self, column_name, val):
        self.update_setting(ActiveGridSettings, column_name, val)

    def update_path_settings(self, column_name, val):
        self.update_setting(PathSettings, column_name, val)

    def update_memory_settings(self, column_name, val):
        self.update_setting(MemorySettings, column_name, val)

    def update_metadata_settings(self, column_name, val):
        self.update_setting(MetadataSettings, column_name, val)

    def update_llm_generator_settings(self, column_name: str, val):
        self.update_setting(LLMGeneratorSettings, column_name, val)

    def update_whisper_settings(self, column_name, val):
        self.update_setting(WhisperSettings, column_name, val)

    def update_ai_models(self, models: List[AIModels]):
        for model in models:
            self.update_ai_model(model)
        self.__settings_updated()

    def update_ai_model(self, model: AIModels):
        ai_model = AIModels.objects.filter_by_first(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action,
            enabled=model.enabled,
            model_type=model.model_type,
            is_default=model.is_default
        )
        if ai_model:
            for key in model.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(ai_model, key, getattr(model, key))
            ai_model.save()
        else:
            model.save()
        self.__settings_updated()

    def update_generator_settings(self, column_name, val):
        generator_settings = self.generator_settings
        setattr(generator_settings, column_name, val)
        generator_settings.save()
        self.__settings_updated(
            setting_name=GeneratorSettings.__tablename__,
            column_name=column_name,
            val=val
        )

    def update_controlnet_image_settings(self, column_name, val):
        controlnet_settings = self.controlnet_settings
        setattr(controlnet_settings, column_name, val)
        self.update_controlnet_settings(column_name, val)

    @staticmethod
    def load_schedulers() -> List[Schedulers]:
        return Schedulers.objects.all()

    @staticmethod
    def load_settings_from_db(model_class_):
        settings = model_class_.objects.first()
        if settings is None:
            settings = model_class_()
            settings.save()
        return model_class_.objects.first()

    def update_setting(self, model_class_, name, value):
        setting = model_class_.objects.order_by(model_class_.id.desc()).first()
        if setting:
            model_class_.objects.update(
                setting.id, **{
                    name: value
                }
            )
            self.__settings_updated(model_class_.__tablename__, name, value)
        else:
            self.logger.error("Failed to update settings: No setting found")

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
            TTSSettings,
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
        return FontSetting.objects.filter_by_first(
            name=name
        )

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
        return AIModels.objects.all()

    @staticmethod
    def load_chatbots() -> List[Type[Chatbot]]:
        return Chatbot.objects.all()

    @staticmethod
    def delete_chatbot_by_name(chatbot_name):
        Chatbot.objects.delete_by(name=chatbot_name)

    @staticmethod
    def create_chatbot(chatbot_name) -> Chatbot:
        new_chatbot = Chatbot(name=chatbot_name)
        new_chatbot.save()
        return new_chatbot

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
            session.execute(
                model_name_.__table__.insert(),
                [default_values]
            )
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
            new_lora.save()
        else:
            lora.save()
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
                lora.save()
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
            is_default=embedding.is_default
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
                is_default=embedding.is_default
            )
            if new_embedding:
                for key in embedding.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(new_embedding, key, getattr(embedding, key))
                new_embedding.save()
            else:
                embedding.save()
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
            chatbot = Chatbot.objects.options(
                joinedload(Chatbot.target_files),
                joinedload(Chatbot.target_directories)
            ).get(chatbot_id)
            if chatbot is None:
                chatbot = self.create_chatbot("Default")
            self.settings_mixin_shared_instance.chatbot = chatbot
        return self.settings_mixin_shared_instance.chatbot

    def __settings_updated(self, setting_name=None, column_name=None, val=None):
        self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, {
            "setting_name": setting_name,
            "column_name": column_name,
            "value": val
        })
