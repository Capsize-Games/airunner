from abc import ABC, abstractmethod
from typing import Tuple, Type, Optional
import pygame

from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QVBoxLayout

from airunner.enums import SignalCode, LLMActionType
from airunner.workers import (
    AudioCaptureWorker,
    AudioProcessorWorker,
    LLMGenerateWorker,
    MaskGeneratorWorker,
    SDWorker,
    TTSGeneratorWorker,
    TTSVocalizerWorker,
)
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.utils import create_worker
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.styles_mixin import StylesMixin
from airunner.mediator_mixin import MediatorMixin
from airunner.handlers.llm.llm_response import LLMResponse

from airunner.api import API

import threading # ADDED

class PygameManager(ABC):
    """
    A class to manage the Pygame window and its initialization.
    This class is responsible for setting up the Pygame environment,
    creating the window, and handling events.
    It is designed to be used with the AI Runner framework.
    This class is a wrapper around the Pygame library to provide
    a consistent interface for creating and managing a Pygame window.
    """
    def __init__(
        self, 
        api: API,
        game_title: str = "Pygame Window",
        width: int = 800,
        height: int = 600,
        screen_color: Tuple = (0, 0, 0)
    ):
        self.api = api
        self.game_title: str = game_title
        self.width: int = width
        self.height: int = height
        self.screen: pygame.Surface = None
        self.screen_color: Tuple = screen_color
        self._initialize()
        self._start()
        self.api.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, self._handle_llm_response_signal)
        self.api.logger.info("PygameManager initialized")

    def _initialize(self):
        self.api.logger.info("Initializing Pygame")
        self._initialize_pygame()
        self._initialize_screen()
        self._initialize_display()
    
    def _handle_llm_response_signal(self, data: dict):
        response = data.get("response")
        self._handle_llm_response(response)
    
    @abstractmethod
    def _handle_llm_response(self, response: LLMResponse):
        """
        Handle the LLM response.
        This method should be overridden by subclasses to provide
        specific functionality for handling LLM responses.
        """
        
    
    @abstractmethod
    def _start(self):
        """
        Start the Pygame loop.
        This method should be overridden by subclasses to provide
        specific functionality for the game loop.
        """
    
    @abstractmethod
    def run(self):
        """
        Run the Pygame loop.
        This method should be overridden by subclasses to provide
        specific functionality for the game loop.
        """
    
    @abstractmethod
    def quit(self):
        """
        Quit the Pygame loop.
        This method should be overridden by subclasses to provide
        specific functionality for quitting the game loop.
        """
        
    def _initialize_pygame(self):
        """
        Initialize the pygame library.
        """
        pygame.init()
    
    def _initialize_screen(self):
        """
        Initialize the screen for the pygame window.
        """
        self.screen = pygame.display.set_mode((self.width, self.height))
    
    def _initialize_display(self):
        """
        Initialize the display for the pygame window.
        """
        pygame.display.set_caption(self.game_title)


class PygameWidget(QWidget):
    def __init__(self, pygame_manager, parent=None):
        super().__init__(parent)
        self.pygame_manager = pygame_manager
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_PaintOnScreen)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Timer to update the Pygame display
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pygame)
        self.timer.start(16)  # ~60 FPS

    def update_pygame(self):
        """
        Update the Pygame display and repaint the widget.
        """
        QTimer.singleShot(0, self._render_pygame) # MODIFIED
        self.update()

    def _render_pygame(self):
        """
        Renders the pygame scene. Must be run on the main thread.
        """
        self.pygame_manager.set_screen_color()
        pygame.display.flip()

    def paintEvent(self, event):
        """
        Override the paint event to draw the Pygame surface onto the widget.
        """
        pass  # Pygame handles its own rendering

    def resizeEvent(self, event: QResizeEvent):
        """
        Handle resizing of the widget and update the Pygame display size.
        """
        size = event.size()
        self.pygame_manager.screen = pygame.display.set_mode((size.width(), size.height()))
        super().resizeEvent(event)

    def closeEvent(self, event):
        """
        Handle the widget close event and quit Pygame.
        """
        self.pygame_manager.quit()
        pygame.quit()
        super().closeEvent(event)


class PygameWindow(
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    PipelineMixin,
    AIModelMixin,
    QMainWindow
):
    """
    A class to create a Pygame window using PySide6."

    This class is a subclass of QMainWindow and is designed to be used
    with the AI Runner framework. It initializes a Pygame window and
    manages the Pygame event loop. The class also provides methods for
    sending requests and handling signals.
    """
    def __init__(
        self, 
        app, 
        game_class: Type[PygameManager],
        width: int = 800,
        height: int = 600,
        *args, 
        **kwargs
    ):
        """
        Initialize the Pygame window.
        :param app: The main application instance.
        :param game_class: The class that manages the Pygame window.
        :param width: The width of the Pygame window.
        :param height: The height of the Pygame window.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        """
        self.app = app
        self.pygame_manager = game_class(
            api=app,
            width=width,
            height=height,
        )
        self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        self._sd_worker = create_worker(SDWorker)
        self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        self._stt_audio_processor_worker = create_worker(AudioProcessorWorker)
        self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
        self._llm_generate_worker = create_worker(LLMGenerateWorker)

        super().__init__(*args, **kwargs)
        self.setWindowTitle("AI Runner - Pygame Window")

        # Create a central widget and layout
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        # Create and add the PygameWidget
        self.pygame_widget = PygameWidget(self.pygame_manager, self)
        layout.addWidget(self.pygame_widget)

        self.setCentralWidget(central_widget)

        # Create and start a thread for the Pygame loop
        pygame_thread = threading.Thread(target=self.pygame_manager.run)
        pygame_thread.daemon = True  # Allow the main program to exit even if the thread is still running
        pygame_thread.start()

    def send_llm_request(self, prompt: str, llm_request: Optional[LLMRequest] = None):
        self.app.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": LLMActionType.CHAT,
                    "prompt": prompt,
                    "llm_request": llm_request or LLMRequest.from_default()
                }
            }
        )
