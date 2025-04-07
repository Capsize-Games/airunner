from abc import ABC, abstractmethod
from typing import Tuple, Type, Optional, Dict, Callable
import threading

import pygame
from pygame.locals import *

from PySide6.QtWidgets import QMainWindow, QSizePolicy
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QResizeEvent, QPainter, QImage, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QVBoxLayout

from airunner.enums import SignalCode
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.sd_worker import SDWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
from airunner.utils.application import create_worker
from airunner.gui.windows.main.ai_model_mixin import AIModelMixin
from airunner.gui.windows.main.pipeline_mixin import PipelineMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.api import API
from airunner.handlers.llm.agent.agents import LocalAgent
from airunner.handlers.stablediffusion.image_response import ImageResponse
from airunner.settings import (
    AIRUNNER_STT_ON,
    AIRUNNER_TTS_ON,
    AIRUNNER_LLM_ON,
    AIRUNNER_SD_ON,
)
from airunner.enums import EngineResponseCode


# Map of PySide6 key codes to Pygame key codes
# This is incomplete and should be expanded as needed
KEY_MAP = {
    Qt.Key.Key_Escape: K_ESCAPE,
    Qt.Key.Key_Return: K_RETURN,
    Qt.Key.Key_Enter: K_RETURN,
    Qt.Key.Key_Space: K_SPACE,
    Qt.Key.Key_Up: K_UP,
    Qt.Key.Key_Down: K_DOWN,
    Qt.Key.Key_Left: K_LEFT,
    Qt.Key.Key_Right: K_RIGHT,
    Qt.Key.Key_A: K_a,
    Qt.Key.Key_B: K_b,
    Qt.Key.Key_C: K_c,
    Qt.Key.Key_D: K_d,
    Qt.Key.Key_E: K_e,
    Qt.Key.Key_F: K_f,
    Qt.Key.Key_G: K_g,
    Qt.Key.Key_H: K_h,
    Qt.Key.Key_I: K_i,
    Qt.Key.Key_J: K_j,
    Qt.Key.Key_K: K_k,
    Qt.Key.Key_L: K_l,
    Qt.Key.Key_M: K_m,
    Qt.Key.Key_N: K_n,
    Qt.Key.Key_O: K_o,
    Qt.Key.Key_P: K_p,
    Qt.Key.Key_Q: K_q,
    Qt.Key.Key_R: K_r,
    Qt.Key.Key_S: K_s,
    Qt.Key.Key_T: K_t,
    Qt.Key.Key_U: K_u,
    Qt.Key.Key_V: K_v,
    Qt.Key.Key_W: K_w,
    Qt.Key.Key_X: K_x,
    Qt.Key.Key_Y: K_y,
    Qt.Key.Key_Z: K_z,
    Qt.Key.Key_0: K_0,
    Qt.Key.Key_1: K_1,
    Qt.Key.Key_2: K_2,
    Qt.Key.Key_3: K_3,
    Qt.Key.Key_4: K_4,
    Qt.Key.Key_5: K_5,
    Qt.Key.Key_6: K_6,
    Qt.Key.Key_7: K_7,
    Qt.Key.Key_8: K_8,
    Qt.Key.Key_9: K_9,
}


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
        screen_color: Tuple = (0, 0, 0),
        fps: int = 60
    ):
        self.api = api
        self.game_title: str = game_title
        self.width: int = width
        self.height: int = height
        self.screen: pygame.Surface = None
        self.screen_color: Tuple = screen_color
        self.running: bool = False
        self.fps: int = fps
        self.clock = pygame.time.Clock()
        self._initialize()
        self._start()
        
        for signal, handler in [
            (SignalCode.LLM_TEXT_STREAMED_SIGNAL, self._handle_llm_response_signal),
            (SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, self._handle_image_response_signal),
        ]:
            self.api.register(signal, handler)

        self.api.logger.info("PygameManager initialized")

    def _initialize(self):
        self.api.logger.info("Initializing Pygame")
        self._initialize_pygame()
        self._initialize_screen()
        self._initialize_display()
    
    def _handle_llm_response_signal(self, data: Dict):
        response = data.get("response")
        thread = threading.Thread(
            target=self._handle_llm_response,
            args=(response,)
        )
        thread.start()
    
    def _handle_image_response_signal(self, data: Dict):
        code = data["code"]
        callback = data.get("callback", None)

        if code in (
            EngineResponseCode.INSUFFICIENT_GPU_MEMORY,
        ):
            self.api.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                "Insufficient GPU memory."
            )
        elif code is EngineResponseCode.IMAGE_GENERATED:
            thread = threading.Thread(
                target=self._handle_image_response,
                args=(data.get("message", None),)
            )
            thread.start()
        else:
            self.api.logger.error(f"Unhandled response code: {code}")
        
        self.api.emit_signal(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL)
        
        if callback:
            callback(data)
    
    @abstractmethod
    def _handle_llm_response(self, response: LLMResponse):
        """
        Handle the LLM response.
        This method should be overridden by subclasses to provide
        specific functionality for handling LLM responses.
        """
    
    @abstractmethod
    def _handle_image_response(self, response: Optional[ImageResponse]):
        """
        Handle the image response.
        This method should be overridden by subclasses to provide
        specific functionality for handling image responses.
        """
            
    @abstractmethod
    def _start(self):
        """
        Start the Pygame loop.
        This method should be overridden by subclasses to provide
        specific functionality for the game loop.
        """
    
    def process_events(self):
        """
        Process Pygame events in a single step.
        This method should process events but not contain a loop.
        It will be called by the Qt timer.
        """
        pass
    
    def update(self):
        """
        Update game state in a single step.
        This method should be overridden by subclasses to provide
        specific functionality for updating the game state.
        """
        pass
    
    def render(self):
        """
        Render the game state to the screen.
        This method should be overridden by subclasses to provide
        specific functionality for rendering the game state.
        """
        pass
    
    def handle_pygame_event(self, event):
        """
        Handle a single pygame event.
        This method should be overridden by subclasses to provide
        specific functionality for handling pygame events.
        """
        pass
    
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
        if not pygame.get_init():
            pygame.init()
    
    def _initialize_screen(self):
        """
        Initialize the screen for the pygame window.
        """
        # Use pygame.Surface instead of pygame.display.set_mode
        # This creates an in-memory surface without a window
        self.screen = pygame.Surface((self.width, self.height))
    
    def _initialize_display(self):
        """
        Initialize the display for the pygame window.
        """
        # We don't set the caption since we're running in a PySide6 window
        pass
        
    def resize(self, width, height):
        """
        Resize the pygame surface.
        """
        self.width = width
        self.height = height
        self.screen = pygame.Surface((width, height))


