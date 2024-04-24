import traceback
from PySide6.QtCore import (
    QSettings,
    QByteArray,
    QDataStream,
    QIODevice
)
from airunner.settings import (
    ORGANIZATION,
    APPLICATION_NAME,
    DEFAULT_APPLICATION_SETTINGS
)
from airunner.enums import (
    SignalCode,
)
from airunner.utils.os.validate_path import validate_path

class SettingsMixin:
    def __init__(
        self,
        use_cuda: bool = DEFAULT_APPLICATION_SETTINGS["use_cuda"],
        sd_enabled: bool = DEFAULT_APPLICATION_SETTINGS["sd_enabled"],
        controlnet_enabled: bool = DEFAULT_APPLICATION_SETTINGS["controlnet_enabled"],
        ocr_enabled: bool = DEFAULT_APPLICATION_SETTINGS["ocr_enabled"],
        tts_enabled: bool = DEFAULT_APPLICATION_SETTINGS["tts_enabled"],
        stt_enabled: bool = DEFAULT_APPLICATION_SETTINGS["stt_enabled"],
        ai_mode: bool = DEFAULT_APPLICATION_SETTINGS["ai_mode"],
    ):
        """
        Constructor for the SettingsMixin class.
        Changes the default settings to the given parameters.
        :param use_cuda:
        :param sd_enabled:
        :param ocr_enabled:
        :param tts_enabled:
        :param stt_enabled:
        :param ai_mode:
        """

        DEFAULT_APPLICATION_SETTINGS["use_cuda"] = use_cuda
        DEFAULT_APPLICATION_SETTINGS["sd_enabled"] = sd_enabled
        DEFAULT_APPLICATION_SETTINGS["controlnet_enabled"] = controlnet_enabled
        DEFAULT_APPLICATION_SETTINGS["ocr_enabled"] = ocr_enabled
        DEFAULT_APPLICATION_SETTINGS["tts_enabled"] = tts_enabled
        DEFAULT_APPLICATION_SETTINGS["stt_enabled"] = stt_enabled
        DEFAULT_APPLICATION_SETTINGS["ai_mode"] = ai_mode

        self.application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        self.register(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL, self.on_reset_settings_signal)
        self.default_settings = DEFAULT_APPLICATION_SETTINGS
        self.update_settings()

    @property
    def settings(self):
        """
        Gets the settings dictionary.
        :return:
        """
        try:
            settings = self.get_settings()
            if settings == {} or settings == "" or settings is None:
                print("SETTINGS IS BLANK")
                traceback.print_stack()
            return settings
        except Exception as e:
            print("Failed to get settings")
            print(e)
        return {}

    @settings.setter
    def settings(self, val):
        """
        Sets the settings dictionary and updates the paths if the base path has changed.
        :param val:
        :return:
        """
        val = self.construct_paths_if_base_path_changed(val)

        try:
            self.set_settings(val)
        except Exception as e:
            print("Failed to set settings")
            print(e)

    def construct_paths_if_base_path_changed(self, updated_settings: dict) -> dict:
        """
        Constructs the paths if the base path has changed.
        :param updated_settings:
        :return:
        """
        settings = self.get_settings()
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

        self.settings = current_settings

    def recursive_update(self, current, default):
        for k, v in default.items():
            if k not in current or k not in current or (
                not isinstance(
                    current[k], type(v)
                ) and v is not None
            ):
                current[k] = v
            elif isinstance(v, dict):
                self.recursive_update(current[k], v)

    def on_reset_settings_signal(self, _message: dict):
        print("Resetting settings")
        self.application_settings.clear()
        self.application_settings.sync()
        self.settings = self.settings

    def get_settings(self):
        application_settings = QSettings(
            ORGANIZATION,
            APPLICATION_NAME
        )
        try:
            settings_byte_array = application_settings.value(
                "settings",
                QByteArray()
            )
            if settings_byte_array:
                data_stream = QDataStream(
                    settings_byte_array,
                    QIODevice.ReadOnly
                )
                settings = data_stream.readQVariant()
                return settings
            else:
                return self.default_settings
        except (TypeError, RuntimeError) as e:
            print("Failed to get settings")
            print(e)
            return self.default_settings

    def set_settings(self, val):
        application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        if val:
            settings_byte_array = QByteArray()
            data_stream = QDataStream(settings_byte_array, QIODevice.WriteOnly)
            data_stream.writeQVariant(val)
            application_settings.setValue("settings", settings_byte_array)
            self.emit_signal(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL)

    def save_settings(self):
        application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        application_settings.sync()

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
            "depth2img_model_path": f"{base_path}/art/models/depth2img",
            "pix2pix_model_path": f"{base_path}/art/models/pix2pix",
            "inpaint_model_path": f"{base_path}/art/models/inpaint",
            "upscale_model_path": f"{base_path}/art/models/upscale",
            "txt2vid_model_path": f"{base_path}/art/models/txt2vid",
            "vae_model_path": f"{base_path}/art/models/vae",
            "safety_checker_model_path": f"{base_path}/art/models/safety_checker",
            "feature_extractor_model_path": f"{base_path}/art/models/feature_extractor",
            "controlnet_model_path": f"{base_path}/art/models/controlnet",
            "embeddings_model_path": f"{base_path}/art/models/embeddings",
            "lora_model_path": f"{base_path}/art/models/lora",
            "image_path": f"{base_path}/art/other/images",
            "video_path": f"{base_path}/art/other/videos",
            "ebooks_path": f"{base_path}/text/other/ebooks",
            "documents_path": f"{base_path}/text/other/documents",
            "tts_model_path": f"{base_path}/text/models/tts",
            "stt_model_path": f"{base_path}/text/models/stt",
            "llm_causallm_model_path": f"{base_path}/text/models/causallm",
            "llm_seq2seq_model_path": f"{base_path}/text/models/seq2seq",
            "llm_visualqa_model_path": f"{base_path}/text/models/visualqa",
            "llm_misc_model_path": f"{base_path}/text/models/misc",
            "llm_causallm_cache": f"{base_path}/text/models/causallm/cache",
            "llm_seq2seq_cache": f"{base_path}/text/models/seq2seq/cache",
            "llm_visualqa_cache": f"{base_path}/text/models/visualqa/cache",
            "llm_misc_cache": f"{base_path}/text/models/misc/cache",
        }
        return paths

    def reset_paths(self):
        settings = self.settings
        path = self.settings["path_settings"].get("base_path", "")
        if path == "":
            return
        settings["path_settings"] = self.construct_paths(path)
        self.settings = settings
