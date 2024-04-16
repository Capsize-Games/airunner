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
from airunner.settings import (
    DEFAULT_PATHS,
)


class SettingsMixin:
    def __init__(
        self,
        use_cuda: bool = DEFAULT_APPLICATION_SETTINGS["use_cuda"],
        ocr_enabled: bool = DEFAULT_APPLICATION_SETTINGS["ocr_enabled"],
        tts_enabled: bool = DEFAULT_APPLICATION_SETTINGS["tts_enabled"],
        stt_enabled: bool = DEFAULT_APPLICATION_SETTINGS["stt_enabled"],
        ai_mode: bool = DEFAULT_APPLICATION_SETTINGS["ai_mode"],
    ):
        """
        Constructor for the SettingsMixin class.
        Changes the default settings to the given parameters.
        :param use_cuda:
        :param ocr_enabled:
        :param tts_enabled:
        :param stt_enabled:
        :param ai_mode:
        """
        DEFAULT_APPLICATION_SETTINGS["use_cuda"] = use_cuda
        DEFAULT_APPLICATION_SETTINGS["ocr_enabled"] = ocr_enabled
        DEFAULT_APPLICATION_SETTINGS["tts_enabled"] = tts_enabled
        DEFAULT_APPLICATION_SETTINGS["stt_enabled"] = stt_enabled
        DEFAULT_APPLICATION_SETTINGS["ai_mode"] = ai_mode

        self.application_settings = QSettings(ORGANIZATION, APPLICATION_NAME)
        self.register(SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL, self.on_reset_settings_signal)
        self.default_settings = DEFAULT_APPLICATION_SETTINGS

    @property
    def settings(self):
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
        try:
            self.set_settings(val)
        except Exception as e:
            print("Failed to set settings")
            print(e)

    def update_settings(self):
        self.logger.debug("Updating settings")
        default_settings = self.default_settings
        current_settings = self.settings
        if current_settings is None:
            current_settings = default_settings
        else:
            self.recursive_update(current_settings, default_settings)
        self.logger.debug("Settings updated")

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
        self.logger.debug("Resetting settings")
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

    def reset_paths(self):
        settings = self.settings
        settings["path_settings"] = DEFAULT_PATHS
        self.settings = settings