class PygameWidget(QWidget):
    def __init__(self, pygame_manager, parent=None):
        super().__init__(parent)
        self.pygame_manager = pygame_manager
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(pygame_manager.width, pygame_manager.height)

        # Timer to update the Pygame display
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pygame)
        self.timer.start(int(1000 / self.pygame_manager.fps))  # Use the FPS from pygame_manager

    def update_pygame(self):
        """
        Update the Pygame display and repaint the widget.
        """
        # Process Pygame events in the Qt main thread
        self.pygame_manager.process_events()
        
        # Update game state
        self.pygame_manager.update()
        
        # Render the Pygame surface
        self.pygame_manager.render()
        
        # Maintain the target framerate
        self.pygame_manager.clock.tick(self.pygame_manager.fps)
        
        # Trigger a repaint
        self.update()

    def paintEvent(self, event):
        """
        Override the paint event to draw the Pygame surface onto the widget.
        """
        if not self.pygame_manager.screen:
            return
            
        # Create a QPainter for drawing onto this widget
        painter = QPainter(self)
        
        # Convert Pygame surface to QImage
        surface_data = pygame.image.tostring(self.pygame_manager.screen, "RGB")
        w = self.pygame_manager.screen.get_width()
        h = self.pygame_manager.screen.get_height()
        
        # Create a QImage from the raw data
        qimage = QImage(surface_data, w, h, w * 3, QImage.Format.Format_RGB888)
        
        # Draw the QImage onto the widget, scaled to fit if needed
        painter.drawImage(self.rect(), qimage)
        painter.end()

    def resizeEvent(self, event: QResizeEvent):
        """
        Handle resizing of the widget and update the Pygame surface size.
        """
        size = event.size()
        # Resize the pygame surface
        self.pygame_manager.resize(size.width(), size.height())
        super().resizeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """
        Convert Qt key events to Pygame key events
        """
        key = event.key()
        if key in KEY_MAP:
            # Create a pygame KEYDOWN event
            pygame_event = pygame.event.Event(
                KEYDOWN,
                key=KEY_MAP[key],
                mod=self._convert_modifiers(event.modifiers())
            )
            # Post the event to pygame's event queue
            pygame.event.post(pygame_event)
            # Also let the manager handle it directly
            self.pygame_manager.handle_pygame_event(pygame_event)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """
        Convert Qt key release events to Pygame key events
        """
        key = event.key()
        if key in KEY_MAP:
            # Create a pygame KEYUP event
            pygame_event = pygame.event.Event(
                KEYUP,
                key=KEY_MAP[key],
                mod=self._convert_modifiers(event.modifiers())
            )
            # Post the event to pygame's event queue
            pygame.event.post(pygame_event)
            # Also let the manager handle it directly
            self.pygame_manager.handle_pygame_event(pygame_event)
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Convert Qt mouse events to Pygame mouse events
        """
        pos = (event.position().x(), event.position().y())
        button = self._convert_mouse_button(event.button())
        
        # Create a pygame MOUSEBUTTONDOWN event
        pygame_event = pygame.event.Event(
            MOUSEBUTTONDOWN,
            pos=pos,
            button=button
        )
        # Post the event to pygame's event queue
        pygame.event.post(pygame_event)
        # Also let the manager handle it directly
        self.pygame_manager.handle_pygame_event(pygame_event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Convert Qt mouse release events to Pygame mouse events
        """
        pos = (event.position().x(), event.position().y())
        button = self._convert_mouse_button(event.button())
        
        # Create a pygame MOUSEBUTTONUP event
        pygame_event = pygame.event.Event(
            MOUSEBUTTONUP,
            pos=pos,
            button=button
        )
        # Post the event to pygame's event queue
        pygame.event.post(pygame_event)
        # Also let the manager handle it directly
        self.pygame_manager.handle_pygame_event(pygame_event)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Convert Qt mouse move events to Pygame mouse events
        """
        pos = (event.position().x(), event.position().y())
        buttons = self._convert_mouse_buttons(event.buttons())
        
        # Create a pygame MOUSEMOTION event
        pygame_event = pygame.event.Event(
            MOUSEMOTION,
            pos=pos,
            rel=(0, 0),  # relative movement, we're not tracking this
            buttons=buttons
        )
        # Post the event to pygame's event queue
        pygame.event.post(pygame_event)
        # Also let the manager handle it directly
        self.pygame_manager.handle_pygame_event(pygame_event)
        super().mouseMoveEvent(event)

    def _convert_modifiers(self, qt_modifiers):
        """
        Convert Qt keyboard modifiers to Pygame modifiers
        """
        pygame_modifiers = 0
        if qt_modifiers & Qt.KeyboardModifier.ShiftModifier:
            pygame_modifiers |= pygame.KMOD_SHIFT
        if qt_modifiers & Qt.KeyboardModifier.ControlModifier:
            pygame_modifiers |= pygame.KMOD_CTRL
        if qt_modifiers & Qt.KeyboardModifier.AltModifier:
            pygame_modifiers |= pygame.KMOD_ALT
        if qt_modifiers & Qt.KeyboardModifier.MetaModifier:
            pygame_modifiers |= pygame.KMOD_META
        return pygame_modifiers

    def _convert_mouse_button(self, qt_button):
        """
        Convert Qt mouse button to Pygame mouse button
        """
        if qt_button == Qt.MouseButton.LeftButton:
            return 1
        elif qt_button == Qt.MouseButton.MiddleButton:
            return 2
        elif qt_button == Qt.MouseButton.RightButton:
            return 3
        return 0

    def _convert_mouse_buttons(self, qt_buttons):
        """
        Convert Qt mouse buttons to Pygame mouse buttons tuple
        """
        left = bool(qt_buttons & Qt.MouseButton.LeftButton)
        middle = bool(qt_buttons & Qt.MouseButton.MiddleButton)
        right = bool(qt_buttons & Qt.MouseButton.RightButton)
        return (left, middle, right)

    def closeEvent(self, event):
        """
        Handle the widget close event and quit Pygame.
        """
        self.pygame_manager.quit()
        if pygame.get_init():
            pygame.quit()
        super().closeEvent(event)

    def sizeHint(self) -> QSize:
        """
        Return the recommended size for the widget.
        """
        return QSize(self.pygame_manager.width, self.pygame_manager.height)


class PygameWindow(
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    PipelineMixin,
    AIModelMixin,
    QMainWindow
):
    """
    A class to create a Pygame window using PySide6.
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
        local_agent_class: Optional[Type[LocalAgent]] = None,
        fps: int = 60,
        *args, 
        **kwargs
    ):
        """
        Initialize the Pygame window.
        :param app: The main application instance.
        :param game_class: The class that manages the Pygame window.
        :param width: The width of the Pygame window.
        :param height: The height of the Pygame window.
        :param fps: Frames per second for the game loop.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        """
        self.app = app
        self.pygame_manager = game_class(
            api=app,
            width=width,
            height=height,
            fps=fps,
            **kwargs.get('pygame_params', {})
        )
        if AIRUNNER_SD_ON:
            self._mask_generator_worker = create_worker(MaskGeneratorWorker)
            self._sd_worker = create_worker(SDWorker)
        
        if AIRUNNER_STT_ON:
            self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
            self._stt_audio_processor_worker = create_worker(AudioProcessorWorker)

        if AIRUNNER_TTS_ON:
            self._tts_generator_worker = create_worker(TTSGeneratorWorker)
            self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
        
        if AIRUNNER_LLM_ON:
            self._llm_generate_worker = create_worker(
                LLMGenerateWorker, 
                local_agent_class=local_agent_class
            )

        super().__init__(*args, **kwargs)
        self.setWindowTitle(f"AI Runner - {self.pygame_manager.game_title}")
        self.resize(width, height)

        # Create a central widget and layout
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better display

        # Create and add the PygameWidget
        self.pygame_widget = PygameWidget(self.pygame_manager, self)
        layout.addWidget(self.pygame_widget)

        self.setCentralWidget(central_widget)
        
        # Mark the game as running
        self.pygame_manager.running = True
        
        # Make sure the window is visible and has focus
        self.show()
        self.activateWindow()
        self.pygame_widget.setFocus()
        
        # Start the process to keep the game running
        QTimer.singleShot(0, self.pygame_manager.run)
    
    def closeEvent(self, event):
        """
        Handle the window close event.
        """
        self.pygame_manager.quit()
        if pygame.get_init():
            pygame.quit()
        super().closeEvent(event)


