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
from airunner.utils.get_current_chatbot import get_current_chatbot
from airunner.utils.os.validate_path import validate_path


class ReadWriteLock:
    def __init__(self):
        self._read_ready = threading.Condition(threading.Lock())
        self._readers = 0

    def acquire_read(self):
        with self._read_ready:
            self._readers += 1

    def release_read(self):
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self):
        self._read_ready.acquire()
        while self._readers > 0:
            self._read_ready.wait()

    def release_write(self):
        self._read_ready.release()


class SettingsMixin:
    _instance = None
    _lock = threading.Lock()
    _cached_settings_lock = ReadWriteLock()
    _cached_settings = None
    _settings_lock = threading.Lock()

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

    @property
    def current_bot(self):
        return get_current_chatbot(self.settings)

    @property
    def settings(self):
        """
        Gets the settings dictionary.
        :return:
        """
        self._cached_settings_lock.acquire_read()
        try:
            if SettingsMixin._cached_settings is not None:
                return SettingsMixin._cached_settings

            settings_byte_array = self.application_settings.value("settings", QByteArray())
            if settings_byte_array:
                data_stream = QDataStream(settings_byte_array, QIODevice.ReadOnly)
                settings = data_stream.readQVariant()
                self.cached_settings = settings
                return settings
            else:
                return self.default_settings
        except (TypeError, RuntimeError) as e:
            logging.error("Failed to get settings")
            logging.error(e)
            return self.default_settings
        finally:
            logging.debug("Releasing _cached_settings_lock after reading settings")

    @settings.setter
    def settings(self, val):
        """
        Sets the settings dictionary and updates the paths if the base path has changed.
        :param val:
        :return:
        """
        self._cached_settings_lock.acquire_read()
        try:
            self.set_settings(val)
            SettingsMixin._cached_settings = val
        except Exception as e:
            logging.error("Failed to set settings")
            logging.error(e)
        finally:
            logging.debug("Releasing _cached_settings_lock after writing settings")

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
        self.save_settings()

    def recursive_update(self, current, default):
        # Remove keys that are in current but not in default
        keys_to_remove = [k for k in current if k not in default]
        for k in keys_to_remove:
            del current[k]

        # Update or add keys from default to current
        for k, v in default.items():
            if k not in current:
                current[k] = v
            elif isinstance(v, dict):
                self.recursive_update(current[k], v)

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
            print("Invalid base path: {e}")
            return {}
