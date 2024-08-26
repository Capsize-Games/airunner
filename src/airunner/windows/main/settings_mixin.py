import logging
import threading
from PySide6.QtCore import (
    QSettings,
    QByteArray,
    QDataStream,
    QIODevice
)
from airunner.settings import (
    ORGANIZATION,
    APPLICATION_NAME,
    DEFAULT_APPLICATION_SETTINGS, BASE_PATH
)
from airunner.enums import (
    SignalCode,
)
from airunner.utils.os.validate_path import validate_path

class SettingsMixin:
    _instance = None
    _lock = threading.Lock()
    _cached_settings = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    logging.debug("Creating new instance of SettingsMixin")
                    cls._instance = super(SettingsMixin, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            logging.debug("SettingsMixin instance already initialized")
            return
        self._initialized = True
        logging.debug("Initializing SettingsMixin instance")

        self.application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        self.default_settings = DEFAULT_APPLICATION_SETTINGS

        self.update_settings()
        self.reset_paths()

    @property
    def current_bot(self):
        current_bot_name = self.settings["llm_generator_settings"]["current_chatbot"]
        current_bot = self.settings["llm_generator_settings"]["saved_chatbots"][current_bot_name]
        return current_bot

    @property
    def settings(self):
        """
        Gets the settings dictionary.
        :return:
        """
        if SettingsMixin._cached_settings is not None:
            return SettingsMixin._cached_settings

        try:
            settings_byte_array = self.application_settings.value("settings", QByteArray())
            if settings_byte_array:
                data_stream = QDataStream(settings_byte_array, QIODevice.ReadOnly)
                settings = data_stream.readQVariant()
                SettingsMixin._cached_settings = settings
                return settings
            else:
                return self.default_settings
        except (TypeError, RuntimeError) as e:
            print("Failed to get settings")
            print(e)
            return self.default_settings

    @settings.setter
    def settings(self, val):
        """
        Sets the settings dictionary and updates the paths if the base path has changed.
        :param val:
        :return:
        """
        try:
            self.set_settings(val)
            SettingsMixin._cached_settings = val
        except Exception as e:
            print("Failed to set settings")
            print(e)

    def construct_paths_if_base_path_changed(self, updated_settings: dict) -> dict:
        """
        Constructs the paths if the base path has changed.
        :param updated_settings:
        :return:
        """
        #settings = self.get_settings()
        settings = self.settings
        if (
            settings is not None and
            updated_settings is not None and
            "path_settings" in settings and
            "path_settings" in updated_settings and
            settings["path_settings"].get("base_path", "") != updated_settings["path_settings"].get("base_path", "")
        ):
            path = settings["path_settings"].get("base_path", "")
            if path == "":
                return updated_settings
            updated_settings["path_settings"] = self.construct_paths(path)
        return updated_settings

    def update_settings(self):
        """
        Updates the settings.
        :return:
        """
        default_settings = self.default_settings
        current_settings = self.settings
        if current_settings is None:
            current_settings = default_settings
        else:
            self.recursive_update(current_settings, default_settings)
        path_settings = self.construct_paths(BASE_PATH)
        current_settings["path_settings"].update(path_settings)
        self.settings = current_settings

    def recursive_update(self, current, default):
        # Remove keys that are in current but not in default
        keys_to_remove = [k for k in current if k not in default]
        for k in keys_to_remove:
            del current[k]

        # Update or add keys from default to current
        for k, v in default.items():
            if k not in current or not isinstance(current[k], type(v)):
                current[k] = v
            elif isinstance(v, dict):
                self.recursive_update(current[k], v)

    # def get_settings(self):
    #     try:
    #         settings_byte_array = self.application_settings.value(
    #             "settings",
    #             QByteArray()
    #         )
    #         if settings_byte_array:
    #             data_stream = QDataStream(
    #                 settings_byte_array,
    #                 QIODevice.ReadOnly
    #             )
    #             settings = data_stream.readQVariant()
    #             return settings
    #         else:
    #             return self.default_settings
    #     except (TypeError, RuntimeError) as e:
    #         print("Failed to get settings")
    #         print(e)
    #         return self.default_settings

    def set_settings(self, val):
        if val:
            settings_byte_array = QByteArray()
            data_stream = QDataStream(settings_byte_array, QIODevice.WriteOnly)
            data_stream.writeQVariant(val)
            self.application_settings.setValue("settings", settings_byte_array)
            self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL)

    def save_settings(self):
        self.application_settings.sync()

    def is_valid_path(self, path: str) -> bool:
        try:
            return validate_path(path)
        except ValueError as e:
            print(f"Invalid base path: {e}")
            return {}

    def construct_paths(self, base_path):
        """
        Constructs a dictionary of paths used throughout the application based on the base path.
        Validates the base path to prevent security issues before using it to build other paths.

        Parameters:
            base_path (str): The base directory for building subpaths.

        Returns:
            dict: A dictionary containing all the constructed and validated paths.
        """
        # Validate the base path to prevent security issues
        if not self.is_valid_path(base_path):
            return {}

        paths = {
            "base_path": base_path,
            "art_models": f"{base_path}/art/models",
            "art_other": f"{base_path}/art/other",
            "text_models": f"{base_path}/text/models",
            "text_other": f"{base_path}/text/other",
            "txt2img_model_path": f"{base_path}/art/models/txt2img",
            "img2img_model_path": f"{base_path}/art/models/txt2img",
            "depth2img_model_path": f"{base_path}/art/models/depth2img",
            "pix2pix_model_path": f"{base_path}/art/models/pix2pix",
            "inpaint_model_path": f"{base_path}/art/models/inpaint",
            "upscale_model_path": f"{base_path}/art/models/upscale",
            "superresolution_model_path": f"{base_path}/art/models/superresolution",
            "txt2vid_model_path": f"{base_path}/art/models/txt2vid",
            "vae_model_path": f"{base_path}/art/models/vae",
            "safety_checker_model_path": f"{base_path}/art/models/safety_checker",
            "feature_extractor_model_path": f"{base_path}/art/models/feature_extractor",
            "controlnet_model_path": f"{base_path}/art/models/controlnet",
            "embeddings_model_path": f"{base_path}/art/models/embeddings",
            "lora_model_path": f"{base_path}/art/models/lora",
            "image_path": f"{base_path}/art/other/images",
            "video_path": f"{base_path}/art/other/videos",
            "ebook_path": f"{base_path}/text/other/ebooks",
            "documents_path": f"{base_path}/text/other/documents",
            "webpages_path": f"{base_path}/text/other/webpages",
            "pdf_path": f"{base_path}/text/other/pdfs",
            "tts_speaker_embeddings_path": f"{base_path}/text/models/speaker_embeddings",
            "tts_datasets_path": f"{base_path}/text/models/datasets",
            "tts_model_path": f"{base_path}/text/models/tts",
            "stt_model_path": f"{base_path}/text/models/stt",
            "llm_causallm_model_path": f"{base_path}/text/models/causallm",
            "llm_seq2seq_model_path": f"{base_path}/text/models/seq2seq",
            "llm_visualqa_model_path": f"{base_path}/text/models/visualqa",
            "llm_misc_model_path": f"{base_path}/text/models/misc",
            "feature_extraction_model_path": f"{base_path}/text/models/feature_extraction",
            "rag_documents_path": f"{base_path}/text/other/rag_temp",
            "sentence_transformers_path": f"{base_path}/text/models/sentence_transformers",
            "storage_path": f"{base_path}/storage",
            "llama_index_path": f"{base_path}/other/llama_index",
        }
        return paths

    def reset_paths(self):
        settings = self.settings
        path = self.settings["path_settings"].get("base_path", "")
        if path == "":
            return
        settings["path_settings"] = self.construct_paths(path)
        self.settings = settings
