import logging
import datetime
from typing import List, Type, Optional

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
    WindowSettings, 
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
    Conversation, 
    Summary, 
    ImageFilterValue, 
    TargetFiles, 
    WhisperSettings, 
    User
)
from airunner.enums import SignalCode
from airunner.utils.image.convert_binary_to_image import convert_binary_to_image
from airunner.enums import LLMChatRole
from airunner.data.session_manager import session_scope


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
        self.conversation_id = None

        # Configure the logger
        self.logger = logging.getLogger("AI Runner")
        self.logger.setLevel(logging.DEBUG)

        # Remove all existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s'))
        self.logger.addHandler(handler)

        # Disable propagation to the root logger
        self.logger.propagate = False

        self._initialized = True
        self.chatbot: Optional[Chatbot] = None


class SettingsMixin:
    _chatbot: Optional[Chatbot] = None

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
    def window_settings(self) -> WindowSettings:
        return self.load_settings_from_db(WindowSettings)

    @property
    def llm_generator_settings(self) -> LLMGeneratorSettings:
        settings = self.load_settings_from_db(LLMGeneratorSettings)
        if settings.current_chatbot == 0:
            chatbots = self.chatbots
            if len(chatbots) > 0:
                settings.current_chatbot = self.chatbots[0].id
                self.update_settings_by_name("llm_generator_settings", "current_chatbot", settings.current_chatbot)
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

    def get_lora_by_version(self, version) -> Optional[List[Lora]]:
        return Lora.objects.filter_by(version=version).all()

    def get_embeddings_by_version(self, version) -> Optional[List[Embedding]]:
        return [
            embedding for embedding in self.embeddings 
                if embedding.version == version
        ]

    @property
    def chatbot(self) -> Optional[Chatbot]:
        chatbot = self._chatbot
        current_chatbot_id = self.llm_generator_settings.current_chatbot
        
        if (
            not chatbot 
            and current_chatbot_id
        ) or (
            chatbot
            and current_chatbot_id 
            and chatbot.id != current_chatbot_id
        ):
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
        
        self._chatbot = chatbot

        return self._chatbot

    @property
    def user(self) -> Type[User]:
        user = User.objects.first()
        if user is None:
            user = User()
            user.username = "User"
            user.save()
            user = User.objects.first()
        return user

    def add_chatbot_document_to_chatbot(self, chatbot, file_path):
        document = TargetFiles.objects.filter_by(
            chatbot_id=chatbot.id, file_path=file_path
        ).first()
        if document is None:
            document = TargetFiles(file_path=file_path, chatbot_id=chatbot.id)
        TargetFiles.objects.merge(document)

    def update_settings_by_name(self, setting_name, column_name, val):
        if setting_name == "application_settings":
            self.update_application_settings(column_name, val)
        elif setting_name == "generator_settings":
            self.update_generator_settings(column_name, val)
        elif setting_name == "controlnet_image_settings":
            self.update_controlnet_image_settings(column_name, val)
        elif setting_name == "brush_settings":
            self.update_brush_settings(column_name, val)
        elif setting_name == "controlnet_settings":
            self.update_controlnet_settings(column_name, val)
        elif setting_name == "image_to_image_settings":
            self.update_image_to_image_settings(column_name, val)
        elif setting_name == "outpaint_settings":
            self.update_outpaint_settings(column_name, val)
        elif setting_name == "drawing_pad_settings":
            self.update_drawing_pad_settings(column_name, val)
        elif setting_name == "grid_settings":
            self.update_grid_settings(column_name, val)
        elif setting_name == "active_grid_settings":
            self.update_active_grid_settings(column_name, val)
        elif setting_name == "path_settings":
            self.update_path_settings(column_name, val)
        elif setting_name == "memory_settings":
            self.update_memory_settings(column_name, val)
        elif setting_name == "llm_generator_settings":
            self.update_llm_generator_settings(column_name, val)
        elif setting_name == "whisper_settings":
            self.update_whisper_settings(column_name, val)
        elif setting_name == "speech_t5_settings":
            self.update_speech_t5_settings(column_name, val)
        else:
            logging.error(f"Invalid setting name: {setting_name}")

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
        ai_model = AIModels.objects.filter_by(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action,
            enabled=model.enabled,
            model_type=model.model_type,
            is_default=model.is_default
        ).first()
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

    def update_controlnet_image_settings(self, column_name, val):
        controlnet_settings = self.controlnet_settings
        setattr(controlnet_settings, column_name, val)
        self.update_controlnet_settings(column_name, val)

    def load_schedulers(self) -> List[Schedulers]:
        return Schedulers.objects.all()

    def load_settings_from_db(self, model_class_):
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

    def reset_settings(self):
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

    def get_saved_prompt_by_id(self, prompt_id) -> Type[SavedPrompt]:
        return SavedPrompt.objects.filter_by(id=prompt_id).first()

    def update_saved_prompt(self, saved_prompt: SavedPrompt):
        new_saved_prompt = SavedPrompt.objects.filter_by(
            id=saved_prompt.id
        ).first()
        if new_saved_prompt:
            for key in saved_prompt.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(new_saved_prompt, key, getattr(saved_prompt, key))
            new_saved_prompt.save()
        else:
            saved_prompt.save()
        self.__settings_updated()

    def create_saved_prompt(self, data: dict):
        new_saved_prompt = SavedPrompt(**data)
        new_saved_prompt.save()

    def load_saved_prompts(self) -> List[Type[SavedPrompt]]:
        return SavedPrompt.objects.all()

    def load_font_settings(self) -> List[Type[FontSetting]]:
        return FontSetting.objects.all()

    def get_font_setting_by_name(self, name) -> Type[FontSetting]:
        return FontSetting.objects.filter_by(
            name=name
        ).first()

    def update_font_setting(self, font_setting: Type[FontSetting]):
        new_font_setting = FontSetting.objects.filter_by(
            name=font_setting.name
        ).first()
        if new_font_setting:
            for key in font_setting.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(new_font_setting, key, getattr(font_setting, key))
            new_font_setting.save()
        else:
            font_setting.save()
        self.__settings_updated()

    def load_ai_models(self) -> List[Type[AIModels]]:
        return AIModels.objects.all()

    def load_chatbots(self) -> List[Type[Chatbot]]:
        return Chatbot.objects.all()

    def delete_chatbot_by_name(self, chatbot_name):
        Chatbot.objects.filter_by(name=chatbot_name).delete()

    def create_chatbot(self, chatbot_name):
        new_chatbot = Chatbot(name=chatbot_name)
        new_chatbot.save()

    def reset_path_settings(self):
        PathSettings.objects.delete_all()
        self.set_default_values(PathSettings)

    def set_default_values(self, model_name_):
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

    def load_lora(self) -> List[Type[Lora]]:
        return Lora.objects.all()

    def get_lora_by_name(self, name):
        return Lora.objects.filter_by(name=name).first()

    def add_lora(self, lora: Lora):
        lora.save()

    def delete_lora(self, lora: Lora):
        loras = Lora.objects.filter_by(name=lora.name)
        for lora in loras:
            lora.delete()

    def update_lora(self, lora: Lora):
        new_lora = Lora.objects.filter_by(name=lora.name).first()
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
            new_lora = Lora.objects.filter_by(name=lora.name).first()
            if new_lora:
                for key in lora.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(new_lora, key, getattr(lora, key))
                new_lora.save()
            else:
                lora.save()
        self.__settings_updated()

    def create_lora(self, lora: Lora):
        lora.save()

    def delete_lora_by_name(self, lora_name, version):
        loras = Lora.objects.filter_by(name=lora_name, version=version)
        for lora in loras:
            lora.delete()

    def delete_embedding(self, embedding: Embedding):
        Embedding.objects.filter_by(
            name=embedding.name,
            path=embedding.path,
            branch=embedding.branch,
            version=embedding.version,
            category=embedding.category,
            pipeline_action=embedding.pipeline_action,
            enabled=embedding.enabled,
            model_type=embedding.model_type,
            is_default=embedding.is_default
        ).delete()

    def update_embeddings(self, embeddings: List[Embedding]):
        for embedding in embeddings:
            new_embedding = Embedding.objects.filter_by(
                name=embedding.name,
                path=embedding.path,
                branch=embedding.branch,
                version=embedding.version,
                category=embedding.category,
                pipeline_action=embedding.pipeline_action,
                enabled=embedding.enabled,
                model_type=embedding.model_type,
                is_default=embedding.is_default
            ).first()
            if new_embedding:
                for key in embedding.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(new_embedding, key, getattr(embedding, key))
                new_embedding.save()
            else:
                embedding.save()
        self.__settings_updated()

    def get_embedding_by_name(self, name):
        return Embedding.objects.filter_by(name=name).first()

    def add_embedding(self, embedding: Embedding):
        embedding.save()

    def load_prompt_templates(self) -> List[Type[PromptTemplate]]:
        return PromptTemplate.objects.all()

    def get_prompt_template_by_name(self, name) -> Type[PromptTemplate]:
        return PromptTemplate.objects.filter_by(template_name=name).first()

    def load_controlnet_models(self) -> List[Type[ControlnetModel]]:
        return ControlnetModel.objects.all()

    def controlnet_model_by_name(self, name) -> Type[ControlnetModel]:
        return ControlnetModel.objects.filter_by(name=name).first()

    def load_pipelines(self) -> List[Type[PipelineModel]]:
        return PipelineModel.objects.all()

    def load_shortcut_keys(self) -> List[Type[ShortcutKeys]]:
        return ShortcutKeys.objects.all()

    def save_window_settings(self, column_name, val):
        window_settings = self.window_settings
        setattr(window_settings, column_name, val)
        new_window_settings = WindowSettings.objects.first()
        if new_window_settings:
            for key in window_settings.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(new_window_settings, key, getattr(window_settings, key))
            new_window_settings.save()
        else:
            window_settings.save()

    def save_object(self, database_object):
        database_object.save()

    def load_history_from_db(self, conversation_id):
        conversation = Conversation.objects.filter_by(
            id=conversation_id
        ).first()
        messages = conversation.value
        return [
            {
                "id": id,
                "role": LLMChatRole.HUMAN if message["role"] == "user"  else LLMChatRole.ASSISTANT,
                "content": message["blocks"][0]["text"],
                "name": self.username if message["role"] == "user" else self.chatbot.name,
                "is_bot": message["role"] == "bot",
                "timestamp": message["timestamp"],
                "conversation_id": conversation_id

            } for id, message in enumerate(messages)
        ]

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

    def create_conversation(self, chat_store_key: str):
        # get prev conversation by key != chat_store_key
        # order by id desc
        # get first
        previous_conversation = Conversation.objects.options(
            joinedload(Conversation.summaries)
        ).filter(
            Conversation.key != chat_store_key
        ).order_by(
            Conversation.id.desc()
        ).first()
        # find conversation which has no title, bot_mood or messages
        conversation = Conversation.objects.options(
            joinedload(Conversation.summaries)
        ).filter_by(
            key=chat_store_key
        ).first()
        if (
            previous_conversation 
            and previous_conversation.bot_mood 
            and conversation 
            and conversation.bot_mood is None
        ):
            conversation.bot_mood = previous_conversation.bot_mood
            conversation.save()
        if conversation:
            return conversation
        conversation = Conversation(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            title="",
            key=chat_store_key,
            value=None,
            chatbot_id=self.chatbot.id,
            user_id=self.user.id,
            chatbot_name=self.chatbot.name,
            user_name=self.user.username,
            bot_mood=previous_conversation.bot_mood if previous_conversation else None
        )
        conversation.save()
        return Conversation.objects.options(
            joinedload(Conversation.summaries)
        ).filter_by(
            key=chat_store_key
        ).first()

    def update_conversation_title(self, conversation_id, title):
        conversation = Conversation.objects.filter_by(
            id=conversation_id
        ).first()
        if conversation:
            conversation.title = title
            conversation.save()

    def add_summary(self, content, conversation_id):
        timestamp = datetime.datetime.now()  # Ensure timestamp is a datetime object
        summary = Summary(
            content=content,
            timestamp=timestamp,
            conversation_id=conversation_id
        )
        summary.save()
    
    def get_all_conversations(self) -> Optional[List[Conversation]]:
        return Conversation.objects.all()

    def delete_conversation(self, conversation_id):
        Summary.objects.delete(conversation_id=conversation_id)
        Conversation.objects.delete(id=conversation_id)

    def get_most_recent_conversation(self) -> Optional[Conversation]:
        return Conversation.objects.order_by(
            Conversation.timestamp.desc()
        ).first()

    def __settings_updated(self, setting_name=None, column_name=None, val=None):
        data = None
        if setting_name and column_name and val:
            data = {
                "setting_name": setting_name,
                "column_name": column_name,
                "value": val
            }
        self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, data)