# Adapter for existing Pygame projects
class PygameAdapter(PygameManager):
    """
    An adapter class that makes it easier to integrate existing Pygame projects.
    
    This class provides a simpler interface for integrating existing Pygame
    projects with the AI Runner framework. It handles the basic setup and
    provides hooks for the existing game loop.
    
    Example usage:
    
    ```python
    # Original Pygame code
    def main():
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # Handle other events...
            
            # Update game state...
            
            # Render...
            screen.fill((0, 0, 0))
            # Draw stuff...
            pygame.display.flip()
            
            clock.tick(60)
        
        pygame.quit()
    
    # Using the adapter
    class MyGame(PygameAdapter):
        def handle_pygame_event(self, event):
            # Handle events same as in original code
            pass
            
        def update(self):
            # Update game state same as in original code
            pass
            
        def render(self):
            # Render same as in original code
            self.screen.fill((0, 0, 0))
            # Draw stuff...
    ```
    """
    def __init__(
        self,
        api: API,
        game_title: str = "Pygame Game",
        width: int = 800,
        height: int = 600,
        screen_color: Tuple = (0, 0, 0),
        fps: int = 60,
        event_handler: Optional[Callable[[pygame.event.Event], None]] = None,
        update_handler: Optional[Callable[[], None]] = None,
        render_handler: Optional[Callable[[pygame.Surface], None]] = None
    ):
        self.event_handler = event_handler
        self.update_handler = update_handler
        self.render_handler = render_handler
        super().__init__(
            api=api,
            game_title=game_title,
            width=width,
            height=height,
            screen_color=screen_color,
            fps=fps
        )
    
    def _handle_llm_response(self, response: LLMResponse):
        # Default implementation - can be overridden
        print(f"LLM: {response.message}")
    
    def _handle_image_response(self, response: Optional[ImageResponse]):
        # Default implementation - can be overridden
        if response and response.images:
            print(f"Received {len(response.images)} images")
    
    def _start(self):
        # Default initialization - can be overridden
        self.screen.fill(self.screen_color)
    
    def process_events(self):
        # Process all pending Pygame events
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            self.handle_pygame_event(event)
    
    def handle_pygame_event(self, event):
        # Use the provided event handler if available
        if self.event_handler:
            self.event_handler(event)
    
    def update(self):
        # Use the provided update handler if available
        if self.update_handler:
            self.update_handler()
    
    def render(self):
        # Use the provided render handler if available
        if self.render_handler:
            self.render_handler(self.screen)
    
    def quit(self):
        self.running = False
    
    def run(self):
        pass
