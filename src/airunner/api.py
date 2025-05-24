import os
from typing import Optional, Dict, Any

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import QObject

from airunner.app import App
from airunner.enums import (
    EngineResponseCode,
    ModelStatus,
    ModelType,
    SignalCode,
)
from airunner.utils.application.create_worker import create_worker
from airunner.gui.utils.ui_dispatcher import render_ui_from_spec
from airunner.utils.application.ui_loader import (
    load_ui_file,
    load_ui_from_string,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.audio.sound_device_manager import SoundDeviceManager

from airunner.api import api as api_module
from airunner.api.image_filter_services import ImageFilterAPIServices
from airunner.api.embedding_services import EmbeddingAPIServices
from airunner.api.lora_services import LoraAPIServices
from airunner.api.nodegraph_services import NodegraphAPIService
from airunner.api.video_services import VideoAPIService
from airunner.api.stt_services import STTAPIService
from airunner.api.tts_services import TTSAPIService
from airunner.api.canvas_services import CanvasAPIService
from airunner.api.art_services import ARTAPIService
from airunner.api.chatbot_services import ChatbotAPIService
from airunner.api.llm_services import LLMAPIService


class API(App):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, *args, **kwargs):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.paths = {
            "google-bert/bert-base-multilingual-uncased": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "google-bert/bert-base-multilingual-uncased",
                )
            ),
            "google-bert/bert-base-uncased": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "google-bert/bert-base-uncased",
                )
            ),
            "dbmdz/bert-base-french-europeana-cased": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "dbmdz/bert-base-french-europeana-cased",
                )
            ),
            "dccuchile/bert-base-spanish-wwm-uncased": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "dccuchile/bert-base-spanish-wwm-uncased",
                )
            ),
            "kykim/bert-kor-base": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "kykim/bert-kor-base",
                )
            ),
            "myshell-ai/MeloTTS-English": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-English",
                )
            ),
            "myshell-ai/MeloTTS-English-v3": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-English-v3",
                )
            ),
            "myshell-ai/MeloTTS-French": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-French",
                )
            ),
            "myshell-ai/MeloTTS-Japanese": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-Japanese",
                )
            ),
            "myshell-ai/MeloTTS-Spanish": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-Spanish",
                )
            ),
            "myshell-ai/MeloTTS-Chinese": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-Chinese",
                )
            ),
            "myshell-ai/MeloTTS-Korean": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "myshell-ai/MeloTTS-Korean",
                )
            ),
            "tohoku-nlp/bert-base-japanese-v3": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "tohoku-nlp/bert-base-japanese-v3",
                )
            ),
            "hfl/chinese-roberta-wwm-ext-large": os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    "hfl/chinese-roberta-wwm-ext-large",
                )
            ),
        }
        self._initialized = True
        self.llm = LLMAPIService(emit_signal=self.emit_signal)
        self.art = ARTAPIService(emit_signal=self.emit_signal)
        self.image_filter = ImageFilterAPIServices(
            emit_signal=self.emit_signal
        )
        self.embedding = EmbeddingAPIServices(emit_signal=self.emit_signal)
        self.lora = LoraAPIServices(emit_signal=self.emit_signal)
        self.canvas = CanvasAPIService(emit_signal=self.emit_signal)
        self.chatbot = ChatbotAPIService(emit_signal=self.emit_signal)
        self.tts = TTSAPIService(emit_signal=self.emit_signal)
        self.stt = STTAPIService(emit_signal=self.emit_signal)
        self.video = VideoAPIService(emit_signal=self.emit_signal)
        self.nodegraph = NodegraphAPIService(emit_signal=self.emit_signal)
        self.sounddevice_manager = SoundDeviceManager()

        # Extract the initialize_app flag and pass the rest to the parent App class
        self._initialize_app = kwargs.pop("initialize_app", True)
        initialize_gui = kwargs.pop("initialize_gui", True)
        self.signal_handlers = {
            SignalCode.SHOW_WINDOW_SIGNAL: self.show_hello_world_window,
            SignalCode.SHOW_DYNAMIC_UI_FROM_STRING_SIGNAL: self.show_dynamic_ui_from_string,
        }
        super().__init__(*args, initialize_gui=initialize_gui, **kwargs)
        if self._initialize_app:
            api_module.setup_database()
        self._initialize_model_scanner()

    def _initialize_model_scanner(self):
        from airunner.workers.model_scanner_worker import (
            ModelScannerWorker,
        )

        if self._initialize_app:
            api_module.setup_database()
            self.model_scanner_worker = create_worker(ModelScannerWorker)
            self.model_scanner_worker.add_to_queue("scan_for_models")

    def show_hello_world_window(self):
        """
        Display a 'Hello, world!' popup window using the UI dispatcher.
        """
        spec = {
            "type": "window",
            "title": "Hello Window",
            "layout": "vertical",
            "widgets": [{"type": "label", "text": "Hello, world!"}],
        }
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle(spec.get("title", "Untitled"))
        render_ui_from_spec(spec, dialog)
        dialog.exec()

    def show_dynamic_ui(self, ui_file_path: str):
        """
        Load and display a .ui file dynamically as a popup window.

        :param ui_file_path: Path to the .ui file.
        """
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle("Dynamic UI")
        widget = load_ui_file(ui_file_path, dialog)
        layout = dialog.layout() or QVBoxLayout(dialog)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()

    def show_dynamic_ui_from_string(self, data: Dict):
        """
        Load and display a .ui file dynamically from a string as a popup window.

        :param ui_content: The content of the .ui file as a string.
        """
        ui_content = data.get("ui_content", "")

        class SignalHandler(QObject):
            def __init__(self, api: API):
                self.api = api
                super().__init__()

            def click_me_button(self):
                self.api.emit_signal(SignalCode.SHOW_WINDOW_SIGNAL)

        signal_handler = SignalHandler(api=self)
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle("Dynamic UI with Signal")
        widget = load_ui_from_string(ui_content, dialog, signal_handler)
        layout = dialog.layout() or QVBoxLayout(dialog)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()

    def change_model_status(self, model: ModelType, status: ModelStatus):
        """
        Change the status of a model and emit a signal.
        :param model: The model type.
        :param status: The new status of the model.
        """
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model, "status": status},
        )

    def worker_response(self, code: EngineResponseCode, message: Dict):
        """
        Emit a signal indicating a response from the worker.
        :param code: The response code from the worker.
        :param message: The message from the worker.
        """
        self.emit_signal(
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
            {"code": code, "message": message},
        )

    def quit_application(self):
        """
        Emit a signal to quit the application.
        """
        self.emit_signal(SignalCode.QUIT_APPLICATION, {})

    def application_error(self, message: str):
        """
        Emit a signal indicating an application error.
        :param message: The error message.
        """
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
            {"message": message},
        )

    def application_status(self, message: str):
        """
        Emit a signal indicating application status.
        :param message: The status message.
        """
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            {"message": message},
        )

    def update_download_log(self, message: str):
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": message},
        )

    def set_download_progress(self, current: int, total: int):
        self.emit_signal(
            SignalCode.DOWNLOAD_PROGRESS,
            {"current": current, "total": total},
        )

    def clear_download_status(self):
        self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)

    def set_download_status(self, message: str):
        self.emit_signal(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            {"message": message},
        )

    def download_complete(self, file_name: str = ""):
        self.emit_signal(
            SignalCode.DOWNLOAD_COMPLETE, {"file_name": file_name}
        )

    def clear_status_message(self):
        self.emit_signal(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)

    def main_window_loaded(self, main_window: Any):
        self.emit_signal(
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL,
            {"main_window": main_window},
        )

    def clear_prompts(self):
        self.emit_signal(SignalCode.CLEAR_PROMPTS)

    def keyboard_shortcuts_updated(self):
        self.emit_signal(SignalCode.KEYBOARD_SHORTCUTS_UPDATED)

    def reset_paths(self):
        self.emit_signal(SignalCode.APPLICATION_RESET_PATHS_SIGNAL)

    def application_settings_changed(
        self, setting_name: str, column_name: str, val: Any
    ):
        self.emit_signal(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            {
                "setting_name": setting_name,
                "column_name": column_name,
                "value": val,
            },
        )

    def widget_element_changed(self, element: str, value_name: str, val: Any):
        self.emit_signal(
            SignalCode.WIDGET_ELEMENT_CHANGED_SIGNAL,
            {
                "element": element,
                value_name: val,
            },
        )

    def delete_prompt(self, prompt_id: int):
        self.emit_signal(
            SignalCode.SD_ADDITIONAL_PROMPT_DELETE_SIGNAL,
            {"prompt_id": prompt_id},
        )

    def refresh_stylesheet(
        self,
        dark_mode: Optional[bool] = None,
        override_system_theme: Optional[bool] = None,
    ):
        self.emit_signal(
            SignalCode.REFRESH_STYLESHEET_SIGNAL,
            {
                "dark_mode": dark_mode,
                "override_system_theme": override_system_theme,
            },
        )

    def retranslate_ui_signal(self):
        self.emit_signal(SignalCode.RETRANSLATE_UI_SIGNAL)

    def update_locale(self, data: Dict):
        self.emit_signal(SignalCode.UPATE_LOCALE, data)

    def llm_model_download_progress(self, percent: int):
        self.emit_signal(
            SignalCode.LLM_MODEL_DOWNLOAD_PROGRESS, {"percent": percent}
        )

    def connect_signal(self, signal_code, handler):
        # Use MediatorMixin's register_signal_handler, not QApplication
        self.register_signal_handler(signal_code, handler)

    def register_signal_handler(self, signal_code, handler):
        MediatorMixin.register_signal_handler(self, signal_code, handler)
