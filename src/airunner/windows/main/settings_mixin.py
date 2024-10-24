import logging
import datetime
import os
from typing import List, Type

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker, scoped_session

from airunner.data.models.settings_models import Chatbot, AIModels, Schedulers, Lora, PathSettings, SavedPrompt, \
    Embedding, PromptTemplate, ControlnetModel, FontSetting, PipelineModel, ShortcutKeys, \
    GeneratorSettings, WindowSettings, ApplicationSettings, ActiveGridSettings, ControlnetSettings, \
    ImageToImageSettings, OutpaintSettings, DrawingPadSettings, MetadataSettings, \
    LLMGeneratorSettings, TTSSettings, SpeechT5Settings, EspeakSettings, STTSettings, BrushSettings, GridSettings, \
    MemorySettings, Message, Conversation, Summary, ImageFilterValue, TargetFiles, WhisperSettings, Base
from airunner.enums import SignalCode
from airunner.utils.convert_binary_to_image import convert_binary_to_image


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
        self.db_path = os.path.expanduser(
            os.path.join(
                "~",
                ".local",
                "share",
                "airunner",
                "data",
                "airunner.db"
            )
        )
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
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

    @property
    def session(self):
        return self.Session()

    def close_session(self):
        self.Session.remove()


class SettingsMixin:
    @property
    def settings_mixin_shared_instance(self):
        return SettingsMixinSharedInstance()

    @property
    def logger(self):
        return self.settings_mixin_shared_instance.logger

    @property
    def session(self):
        return self.settings_mixin_shared_instance.session

    def close_session(self):
        self.settings_mixin_shared_instance.close_session()

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
        return self.session.query(Embedding).all()

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
    def image_filter_values(self):
        return self.session.query(ImageFilterValue).all()

    def get_lora_by_version(self, version):
        return self.session.query(Lora).filter_by(version=version).all()

    def get_embeddings_by_version(self, version):
        return [embedding for embedding in self.embeddings if embedding.version == version]

    @property
    def chatbot(self) -> Type[Chatbot]:
        return self.get_chatbot_by_id(
            self.llm_generator_settings.current_chatbot
        )

    @property
    def window_settings(self):
        return self.load_window_settings()

    def add_chatbot_document_to_chatbot(self, chatbot, file_path):
        document = self.session.query(TargetFiles).filter_by(chatbot_id=chatbot.id, file_path=file_path).first()
        if document is None:
            document = TargetFiles(file_path=file_path, chatbot_id=chatbot.id)
        self.session.merge(document)  # Use merge instead of add
        self.session.commit()

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
        else:
            logging.error(f"Invalid setting name: {setting_name}")

    def update_application_settings(self, column_name, val):
        self.update_setting(ApplicationSettings, column_name, val)
        self.__settings_updated()

    def update_espeak_settings(self, column_name, val):
        self.update_setting(EspeakSettings, column_name, val)
        self.__settings_updated()

    def update_tts_settings(self, column_name, val):
        self.update_setting(TTSSettings, column_name, val)
        self.__settings_updated()

    def update_speech_t5_settings(self, column_name, val):
        self.update_setting(SpeechT5Settings, column_name, val)
        self.__settings_updated()

    def update_controlnet_settings(self, column_name, val):
        self.update_setting(ControlnetSettings, column_name, val)
        self.__settings_updated()

    def update_brush_settings(self, column_name, val):
        self.update_setting(BrushSettings, column_name, val)
        self.__settings_updated()

    def update_image_to_image_settings(self, column_name, val):
        self.update_setting(ImageToImageSettings, column_name, val)
        self.__settings_updated()

    def update_outpaint_settings(self, column_name, val):
        self.update_setting(OutpaintSettings, column_name, val)
        self.__settings_updated()

    def update_drawing_pad_settings(self, column_name, val):
        self.update_setting(DrawingPadSettings, column_name, val)
        self.__settings_updated()

    def update_grid_settings(self, column_name, val):
        self.update_setting(GridSettings, column_name, val)
        self.__settings_updated()

    def update_active_grid_settings(self, column_name, val):
        self.update_setting(ActiveGridSettings, column_name, val)
        self.__settings_updated()

    def update_path_settings(self, column_name, val):
        self.update_setting(PathSettings, column_name, val)
        self.__settings_updated()

    def update_memory_settings(self, column_name, val):
        self.update_setting(MemorySettings, column_name, val)
        self.__settings_updated()

    def update_metadata_settings(self, column_name, val):
        self.update_setting(MetadataSettings, column_name, val)
        self.__settings_updated()

    def update_llm_generator_settings(self, column_name, val):
        self.update_setting(LLMGeneratorSettings, column_name, val)
        self.__settings_updated()

    def update_whisper_settings(self, column_name, val):
        self.update_setting(WhisperSettings, column_name, val)
        self.__settings_updated()

    def update_ai_models(self, models: List[AIModels]):
        for model in models:
            self.update_ai_model(model)
        self.__settings_updated()

    def update_ai_model(self, model: AIModels):
        query = self.session.query(AIModels).filter_by(
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
        if query:
            for key in model.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(query, key, getattr(model, key))
        else:
            self.session.add(model)
        self.session.commit()
        self.__settings_updated()

    def update_generator_settings(self, column_name, val):
        generator_settings = self.generator_settings
        setattr(generator_settings, column_name, val)
        self.save_generator_settings(generator_settings)

    def update_controlnet_image_settings(self, column_name, val):
        controlnet_settings = self.controlnet_settings
        setattr(controlnet_settings, column_name, val)
        self.update_controlnet_settings(column_name, val)

    def load_schedulers(self) -> list[Type[Schedulers]]:
        return self.session.query(Schedulers).all()

    def load_settings_from_db(self, model_class_):
        settings = self.session.query(model_class_).first()
        if settings is None:
            settings = self.create_new_settings(model_class_)
        return settings

    def update_setting(self, model_class_, name, value):
        setting = self.session.query(model_class_).order_by(model_class_.id.desc()).first()
        if setting:
            setattr(setting, name, value)
            self.session.commit()

    def save_generator_settings(self, generator_settings: GeneratorSettings):
        query = self.session.query(GeneratorSettings).filter_by(
            id=generator_settings.id
        ).first()
        if query:
            for key in generator_settings.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(query, key, getattr(generator_settings, key))
        else:
            self.session.add(generator_settings)
        self.session.commit()
        self.__settings_updated()

    def reset_settings(self):
        # Delete all entries from the model class
        self.session.query(ApplicationSettings).delete()
        self.session.query(ActiveGridSettings).delete()
        self.session.query(ControlnetSettings).delete()
        self.session.query(ImageToImageSettings).delete()
        self.session.query(OutpaintSettings).delete()
        self.session.query(DrawingPadSettings).delete()
        self.session.query(MetadataSettings).delete()
        self.session.query(GeneratorSettings).delete()
        self.session.query(LLMGeneratorSettings).delete()
        self.session.query(TTSSettings).delete()
        self.session.query(SpeechT5Settings).delete()
        self.session.query(EspeakSettings).delete()
        self.session.query(STTSettings).delete()
        self.session.query(BrushSettings).delete()
        self.session.query(GridSettings).delete()
        self.session.query(PathSettings).delete()
        self.session.query(MemorySettings).delete()
        # Commit the changes
        self.session.commit()

    def create_new_settings(self, model_class_):
        new_settings = model_class_()
        self.session.add(new_settings)
        self.session.commit()
        self.session.refresh(new_settings)
        return new_settings

    def get_saved_prompt_by_id(self, prompt_id) -> Type[SavedPrompt]:
        return self.session.query(SavedPrompt).filter_by(id=prompt_id).first()

    def update_saved_prompt(self, saved_prompt: SavedPrompt):
        query = self.session.query(SavedPrompt).filter_by(
            id=saved_prompt.id
        ).first()
        if query:
            for key in saved_prompt.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(query, key, getattr(saved_prompt, key))
        else:
            self.session.add(saved_prompt)
        self.session.commit()
        self.__settings_updated()

    def create_saved_prompt(self, data: dict):
        new_saved_prompt = SavedPrompt(**data)
        self.session.add(new_saved_prompt)
        self.session.commit()

    def load_saved_prompts(self) -> List[Type[SavedPrompt]]:
        return self.session.query(SavedPrompt).all()

    def load_font_settings(self) -> List[Type[FontSetting]]:
        return self.session.query(FontSetting).all()

    def get_font_setting_by_name(self, name) -> Type[FontSetting]:
        return self.session.query(FontSetting).filter_by(name=name).first()

    def update_font_setting(self, font_setting: Type[FontSetting]):
        query = self.session.query(FontSetting).filter_by(
            name=font_setting.name
        ).first()
        if query:
            for key in font_setting.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(query, key, getattr(font_setting, key))
        else:
            self.session.add(font_setting)
        self.session.commit()
        self.__settings_updated()

    def load_ai_models(self) -> List[Type[AIModels]]:
        return self.session.query(AIModels).all()

    def load_chatbots(self) -> List[Type[Chatbot]]:
        settings = self.session.query(Chatbot).all()
        return settings

    def delete_chatbot_by_name(self, chatbot_name):
        self.session.query(Chatbot).filter_by(name=chatbot_name).delete()
        self.session.commit()

    def create_chatbot(self, chatbot_name):
        new_chatbot = Chatbot(name=chatbot_name)
        self.session.add(new_chatbot)
        self.session.commit()

    def reset_path_settings(self):
        self.session.query(PathSettings).delete()
        self.set_default_values(PathSettings)
        self.session.commit()

    def set_default_values(self, model_name_):
        default_values = {}
        for column in model_name_.__table__.columns:
            if column.default is not None:
                default_values[column.name] = column.default.arg
        self.session.execute(
            model_name_.__table__.insert(),
            [default_values]
        )
        self.session.commit()

    def load_lora(self) -> List[Type[Lora]]:
        return self.session.query(Lora).all()

    def get_lora_by_name(self, name):
        return self.session.query(Lora).filter_by(name=name).first()

    def add_lora(self, lora: Lora):
        self.session.add(lora)
        self.session.commit()

    def delete_lora(self, lora: Lora):
        self.session.query(Lora).filter_by(name=lora.name).delete()
        self.session.commit()

    def update_lora(self, lora: Lora):
        query = self.session.query(Lora).filter_by(name=lora.name).first()
        if query:
            for key in lora.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(query, key, getattr(lora, key))
        else:
            self.session.add(lora)
        self.session.commit()
        self.__settings_updated()

    def update_loras(self, loras: List[Lora]):
        for lora in loras:
            query = self.session.query(Lora).filter_by(name=lora.name).first()
            if query:
                for key in lora.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(lora, key))
            else:
                self.session.add(lora)
        self.session.commit()
        self.__settings_updated()

    def create_lora(self, lora: Lora):
        self.session.add(lora)
        self.session.commit()

    def delete_lora_by_name(self, lora_name, version):
        self.session.query(Lora).filter_by(name=lora_name, version=version).delete()
        self.session.commit()

    def delete_embedding(self, embedding: Embedding):
        self.session.query(Embedding).filter_by(
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
        self.session.commit()

    def update_embeddings(self, embeddings: List[Embedding]):
        for embedding in embeddings:
            query = self.session.query(Embedding).filter_by(
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
            if query:
                for key in embedding.__dict__.keys():
                    if key != "_sa_instance_state":
                        setattr(query, key, getattr(embedding, key))
            else:
                self.session.add(embedding)
        self.session.commit()
        self.__settings_updated()

    def get_embedding_by_name(self, name):
        return self.session.query(Embedding).filter_by(name=name).first()

    def add_embedding(self, embedding: Embedding):
        self.session.add(embedding)
        self.session.commit()

    def load_prompt_templates(self) -> List[Type[PromptTemplate]]:
        return self.session.query(PromptTemplate).all()

    def get_prompt_template_by_name(self, name) -> Type[PromptTemplate]:
        return self.session.query(PromptTemplate).filter_by(template_name=name).first()

    def load_controlnet_models(self) -> List[Type[ControlnetModel]]:
        return self.session.query(ControlnetModel).all()

    def controlnet_model_by_name(self, name) -> Type[ControlnetModel]:
        return self.session.query(ControlnetModel).filter_by(name=name).first()

    def load_pipelines(self) -> List[Type[PipelineModel]]:
        return self.session.query(PipelineModel).all()

    def load_shortcut_keys(self) -> List[Type[ShortcutKeys]]:
        return self.session.query(ShortcutKeys).all()

    def load_window_settings(self) -> Type[WindowSettings]:
        return self.session.query(WindowSettings).first()

    def save_window_settings(self, column_name, val):
        window_settings = self.window_settings
        setattr(window_settings, column_name, val)
        query = self.session.query(WindowSettings).first()
        if query:
            for key in window_settings.__dict__.keys():
                if key != "_sa_instance_state":
                    setattr(query, key, getattr(window_settings, key))
        else:
            self.session.add(window_settings)
        self.session.commit()

    def save_object(self, database_object):
        self.session.add(database_object)
        self.session.commit()

    def load_history_from_db(self, conversation_id):
        messages = self.session.query(Message).filter_by(
            conversation_id=conversation_id
        ).order_by(Message.timestamp).all()
        results = [
            {
                "role": message.role,
                "content": message.content,
                "name": message.name,
                "is_bot": message.is_bot,
                "timestamp": message.timestamp,
                "conversation_id": message.conversation_id
            } for message in messages
        ]
        return results

    def save_message(self, content, role, name, is_bot, conversation_id) -> Message:
        timestamp = datetime.datetime.now()  # Ensure timestamp is a datetime object
        llm_generator_settings = self.session.query(LLMGeneratorSettings).first()
        message = Message(
            role=role,
            content=content,
            name=name,
            is_bot=is_bot,
            timestamp=timestamp,
            conversation_id=conversation_id,
            chatbot_id=llm_generator_settings.current_chatbot
        )
        self.session.add(message)
        self.session.commit()
        return message

    def get_chatbot_by_id(self, chatbot_id) -> Type[Chatbot]:
        chatbot = self.session.query(Chatbot).filter_by(id=chatbot_id).options(joinedload(Chatbot.target_files)).first()
        if chatbot is None:
            chatbot = self.session.query(Chatbot).options(joinedload(Chatbot.target_files)).first()
        return chatbot

    def create_conversation(self):
        conversation = Conversation(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            title=""
        )
        self.session.add(conversation)
        self.session.commit()
        return conversation

    def update_conversation_title(self, conversation_id, title):
        conversation = self.session.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.title = title
            self.session.commit()

    def add_summary(self, content, conversation_id):
        timestamp = datetime.datetime.now()  # Ensure timestamp is a datetime object
        summary = Summary(
            content=content,
            timestamp=timestamp,
            conversation_id=conversation_id
        )
        self.session.add(summary)
        self.session.commit()

    def get_all_conversations(self):
        conversations = self.session.query(Conversation).all()
        return conversations

    def delete_conversation(self, conversation_id):
        self.session.query(Message).filter_by(conversation_id=conversation_id).delete()
        self.session.query(Summary).filter_by(conversation_id=conversation_id).delete()
        self.session.query(Conversation).filter_by(id=conversation_id).delete()
        self.session.commit()

    def get_most_recent_conversation(self):
        conversation = self.session.query(Conversation).order_by(Conversation.timestamp.desc()).first()
        return conversation

    def __settings_updated(self):
        self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL)
