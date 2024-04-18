import os
from abc import abstractmethod, ABCMeta

from PySide6.QtCore import Slot
from PySide6.QtGui import QWindow
from airunner.aihandler.tts.speecht5_tts_handler import SpeechT5TTSHandler
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.worker_manager import WorkerManager

DISABLE_SD = os.getenv("DISABLE_SD", "False").lower() == "true"
DISABLE_LLM = os.getenv("DISABLE_LLM", "False").lower() == "true"
DISABLE_TTS = os.getenv("DISABLE_TTS", "False").lower() == "true"
DISABLE_STT = os.getenv("DISABLE_STT", "False").lower() == "true"
OCR_ENABLED = os.getenv("OCR_ENABLED", "False").lower() == "true"
DISABLE_VISION_CAPTURE = os.getenv("DISABLE_VISION_CAPTURE", "True").lower() == "true"
TTS_ENABLED = os.getenv("TTS_ENABLED", "True").lower() == "true"
STT_ENABLED = os.getenv("STT_ENABLED", "True").lower() == "true"
DO_LOAD_LLM_ON_INIT = os.getenv("DO_LOAD_LLM_ON_INIT", "True").lower() == "true"
TTS_HANDLER_CLASS = os.getenv("TTS_HANDLER_CLASS", "SpeechT5TTSHandler")


class CombinedMeta(ABCMeta, type(QWindow)):
    pass


class WindowInterface(
    QWindow,
    MediatorMixin,
    SettingsMixin,
    metaclass=CombinedMeta
):
    template_class_ = None
    template = None
    is_modal: bool = False  # allow the window to be treated as a modal
    title: str = "Base Window"

    def __init__(
        self,
        disable_sd: bool = True,
        disable_llm: bool = False,
        disable_tts: bool = False,
        disable_stt: bool = False,
        ocr_enabled: bool = False,
        disable_vision_capture: bool = True,
        tts_enabled: bool = True,
        stt_enabled: bool = True,
        do_load_llm_on_init: bool = True,
        tts_handler_class=SpeechT5TTSHandler,
    ):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()

        self.conversation_history = []
        self.vision_history = []
        self.prefix = ""
        self.prompt = ""
        self.suffix = ""

        self.worker_manager = WorkerManager(
            disable_sd=disable_sd,
            disable_llm=disable_llm,
            disable_tts=disable_tts,
            disable_stt=disable_stt,
            disable_vision_capture=disable_vision_capture,
            do_load_llm_on_init=do_load_llm_on_init,
            tts_handler_class=tts_handler_class
        )

    @Slot(bool)
    def toggle_tts(self, val: bool):
        settings = self.settings
        settings["tts_enabled"] = val
        self.settings = settings

    @Slot(bool)
    def toggle_stt(self, val: bool):
        settings = self.settings
        settings["stt_enabled"] = val
        self.settings = settings

    @abstractmethod
    def initialize_widget_elements(self):
        """
        Initialize the widget elements of the window.
        """
        pass

    @abstractmethod
    def restore_state(self):
        """
        Restore the state of the window.
        """
        pass

    @abstractmethod
    def terminate(self):
        """
        Cleanup method to close or release resources when plugin is stopped.
        """
        pass

