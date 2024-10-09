import logging
from typing import List

from sqlalchemy.orm import joinedload

from airunner.data.models.settings_db_handler import SettingsDBHandler
from airunner.data.models.settings_models import ApplicationSettings, LLMGeneratorSettings, GeneratorSettings, \
    ControlnetSettings, BrushSettings, DrawingPadSettings, GridSettings, ActiveGridSettings, \
    ImageToImageSettings, OutpaintSettings, PathSettings, MemorySettings, Chatbot, \
    AIModels, Schedulers, Lora, ShortcutKeys, SavedPrompt, SpeechT5Settings, TTSSettings, EspeakSettings, \
    MetadataSettings, Embedding, STTSettings, PromptTemplate, ControlnetModel, FontSetting, PipelineModel, TargetFiles, \
    ImageFilterValue
from airunner.enums import SignalCode
from airunner.utils.convert_base64_to_image import convert_base64_to_image


class SettingsMixin:
    def __init__(self):
        logging.debug("Initializing SettingsMixin instance")
        self.db_handler = SettingsDBHandler()

    @property
    def stt_settings(self) -> STTSettings:
        return self.db_handler.load_settings_from_db(STTSettings)

    @property
    def application_settings(self) -> ApplicationSettings:
        return self.db_handler.load_settings_from_db(ApplicationSettings)

    @property
    def llm_generator_settings(self) -> LLMGeneratorSettings:
        return self.db_handler.load_settings_from_db(LLMGeneratorSettings)

    @property
    def generator_settings(self) -> GeneratorSettings:
        return self.db_handler.load_settings_from_db(GeneratorSettings)

    @property
    def controlnet_settings(self) -> ControlnetSettings:
        return self.db_handler.load_settings_from_db(ControlnetSettings)

    @property
    def image_to_image_settings(self) -> ImageToImageSettings:
        return self.db_handler.load_settings_from_db(ImageToImageSettings)

    @property
    def outpaint_settings(self) -> OutpaintSettings:
        return self.db_handler.load_settings_from_db(OutpaintSettings)

    @property
    def drawing_pad_settings(self) -> DrawingPadSettings:
        return self.db_handler.load_settings_from_db(DrawingPadSettings)

    @property
    def brush_settings(self) -> BrushSettings:
        return self.db_handler.load_settings_from_db(BrushSettings)

    @property
    def grid_settings(self) -> GridSettings:
        return self.db_handler.load_settings_from_db(GridSettings)

    @property
    def active_grid_settings(self) -> ActiveGridSettings:
        return self.db_handler.load_settings_from_db(ActiveGridSettings)

    @property
    def path_settings(self) -> PathSettings:
        return self.db_handler.load_settings_from_db(PathSettings)

    @property
    def memory_settings(self) -> MemorySettings:
        return self.db_handler.load_settings_from_db(MemorySettings)

    @property
    def chatbots(self) -> List[Chatbot]:
        return self.db_handler.load_chatbots()

    @property
    def ai_models(self) -> List[AIModels]:
        return self.db_handler.load_ai_models()

    @property
    def schedulers(self) -> List[Schedulers]:
        return self.db_handler.load_schedulers()

    @property
    def lora(self) -> List[Lora]:
        return self.db_handler.load_lora()

    @property
    def shortcut_keys(self) -> List[ShortcutKeys]:
        return self.db_handler.load_shortcut_keys()

    @property
    def speech_t5_settings(self) -> SpeechT5Settings:
        return self.db_handler.load_settings_from_db(SpeechT5Settings)

    @property
    def tts_settings(self) -> TTSSettings:
        return self.db_handler.load_settings_from_db(TTSSettings)

    @property
    def espeak_settings(self) -> EspeakSettings:
        return self.db_handler.load_settings_from_db(EspeakSettings)

    @property
    def metadata_settings(self) -> MetadataSettings:
        return self.db_handler.load_settings_from_db(MetadataSettings)

    @property
    def embeddings(self) -> List[Embedding]:
        return self.db_handler.load_embeddings()

    @property
    def prompt_templates(self) -> List[PromptTemplate]:
        return self.db_handler.load_prompt_templates()

    @property
    def controlnet_models(self):
        return self.db_handler.load_controlnet_models()

    @property
    def saved_prompts(self) -> List[SavedPrompt]:
        return self.db_handler.load_saved_prompts()

    @property
    def font_settings(self) -> List[FontSetting]:
        return self.db_handler.load_font_settings()

    @property
    def pipelines(self) -> List[PipelineModel]:
        return self.db_handler.load_pipelines()

    @property
    def drawing_pad_image(self):
        base_64_image = self.drawing_pad_settings.image
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def drawing_pad_mask(self):
        base_64_image = self.drawing_pad_settings.mask
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def img2img_image(self):
        base_64_image = self.image_to_image_settings.image
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_image(self):
        base_64_image = self.controlnet_settings.image
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_generated_image(self):
        base_64_image = self.controlnet_settings.imported_image_base64
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def outpaint_mask(self):
        base_64_image = self.drawing_pad_settings.mask
        image = convert_base64_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def image_filter_values(self):
        session = self.db_handler.get_db_session()
        try:
            return session.query(ImageFilterValue).all()
        finally:
            session.close()

    #######################################
    ### LORA ###
    #######################################

    def get_lora_by_version(self, version):
        session = self.db_handler.get_db_session()
        try:
            return session.query(Lora).filter_by(version=version).all()
        finally:
            session.close()

    def delete_lora_by_name(self, name, version):
        self.db_handler.delete_lora_by_name(name, version)

    def create_lora(self, lora: Lora):
        self.db_handler.create_lora(lora)

    def update_lora(self, lora: Lora):
        self.db_handler.update_lora(lora)
        self.__settings_updated()

    def update_loras(self, loras: List[Lora]):
        self.db_handler.update_loras(loras)
        self.__settings_updated()

    #######################################
    ### EMBEDDINGS ###
    #######################################
    def get_embeddings_by_version(self, version):
        return [embedding for embedding in self.embeddings if embedding.version == version]

    def delete_embedding(self, embedding: Embedding):
        self.db_handler.delete_embedding(embedding)

    def update_embeddings(self, embeddings: List[Embedding]):
        self.db_handler.update_embeddings(embeddings)
        self.__settings_updated()

    #######################################
    ### CHATBOT ###
    #######################################
    @property
    def chatbot(self) -> Chatbot:
        return self.get_chatbot_by_id(
            self.llm_generator_settings.current_chatbot
        )

    def get_chatbot_by_id(self, chatbot_id) -> Chatbot:
        chatbot = None
        session = self.db_handler.get_db_session()
        try:
            chatbot = session.query(Chatbot).filter_by(id=chatbot_id).options(joinedload(Chatbot.target_files)).first()
            if chatbot is None:
                chatbot = session.query(Chatbot).options(joinedload(Chatbot.target_files)).first()
        finally:
            session.close()
        return chatbot

    def delete_chatbot_by_name(self, chatbot_name):
        self.db_handler.delete_chatbot_by_name(chatbot_name)

    def create_chatbot(self, chatbot_name):
        self.db_handler.create_chatbot(chatbot_name)

    def add_chatbot_document_to_chatbot(self, chatbot, file_path):
        session = self.db_handler.get_db_session()
        try:
            document = session.query(TargetFiles).filter_by(chatbot_id=chatbot.id, file_path=file_path).first()
            if document is None:
                document = TargetFiles(file_path=file_path, chatbot_id=chatbot.id)
            session.merge(document)  # Use merge instead of add
            session.commit()
        finally:
            session.close()

    #######################################
    ### SAVED PROMPTS ###
    #######################################
    def create_saved_prompt(self, data: dict):
        self.db_handler.create_saved_prompt(data)

    def update_saved_prompt(self, saved_prompt: SavedPrompt):
        self.db_handler.update_saved_prompt(saved_prompt)
        self.__settings_updated()

    def get_saved_prompt_by_id(self, prompt_id) -> SavedPrompt:
        self.db_handler.get_saved_prompt_by_id(prompt_id)

    #######################################
    ### SETTINGS ###
    #######################################
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
        else:
            logging.error(f"Invalid setting name: {setting_name}")

    def update_application_settings(self, column_name, val):
        self.db_handler.update_setting(ApplicationSettings, column_name, val)
        self.__settings_updated()

    #######################################
    ### TTS Settings ###
    #######################################
    def update_espeak_settings(self, column_name, val):
        self.db_handler.update_setting(EspeakSettings, column_name, val)
        self.__settings_updated()

    def update_tts_settings(self, column_name, val):
        self.db_handler.update_setting(TTSSettings, column_name, val)
        self.__settings_updated()

    def update_speech_t5_settings(self, column_name, val):
        self.db_handler.update_setting(SpeechT5Settings, column_name, val)
        self.__settings_updated()


    #######################################
    ### CONTROLNET ###
    #######################################
    def update_controlnet_settings(self, column_name, val):
        self.db_handler.update_setting(ControlnetSettings, column_name, val)
        self.__settings_updated()

    def update_brush_settings(self, column_name, val):
        self.db_handler.update_setting(BrushSettings, column_name, val)
        self.__settings_updated()

    def update_image_to_image_settings(self, column_name, val):
        self.db_handler.update_setting(ImageToImageSettings, column_name, val)
        self.__settings_updated()

    def update_outpaint_settings(self, column_name, val):
        self.db_handler.update_setting(OutpaintSettings, column_name, val)
        self.__settings_updated()

    def update_drawing_pad_settings(self, column_name, val):
        self.db_handler.update_setting(DrawingPadSettings, column_name, val)
        self.__settings_updated()

    def update_grid_settings(self, column_name, val):
        self.db_handler.update_setting(GridSettings, column_name, val)
        self.__settings_updated()

    def update_active_grid_settings(self, column_name, val):
        self.db_handler.update_setting(ActiveGridSettings, column_name, val)
        self.__settings_updated()

    #######################################
    ### PATH ###
    #######################################
    def update_path_settings(self, column_name, val):
        self.db_handler.update_setting(PathSettings, column_name, val)
        self.__settings_updated()

    def reset_path_settings(self):
        self.db_handler.reset_path_settings()

    def update_memory_settings(self, column_name, val):
        self.db_handler.update_setting(MemorySettings, column_name, val)
        self.__settings_updated()

    def update_metadata_settings(self, column_name, val):
        self.db_handler.update_setting(MetadataSettings, column_name, val)
        self.__settings_updated()

    def update_llm_generator_settings(self, column_name, val):
        self.db_handler.update_setting(LLMGeneratorSettings, column_name, val)
        self.__settings_updated()

    def __settings_updated(self):
        self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL)

    def reset_settings(self):
        self.db_handler.reset_settings()

    #######################################
    ### AI MODELS ###
    #######################################
    def update_ai_models(self, models: List[AIModels]):
        self.db_handler.update_ai_models(models)
        self.__settings_updated()

    def update_ai_model(self, model: AIModels):
        self.db_handler.update_ai_model(model)
        self.__settings_updated()

    #######################################
    ### PROMPT TEMPLATES ###
    #######################################
    def get_prompt_template_by_name(self, name) -> PromptTemplate:
        return self.db_handler.get_prompt_template_by_name(name)

    #######################################
    ### CONTROLNET MODELS ###
    #######################################
    def controlnet_model_by_name(self, name) -> ControlnetModel:
        return self.db_handler.controlnet_model_by_name(name)

    def get_font_setting_by_name(self, name) -> FontSetting:
        return self.db_handler.get_font_setting_by_name(name)

    def update_font_setting(self, font_setting: FontSetting):
        self.db_handler.update_font_setting(font_setting)
        self.__settings_updated()

    def ai_model_get_by_filter(self, filter_dict: dict) -> List[AIModels]:
        results = []
        models = self.db_handler.load_ai_models()
        for item in models:
            match = True
            for k, v in filter_dict.items():
                if isinstance(item, dict):
                    if item.get(k, "") != v:
                        match = False
                        break
                else:
                    if not hasattr(item, k) or getattr(item, k) != v:
                        match = False
                        break
            if match:
                results.append(item)
        return results

    #######################################
    ### GENERATOR SETTINGS ###
    #######################################
    def update_generator_settings(self, column_name, val):
        generator_settings = self.generator_settings
        setattr(generator_settings, column_name, val)
        self.save_generator_settings(generator_settings)

    def save_generator_settings(self, generator_settings):
        self.db_handler.save_generator_settings(generator_settings)
        self.__settings_updated()


    #######################################
    ### WINDOW SETTINGS ###
    #######################################
    @property
    def window_settings(self):
        return self.db_handler.load_window_settings()


    def save_window_settings(self, column_name, val):
        window_settings = self.window_settings
        setattr(window_settings, column_name, val)
        self.db_handler.save_window_settings(window_settings)
