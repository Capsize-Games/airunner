import os
import re
import sys
import urllib
import webbrowser
from functools import partial
from typing import Dict, Optional

import requests
from PIL import Image
from PySide6 import QtGui
from PySide6.QtCore import (
    Slot,
    Signal,
    QProcess,
    QTimer,
)
from PySide6.QtGui import QGuiApplication, QKeySequence, QAction, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QCheckBox,
    QInputDialog,
    QSystemTrayIcon,
    QMenu,
)
from PySide6.QtGui import QIcon

from bs4 import BeautifulSoup

from airunner.settings import (
    AIRUNNER_STATUS_ERROR_COLOR,
    AIRUNNER_STATUS_NORMAL_COLOR_LIGHT,
    AIRUNNER_STATUS_NORMAL_COLOR_DARK,
    AIRUNNER_NSFW_CONTENT_DETECTED_MESSAGE,
    AIRUNNER_DISCORD_URL,
    AIRUNNER_BASE_PATH,
    AIRUNNER_BUG_REPORT_LINK,
    AIRUNNER_VULNERABILITY_REPORT_LINK,
    AIRUNNER_ART_ENABLED,
    AIRUNNER_MEM_SD_DEVICE,
    AIRUNNER_MEM_LLM_DEVICE,
    AIRUNNER_MEM_TTS_DEVICE,
    AIRUNNER_MEM_STT_DEVICE,
)
from airunner.utils.settings import get_qsettings
from airunner.handlers.llm.agent.actions.bash_execute import bash_execute
from airunner.handlers.llm.agent.actions.show_path import show_path
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.data.models.shortcut_keys import ShortcutKeys
from airunner.data.models.image_filter import ImageFilter
from airunner.data.models.drawingpad_settings import DrawingPadSettings
from airunner.data.models.tab import Tab
from airunner.app_installer import AppInstaller
from airunner.enums import (
    SignalCode,
    CanvasToolName,
    GeneratorSection,
    LLMActionType,
    ModelType,
    ModelStatus,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application.get_version import get_version
from airunner.utils.application.create_worker import create_worker
from airunner.utils.widgets import (
    save_splitter_settings,
    load_splitter_settings,
)
from airunner.utils.image import convert_image_to_binary
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.gui.widgets.stats.stats_widget import StatsWidget
from airunner.gui.widgets.status.status_widget import StatusWidget
from airunner.gui.windows.about.about import AboutWindow
from airunner.gui.windows.filter_window import FilterWindow
from airunner.gui.windows.main.ai_model_mixin import AIModelMixin
from airunner.gui.windows.main.pipeline_mixin import PipelineMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.gui.windows.main.templates.main_window_ui import Ui_MainWindow
from airunner.gui.windows.prompt_browser.prompt_browser import PromptBrowser
from airunner.gui.windows.settings.airunner_settings import SettingsWindow
from airunner.gui.windows.update.update_window import UpdateWindow
from airunner.gui.managers.icon_manager import IconManager
from airunner.plugin_loader import PluginLoader
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.sd_worker import SDWorker

try:
    from airunner.workers.audio_capture_worker import AudioCaptureWorker
    from airunner.workers.audio_processor_worker import AudioProcessorWorker
    from airunner.workers.tts_generator_worker import TTSGeneratorWorker
    from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
except OSError as e:
    print("Error loading audio workers:", e)
    AudioCaptureWorker = None
    AudioProcessorWorker = None
    TTSGeneratorWorker = None
    TTSVocalizerWorker = None


class MainWindow(
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    PipelineMixin,
    AIModelMixin,
    QMainWindow,
):
    show_grid_toggled = Signal(bool)
    image_generated = Signal(bool)
    generator_tab_changed_signal = Signal()
    load_image = Signal(str)
    load_image_object = Signal(object)
    loaded = Signal()
    window_opened = Signal()
    ui_class_ = Ui_MainWindow
    _window_title = f"AI Runner"
    icons = [
        ("settings", "actionSettings"),
        ("crosshair", "actionToggle_Controlnet"),
        ("cpu", "actionToggle_LLM"),
        ("mic", "actionToggle_Speech_to_Text"),
        ("image", "actionToggle_Stable_Diffusion"),
        ("image", "menuArt"),
        ("message-circle", "menuChat"),
        ("refresh-cw", "actionReset_Settings_2"),
        ("x-circle", "actionQuit"),
        ("plus-circle", "artActionNew"),
        ("upload-icon", "actionImport_image"),
        ("download-icon", "actionExport_image_button"),
        ("message-circle", "actionNew_Conversation"),
        ("trash-2", "actionDelete_conversation"),
        ("scissors", "actionCut"),
        ("copy", "actionCopy"),
        ("clipboard", "actionPaste"),
        ("corner-right-down", "actionRotate_90_clockwise"),
        ("corner-left-down", "actionRotate_90_counter_clockwise"),
        ("delete", "actionClear_all_prompts"),
        ("settings", "actionSettings"),
        ("book-open", "actionPrompt_Browser"),
        ("folder", "actionBrowse_AI_Runner_Path"),
        ("folder", "actionBrowse_Images_Path_2"),
        ("speaker", "actionToggle_Text_to_Speech"),
        ("object-selected-icon", "actionToggle_Active_Grid_Area"),
        ("pencil-icon", "actionToggle_Brush"),
        ("eraser-icon", "actionToggle_Eraser"),
        ("grid", "actionToggle_Grid"),
        ("image", "menuStable_Diffusion"),
        ("activity", "actionStats"),
        ("zap", "actionRun_setup_wizard_2"),
        ("x-circle", "actionCollapse_to_system_tray"),
        ("slash", "actionSafety_Checker"),
        ("external-link", "actionBug_report"),
        ("external-link", "actionReport_vulnerability"),
        ("message-square", "actionDiscord"),
        ("download", "actionImport_image"),
        ("upload", "actionExport_image_button"),
        ("codesandbox", "menuWorkflow"),
        ("trash-2", "workflow_actionClear"),
        ("edit", "workflow_actionEdit"),
        ("folder", "workflow_actionOpen"),
        ("pause-circle", "workflow_actionPause"),
        ("play", "workflow_actionRun"),
        ("save", "workflow_actionSave"),
        ("stop-circle", "workflow_actionStop"),
        ("corner-up-right", "actionRedo"),
        ("corner-up-left", "actionUndo"),
    ]

    def __init__(self, *args, **kwargs):
        self.ui = self.ui_class_()
        self.qsettings = get_qsettings()
        self.icon_manager: Optional[IconManager] = None
        self.quitting = False
        self.update_popup = None
        self._document_path = None
        self.prompt = None
        self.negative_prompt = None
        self.image_path = None
        self.token_signal = Signal(str)
        self.api = None
        self.input_event_manager = None
        self.tqdm_callback_triggered = False
        self.action = GeneratorSection.TXT2IMG.value
        self.progress_bar_started = False
        self.window = None
        self.canvas = None
        self.models = None
        self.client = None
        self._version = None
        self._latest_version = None
        self.status_error_color = AIRUNNER_STATUS_ERROR_COLOR
        self.status_normal_color_light = AIRUNNER_STATUS_NORMAL_COLOR_LIGHT
        self.status_normal_color_dark = AIRUNNER_STATUS_NORMAL_COLOR_DARK
        self._themes = None
        self.button_clicked_signal = Signal(Dict)
        self.status_widget = None
        self.header_widget_spacer = None
        self.deterministic_window = None
        self.generator = None
        self._generator = None
        self._generator_settings = None
        self.listening = False
        self.initialized = False
        self._model_status = {
            model_type: ModelStatus.UNLOADED for model_type in ModelType
        }
        self.signal_handlers = {
            SignalCode.SD_SAVE_PROMPT_SIGNAL: self.on_save_stablediffusion_prompt_signal,
            SignalCode.QUIT_APPLICATION: self.handle_quit_application_signal,
            SignalCode.SD_NSFW_CONTENT_DETECTED_SIGNAL: self.on_nsfw_content_detected_signal,
            SignalCode.BASH_EXECUTE_SIGNAL: self.on_bash_execute_signal,
            SignalCode.WRITE_FILE: self.on_write_file_signal,
            SignalCode.TOGGLE_FULLSCREEN_SIGNAL: self.on_toggle_fullscreen_signal,
            SignalCode.TOGGLE_TTS_SIGNAL: self.on_toggle_tts,
            SignalCode.TOGGLE_SD_SIGNAL: self.on_toggle_sd,
            SignalCode.TOGGLE_LLM_SIGNAL: self.on_toggle_llm,
            SignalCode.UNLOAD_NON_SD_MODELS: self.on_unload_non_sd_models,
            SignalCode.LOAD_NON_SD_MODELS: self.on_load_non_sd_models,
            SignalCode.APPLICATION_RESET_SETTINGS_SIGNAL: self._action_reset_settings,
            SignalCode.APPLICATION_RESET_PATHS_SIGNAL: self.on_reset_paths_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.KEYBOARD_SHORTCUTS_UPDATED: self.on_keyboard_shortcuts_updated,
            SignalCode.REFRESH_STYLESHEET_SIGNAL: self.on_theme_changed_signal,
            SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL: self.on_ai_models_save_or_update_signal,
            SignalCode.NAVIGATE_TO_URL: self.on_navigate_to_url,
            SignalCode.MISSING_REQUIRED_MODELS: self.display_missing_models_error,
            SignalCode.TOGGLE_TOOL: self.on_toggle_tool_signal,
            SignalCode.ENABLE_WORKFLOWS_TOGGLED: self.on_enable_workflows_toggled,
        }
        self.logger.debug("Starting AI Runnner")
        super().__init__()

        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.timeout.connect(self.handle_single_click)

        self.initialize_system_tray()

        # Add plugins directory to Python path
        plugins_path = os.path.join(self.path_settings.base_path, "plugins")
        if plugins_path not in sys.path:
            sys.path.append(plugins_path)

        self._updating_settings = True
        self._updating_settings = False
        self._worker_manager = None
        self.initialize_ui()
        self._initialize_workers()
        self.last_tray_click_time = 0

    @property
    def close_to_system_tray(self) -> bool:
        val = self.qsettings.value("close_to_system_tray")
        return val is True or val is None

    @property
    def generator_tab_widget(self):
        return self.ui.generator_widget

    @property
    def version(self):
        if self._version is None:
            self._version = get_version()
        return f"v{self._version}"

    @property
    def latest_version(self):
        return self._latest_version

    @latest_version.setter
    def latest_version(self, val):
        self._latest_version = val

    @property
    def document_name(self):
        return "Untitled"

    @property
    def enable_workflows(self) -> bool:
        return self.qsettings.value("enable_workflows") == "true"

    """
    Slot functions
    
    The following functions are defined in and connected to the appropriate
    signals in the corresponding ui file.
    """

    def on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon activation events."""
        print(f"Tray icon activated with reason: {reason}")

        # For single left click or double click, toggle visibility
        if (
            reason is QSystemTrayIcon.ActivationReason.Trigger
            or reason is QSystemTrayIcon.ActivationReason.DoubleClick
        ):
            print(f"Left click detected (reason: {reason})")
            self.toggle_window_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            print("Middle click detected")
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            print("Context menu requested")
            # Update menu text before showing context menu
            if self.isVisible():
                self.toggle_visibility_action.setText("Hide Window")
            else:
                self.toggle_visibility_action.setText("Show Window")

    @Slot()
    def on_actionQuit_triggered(self):
        self.handle_close()

    @Slot(bool)
    def on_actionCollapse_to_system_tray_toggled(self, val):
        self.qsettings.setValue("close_to_system_tray", val)
        self.qsettings.sync()

    @Slot(bool)
    def on_actionToggle_Eraser_toggled(self, active: bool):
        self.toggle_tool(CanvasToolName.ERASER, active)

    @Slot()
    def on_actionRecenter_triggered(self):
        self.api.art.canvas.recenter_grid()

    @Slot()
    def on_actionReset_Settings_2_triggered(self):
        self._action_reset_settings()

    @Slot()
    def import_controlnet_image(self):
        pass

    @Slot()
    def export_controlnet_image(self):
        pass

    @Slot()
    def import_drawingpad_image(self):
        pass

    @Slot()
    def export_drawingpad_image(self):
        pass

    @Slot()
    def on_actionExport_image_button_triggered(self):
        self.api.art.canvas.export_image()

    @Slot()
    def on_actionImport_image_triggered(self):
        self.api.art.canvas.import_image()

    @Slot()
    def on_artActionNew_triggered(self):
        self.api.art.canvas.clear()

    @Slot()
    def on_actionUndo_triggered(self):
        self.api.art.canvas.undo()

    @Slot()
    def on_actionRedo_triggered(self):
        self.api.art.canvas.redo()

    @Slot()
    def on_actionPaste_triggered(self):
        self.api.art.canvas.paste_image()

    @Slot()
    def on_actionCopy_triggered(self):
        self.api.art.canvas.copy_image()

    @Slot()
    def on_actionCut_triggered(self):
        self.api.art.canvas.cut_image()

    @Slot()
    def on_actionRotate_90_clockwise_triggered(self):
        self.api.art.canvas.rotate_image_90_clockwise()

    @Slot()
    def on_actionRotate_90_counter_clockwise_triggered(self):
        self.api.art.canvas.rotate_image_90_counterclockwise()

    @Slot()
    def on_actionClear_all_prompts_triggered(self):
        self.clear_all_prompts()

    @Slot()
    def on_actionBrowse_AI_Runner_Path_triggered(self):
        path = self.path_settings.base_path
        if path == "":
            path = AIRUNNER_BASE_PATH
        show_path(path)

    @Slot()
    def action_show_model_path_txt2img(self):
        self.show_settings_path("txt2img_model_path")

    @Slot()
    def action_show_model_path_inpaint(self):
        self.show_settings_path("inpaint_model_path")

    @Slot()
    def action_show_model_path_embeddings(self):
        self.show_settings_path("embeddings_model_path")

    @Slot()
    def action_show_model_path_lora(self):
        self.show_settings_path("lora_model_path")

    @Slot()
    def action_show_llm(self):
        pass

    @Slot()
    def on_actionReport_vulnerability_triggered(self):
        webbrowser.open(AIRUNNER_VULNERABILITY_REPORT_LINK)

    @Slot()
    def on_actionBug_report_triggered(self):
        webbrowser.open(AIRUNNER_BUG_REPORT_LINK)

    @Slot()
    def on_actionDiscord_triggered(self):
        if AIRUNNER_DISCORD_URL:
            webbrowser.open(AIRUNNER_DISCORD_URL)

    @Slot(bool)
    def action_toggle_mask_layer(self, val: bool):
        if val is True and self.drawing_pad_mask is None:
            self._generate_drawingpad_mask()
        self.update_drawing_pad_settings("mask_layer_enabled", val)
        self.api.art.canvas.mask_layer_toggled()

    @Slot(bool)
    def action_outpaint_toggled(self, val: bool):
        self.update_outpaint_settings("enabled", val)

    @Slot()
    def action_outpaint_export(self):
        pass

    @Slot()
    def action_outpaint_import(self):
        pass

    @Slot()
    def on_actionRun_setup_wizard_2_triggered(self):
        self.show_setup_wizard()

    @Slot(bool)
    def on_actionToggle_Stable_Diffusion_toggled(self, val: bool):
        self.on_toggle_sd({"enabled": val})

    @Slot()
    def on_actionSettings_triggered(self):
        SettingsWindow()

    @Slot()
    def on_actionBrowse_Images_Path_2_triggered(self):
        self.show_settings_path("image_path")

    @Slot()
    def on_actionPrompt_Browser_triggered(self):
        PromptBrowser()

    @Slot()
    def on_actionStats_triggered(self):
        widget = StatsWidget()
        # display in a window
        widget.show()

    @Slot(bool)
    def on_actionToggle_Active_Grid_Area_toggled(self, val: bool):
        self.toggle_tool(CanvasToolName.ACTIVE_GRID_AREA, val)

    @Slot(bool)
    def on_actionToggle_Brush_toggled(self, val: bool):
        self.toggle_tool(CanvasToolName.BRUSH, val)

    @Slot(bool)
    def on_actionToggle_Eraser_toggled(self, val: bool):
        self.toggle_tool(CanvasToolName.ERASER, val)

    @Slot(bool)
    def on_actionToggle_Grid_toggled(self, val: bool):
        self.update_grid_settings("show_grid", val)
        self.api.art.canvas.toggle_grid(val)

    @Slot(bool)
    def on_actionToggle_LLM_toggled(self, val: bool):
        self.on_toggle_llm(val=val)

    @Slot(bool)
    def on_actionSafety_Checker_toggled(self, val: bool):
        if val is False:
            self.show_nsfw_warning_popup()
        else:
            self.update_application_settings("nsfw_filter", val)
            self.toggle_nsfw_filter()
            self.api.art.load_safety_checker()

    @Slot(bool)
    def on_actionToggle_Speech_to_Text_toggled(self, val: bool):
        if self._model_status[ModelType.STT] is ModelStatus.LOADING:
            val = not val
        self._update_action_button(
            ModelType.STT,
            self.ui.actionToggle_Speech_to_Text,
            val,
            SignalCode.STT_LOAD_SIGNAL,
            SignalCode.STT_UNLOAD_SIGNAL,
            "stt_enabled",
        )
        QApplication.processEvents()
        self.update_application_settings("stt_enabled", val)

    @Slot()
    def on_workflow_actionClear_triggered(self):
        self.ui.graph.clear_graph()

    @Slot()
    def on_workflow_actionRun_triggered(self):
        self.ui.graph.run_workflow()

    @Slot()
    def on_workflow_actionEdit_triggered(self):
        self.ui.graph.edit_workflow()

    @Slot()
    def on_workflow_actionPause_triggered(self):
        self.ui.graph.pause_workflow()

    @Slot()
    def on_workflow_actionSave_triggered(self):
        self.ui.graph.save_workflow()

    @Slot()
    def on_workflow_actionStop_triggered(self):
        self.ui.graph.stop_workflow()

    @Slot()
    def on_workflow_actionOpen_triggered(self):
        self.ui.graph.load_workflow()

    @Slot(bool)
    def on_actionToggle_Text_to_Speech_toggled(self, val: bool):
        self.on_toggle_tts(val=val)

    @Slot()
    def on_actionAbout_triggered(self):
        AboutWindow()

    @Slot(bool)
    def on_actionToggle_Controlnet_toggled(self, val: bool):
        self.update_controlnet_settings("enabled", val)
        self._update_action_button(
            ModelType.CONTROLNET,
            self.ui.actionToggle_Controlnet,
            val,
            SignalCode.CONTROLNET_LOAD_SIGNAL,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL,
            "controlnet_enabled",
        )

    @Slot()
    def on_actionNew_Conversation_triggered(self):
        self.api.llm.clear_history()

    @Slot()
    def on_actionDelete_conversation_triggered(self):
        current_conversation = self.llm_generator_settings.current_conversation
        self.api.llm.converation_deleted(current_conversation.id)

    def _action_reset_settings(self):
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.reset_settings()
            self.restart()

    """
    End slot functions
    """

    @staticmethod
    def download_url(url, save_path):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.string if soup.title else url
        # Truncate title to 10 words
        title_words = title.split()[:10]
        filename = "_".join(title_words) + ".html"
        # Replace any characters in filename that are not alphanumerics, underscores, or hyphens
        filename = re.sub(r"[^\w\-_]", "_", filename)
        save_path = os.path.join(save_path, filename)
        with open(save_path, "wb") as file:
            file.write(response.content)
        return filename

    @staticmethod
    def download_pdf(url, save_path):
        response = requests.get(url)
        filename = url.split("/")[-1]  # Get the filename from the URL
        save_path = os.path.join(save_path, filename)
        with open(save_path, "wb") as file:
            file.write(response.content)
        return filename

    def initialize_system_tray(self):
        """Initialize the system tray icon with a simple menu."""
        here = os.path.dirname(os.path.abspath(__file__))
        self.setWindowIcon(
            QIcon(os.path.join(here, "../../gui/images/icon64x64.png"))
        )
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(
            QIcon(os.path.join(here, "../../images/icon64x64.png"))
        )

        # Create a simple tray menu with actions
        self.tray_menu = QMenu()
        self.toggle_visibility_action = QAction("Hide Window", self)
        quit_action = QAction("Quit Application", self)
        self.tray_menu.addAction(self.toggle_visibility_action)
        self.tray_menu.addAction(quit_action)

        # Connect actions
        self.toggle_visibility_action.triggered.connect(
            self.toggle_window_visibility
        )
        quit_action.triggered.connect(self.quit)

        # Set the menu for the tray icon
        self.tray_icon.setContextMenu(self.tray_menu)

        # Connect activated signal to our custom handler
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Show the tray icon
        self.tray_icon.show()

    def on_navigate_to_url(self, _data: Dict = None):
        url, ok = QInputDialog.getText(self, "Browse Web", "Enter your URL:")
        if ok:
            try:
                result = urllib.parse.urlparse(url)
                is_url = all([result.scheme, result.netloc])
            except ValueError:
                is_url = False

            # If the input is a URL, download it
            if is_url:
                if url.lower().endswith(".pdf"):
                    # Handle PDF file
                    filepath = os.path.expanduser(self.path_settings.pdf_path)
                    filename = self.download_pdf(url, filepath)
                else:
                    # Handle URL
                    filepath = os.path.expanduser(
                        self.path_settings.webpages_path
                    )
                    filename = self.download_url(url, filepath)
            elif os.path.isfile(url):
                filepath = os.path.dirname(url)
                filename = os.path.basename(url)
            else:
                self.logger.error(f"Invalid URL or file path")
                return

            # Update target files to use only the file that was downloaded or navigated to
            # and update the index.
            self.update_chatbot(
                "target_files", [os.path.join(filepath, filename)]
            )
            self.api.llm.reload_rag(self.chatbot.target_files)
            self.api.llm.send_request(
                action=LLMActionType.RAG,
                prompt="Summarize the text and provide a synopsis of the content. Be concise and informative.",
                llm_request=LLMRequest.from_default(),
            )

    def show_layers(self):
        self.api.art.canvas.show_layers()

    def on_reset_paths_signal(self):
        self.reset_path_settings()

    def restart(self):
        # Save the current state
        self.save_state()

        # Close the main window
        self.close()

        # Start a new instance of the application
        QProcess.startDetached(sys.executable, sys.argv)

    def toggle_window_visibility(self):
        """Toggle window visibility and update the menu text."""
        if self.isVisible():
            self.hide()
            self.toggle_visibility_action.setText("Show Window")
        else:
            self.showNormal()
            self.activateWindow()  # Ensure window gets focus when showing
            self.toggle_visibility_action.setText("Hide Window")

        # Update the tray menu so it reflects the current state immediately
        self.tray_icon.setContextMenu(self.tray_menu)

    def handle_single_click(self):
        """Handle single-click on the tray icon."""
        print("Single click handler executing")
        # Create a dropdown menu
        menu = QMenu()

        # Dynamically set the text based on current window visibility
        show_hide_text = "Hide Window" if self.isVisible() else "Show Window"
        show_action = QAction(show_hide_text, self)
        quit_action = QAction("Quit", self)

        # Connect actions to their respective slots
        show_action.triggered.connect(self.toggle_window_visibility)
        quit_action.triggered.connect(QApplication.quit)

        # Add actions to the menu
        menu.addAction(show_action)
        menu.addAction(quit_action)

        # Display the menu under the tray icon
        menu.exec(QCursor.pos())

    def handle_double_click(self):
        """Handle double-click on the tray icon."""
        print("Double click detected")
        self.toggle_window_visibility()  # Use toggle instead of just showing

    @staticmethod
    def on_write_file_signal(data: Dict):
        """
        Writes data to a file.
        :param data: Dict
        :return: None
        """
        args = data["args"]
        if len(args) == 1:
            message = args[0]
        else:
            message = args[1]
        with open("output.txt", "w") as f:
            f.write(message)

    @staticmethod
    def on_bash_execute_signal(data: Dict) -> str:
        """
        Takes a message from the LLM and strips bash commands from it.
        Passes bash command to the bash_execute function.
        :param data: Dict
        :return:
        """
        args = data["args"]
        return bash_execute(args[0])

    def on_theme_changed_signal(self):
        self.update_icons()
        self.set_stylesheet()

    def update_icons(self):
        theme = (
            "dark" if self.application_settings.dark_mode_enabled else "light"
        )
        self.icon_manager.update_icons(theme)

    def initialize_ui(self):
        self.logger.debug("Loading UI")

        self.ui.setupUi(self)

        self.icon_manager = IconManager(self.icons, self.ui)

        if not AIRUNNER_ART_ENABLED:
            self._disable_aiart_gui_elements()

        active_index = 0
        tab = Tab.objects.filter_by(section="center", active=True)
        if tab:
            print(tab)
            active_index = tab[0].index

        self.ui.center_tab_container.setCurrentIndex(active_index)
        # on tab change, track the Tab index on the Tab object
        self.ui.center_tab_container.currentChanged.connect(
            lambda index: self.update_tab_index(section="center", index=index)
        )

        self.set_stylesheet()

        load_splitter_settings(self.ui, ["main_window_splitter"])

        self.restore_state()

        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget)
        self.api.clear_status_message()
        self.initialize_widget_elements()
        self._load_plugins()
        self.api.main_window_loaded(self)

        if not AIRUNNER_DISCORD_URL:
            self.ui.actionDiscord.deleteLater()

        self.ui.actionCollapse_to_system_tray.setChecked(
            self.close_to_system_tray
        )

        self._toggle_agent_workflow_feature(self.enable_workflows)

    def update_tab_index(self, section: str, index: int):
        Tab.objects.update_by(filter=dict(section=section), active=False)
        Tab.objects.update_by(
            filter=dict(section=section, index=index), active=True
        )

    def _disable_aiart_gui_elements(self):
        self.ui.center_widget.hide()
        self.ui.menuImage.hide()
        self.ui.menuFilters.hide()
        self.ui.menuStable_Diffusion.hide()
        self.ui.menuArt.hide()

        self.ui.center_widget.deleteLater()
        self.ui.actionToggle_Stable_Diffusion.deleteLater()
        self.ui.actionToggle_Controlnet.deleteLater()
        self.ui.menuImage.deleteLater()
        self.ui.menuFilters.deleteLater()
        self.ui.menuStable_Diffusion.deleteLater()
        self.ui.actionBrowse_AI_Runner_Path.deleteLater()
        self.ui.actionBrowse_Images_Path_2.deleteLater()
        self.ui.actionArt.deleteLater()
        self.ui.menuArt.deleteLater()
        self.ui.actionCut.deleteLater()
        self.ui.actionCopy.deleteLater()
        self.ui.actionPaste.deleteLater()
        self.ui.actionRotate_90_clockwise.deleteLater()
        self.ui.actionRotate_90_counter_clockwise.deleteLater()
        self.ui.actionPrompt_Browser.deleteLater()

    def _load_plugins(self):
        base_path = self.path_settings.base_path
        path = os.path.join(base_path, "plugins")
        self.logger.info(f"Loading pluggins from {path}")
        plugin_loader = PluginLoader(plugin_dir=path)
        plugins = plugin_loader.load_plugins()

        if len(plugins) == 0:
            self.logger.info("No plugins found at " + path)
        else:
            self.logger.info("Loading plugins from " + path)
            for plugin in plugins:
                if hasattr(plugin, "get_widget"):
                    widget = plugin.get_widget()
                    self.ui.center_tab_container.addTab(widget, plugin.name)

    def initialize_widget_elements(self):
        for item in (
            (self.ui.actionToggle_LLM, self.application_settings.llm_enabled),
            (
                self.ui.actionToggle_Text_to_Speech,
                self.application_settings.tts_enabled,
            ),
            (
                self.ui.actionToggle_Speech_to_Text,
                self.application_settings.stt_enabled,
            ),
            (
                self.ui.actionToggle_Stable_Diffusion,
                self.application_settings.sd_enabled,
            ),
            (
                self.ui.actionToggle_Controlnet,
                self.application_settings.controlnet_enabled,
            ),
        ):
            item[0].blockSignals(True)
            item[0].setChecked(item[1] or False)
            item[0].blockSignals(False)
        self.initialized = True

    def layer_opacity_changed(self, _attr_name, value=None, _widget=None):
        self.api.art.canvas.layer_opacity_changed(value)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        for v in self.shortcut_keys:
            if v.key == event.key():
                for signal in SignalCode:
                    if signal.value == v.signal:
                        self.emit_signal(signal)
                        break

    def key_text(self, key_name):
        for shortcutkey in self.shortcut_keys:
            if shortcutkey.name == key_name:
                return shortcutkey.text
        return ""

    def on_save_stablediffusion_prompt_signal(self, data: Dict):
        self.create_saved_prompt(
            {
                "prompt": data["prompt"],
                "negative_prompt": data["negative_prompt"],
                "secondary_prompt": data["secondary_prompt"],
                "secondary_negative_prompt": data["secondary_negative_prompt"],
            }
        )

    def set_path_settings(self, key, val):
        self.update_path_settings(key, val)

    def on_nsfw_content_detected_signal(self):
        # display message in status
        self.api.application_error(AIRUNNER_NSFW_CONTENT_DETECTED_MESSAGE)

    def closeEvent(self, event):
        event.ignore()
        self.handle_close()

    def handle_close(self):
        """Override close to minimize to tray instead of exiting."""
        if self.close_to_system_tray:
            self.hide()
            # Update menu text when window is hidden
            self.toggle_visibility_action.setText("Show Window")

            # Update the tray menu so it reflects the current state immediately
            self.tray_icon.setContextMenu(self.tray_menu)

            self.tray_icon.showMessage(
                "AI Runner",
                "Application minimized to tray. Click the icon to restore.",
                QSystemTrayIcon.Information,
                2000,
            )
        else:
            self.quit()

    def quit(self):
        self.logger.debug("Quitting")
        self.save_state()
        self.api.quit_application()

    def handle_quit_application_signal(self):
        self.hide()
        QApplication.quit()
        self.close()

    def show_settings_path(self, name, default_path=None):
        path = getattr(self.path_settings, name)
        show_path(default_path if default_path and path == "" else path)

    def set_icons(self, icon_name, widget_name, theme):
        if not self.initialized:
            return

        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(f":/{theme}/icons/feather/{theme}/{icon_name}.svg"),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off,
        )
        getattr(self.ui, widget_name).setIcon(icon)
        self.update()

    def toggle_nsfw_filter(self):
        self.set_nsfw_filter_tooltip()

    def set_nsfw_filter_tooltip(self):
        self.ui.actionSafety_Checker.setToolTip(
            f"Click to {'enable' if not self.application_settings.nsfw_filter else 'disable'} NSFW filter"
        )

    def on_toggle_fullscreen_signal(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def on_unload_non_sd_models(self, data: Dict = None):
        if not self.memory_settings.prevent_unload_on_llm_image_generation:
            sd_device = (
                AIRUNNER_MEM_SD_DEVICE or self.memory_settings.default_gpu_sd
            )
            llm_device = (
                AIRUNNER_MEM_LLM_DEVICE or self.memory_settings.default_gpu_llm
            )
            tts_device = (
                AIRUNNER_MEM_TTS_DEVICE or self.memory_settings.default_gpu_tts
            )
            stt_device = (
                AIRUNNER_MEM_STT_DEVICE or self.memory_settings.default_gpu_stt
            )

            if sd_device == tts_device:
                self._tts_generator_worker.unload()

            if sd_device == stt_device:
                self._stt_audio_processor_worker.unload()

        callback = data.get("callback", None)
        if callback:
            callback()

    def on_load_non_sd_models(self, data: Dict = None):
        if self.application_settings.llm_enabled:
            self._llm_generate_worker.load()
        if self.application_settings.tts_enabled:
            self._tts_generator_worker.load()
        if self.application_settings.stt_enabled:
            self._stt_audio_processor_worker.load()
        callback = data.get("callback", None)
        if callback:
            callback(data)

    def on_toggle_llm(self, data: Dict = None, val=None):
        if val is None:
            val = not self.application_settings.llm_enabled
        self._update_action_button(
            ModelType.LLM,
            self.ui.actionToggle_LLM,
            val,
            SignalCode.LLM_LOAD_SIGNAL,
            SignalCode.LLM_UNLOAD_SIGNAL,
            "llm_enabled",
            data,
        )

    def on_toggle_sd(self, data: Dict):
        val = data.get("enabled", False)
        self._update_action_button(
            ModelType.SD,
            self.ui.actionToggle_Stable_Diffusion,
            val,
            SignalCode.SD_LOAD_SIGNAL,
            SignalCode.SD_UNLOAD_SIGNAL,
            "sd_enabled",
            data,
        )

    def on_toggle_tts(self, data: Dict = None, val=None):
        if val is None:
            val = data.get(
                "enabled", not self.application_settings.tts_enabled
            )
        self._update_action_button(
            ModelType.TTS,
            self.ui.actionToggle_Text_to_Speech,
            val,
            SignalCode.TTS_ENABLE_SIGNAL,
            SignalCode.TTS_DISABLE_SIGNAL,
            "tts_enabled",
            data,
        )

    def _update_action_button(
        self,
        model_type,
        element,
        val: bool,
        load_signal: SignalCode,
        unload_signal: SignalCode,
        application_setting: str = None,
        data: Dict = None,
    ):
        if self._model_status[model_type] is ModelStatus.LOADING:
            val = not val
        element.blockSignals(True)
        element.setChecked(val)
        element.blockSignals(False)
        QApplication.processEvents()
        if application_setting:
            self.update_application_settings(application_setting, val)
        if self._model_status[model_type] is not ModelStatus.LOADING:
            if val:
                self.emit_signal(load_signal, data)
            else:
                self.emit_signal(unload_signal, data)

    def save_state(self):
        if self.quitting:
            return
        self.quitting = True
        self.logger.debug("Saving window state")

        self.qsettings.beginGroup("window_settings")
        self.qsettings.setValue("is_maximized", self.isMaximized())
        self.qsettings.setValue("is_fullscreen", self.isFullScreen())
        self.qsettings.setValue("width", self.width())
        self.qsettings.setValue("height", self.height())
        self.qsettings.setValue("x_pos", self.pos().x())
        self.qsettings.setValue("y_pos", self.pos().y())
        self.qsettings.setValue(
            "mode_tab_widget_index",
            self.ui.generator_widget.ui.generator_form_tabs.currentIndex(),
        )
        self.qsettings.endGroup()
        save_splitter_settings(self.ui, ["main_window_splitter"])

    def restore_state(self):
        """
        Restore the window based on the previous state.
        """
        self.logger.debug("Restoring state")

        # Get the window settings
        settings = self.window_settings

        # Resize the window
        self.setMinimumSize(512, 512)
        width = int(settings["width"])
        height = int(settings["height"])
        self.resize(width, height)

        # Move the window
        x_pos = int(settings["x_pos"])
        y_pos = int(settings["y_pos"])
        self.move(x_pos, y_pos)

        # Show the window
        if settings is not None and settings.get("is_maximized", False):
            self.logger.info("Restoring window to maximized state")
            self.showMaximized()
        elif settings is not None and settings.get("is_fullscreen", False):
            self.logger.info("Restoring window to fullscreen state")
            self.showFullScreen()
        else:
            self.logger.info("Restoring window to normal state")
            self.showNormal()

        # Raise the window to the top of the stack
        self.raise_()

    ##### End window properties #####
    #################################

    ###### Window handlers ######
    def on_toggle_tool_signal(self, data: Dict):
        self.toggle_tool(data["tool"], data["active"])

    def on_enable_workflows_toggled(self, message: Dict):
        self._toggle_agent_workflow_feature(message.get("enabled", False))

    tab_backup = {}
    workflow_tab = None

    def _toggle_agent_workflow_feature(self, enabled: bool):
        """
        Toggles the visibility of the workflow tab and menu based on the given value.
        """
        # --- Tab handling ---
        tab_widget = self.ui.center_tab_container
        if not self.workflow_tab:
            self.workflow_tab = self.ui.agent_workflow_tab

        if enabled:
            # Only add if not present
            if self.tab_backup != {}:
                tab_widget.addTab(
                    self.tab_backup["tab_widget"],
                    self.tab_backup["tab_text"],
                )
                self.tab_backup = {}
        else:
            # Remove if present
            index = tab_widget.indexOf(self.workflow_tab)
            self.tab_backup = dict(
                tab_text=tab_widget.tabText(index),
                tab_widget=tab_widget.widget(index),
            )
            if index != -1:
                tab_widget.removeTab(index)

        # --- Menu handling ---
        # If menuWorkflow is a QMenu, use menuBar(). If it's an action, use setVisible.
        if hasattr(self.ui, "menuWorkflow"):
            menu = self.ui.menuWorkflow
            # Try both methods for robustness
            try:
                menu.menuAction().setVisible(enabled)
            except Exception:
                try:
                    menu.setVisible(enabled)
                except Exception:
                    pass

    def show_nsfw_warning_popup(self):
        if self.application_settings.show_nsfw_warning:
            """
            Display a popup window which asks the user if they are sure they want to disable the NSFW filter
            along with a checkbox that allows the user to disable the warning in the future.
            """
            msg_box = QMessageBox()
            msg_box.setWindowTitle("Disable Safety Checker Warning")
            msg_box.setText(
                (
                    "WARNING\n\n"
                    "You are attempting to disable the safety checker (NSFW filter).\n"
                    "It is strongly recommended that you keep this enabled at all times.\n"
                    "The Safety Checker prevents potentially harmful content from being displayed.\n"
                    "Only disable it if you are sure the Image model you are using is not capable of generating "
                    "harmful content.\n"
                    "Disabling the safety checker is intended as a last resort for continual false positives and as a "
                    "research feature.\n"
                    "\n\n"
                    "Are you sure you want to disable the filter?"
                )
            )
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)

            # Create a QCheckBox
            checkbox = QCheckBox("Do not show this warning again")
            # Add the checkbox to the message box
            msg_box.setCheckBox(checkbox)

            result = msg_box.exec()

            if result == QMessageBox.StandardButton.Yes:
                self._disable_nsfw_filter(not checkbox.isChecked())

            self.ui.actionSafety_Checker.blockSignals(True)
            self.ui.actionSafety_Checker.setChecked(
                self.application_settings.nsfw_filter
            )
            self.ui.actionSafety_Checker.blockSignals(False)
        else:
            self._disable_nsfw_filter()

    def _disable_nsfw_filter(self, show_nsfw_warning=None):
        """
        Do not call this function directly.
        :return:
        """
        # User confirmed to disable the NSFW filter
        # Update the settings accordingly
        self.update_application_settings("nsfw_filter", False)
        # Update the show_nsfw_warning setting based on the checkbox state
        if show_nsfw_warning is not None:
            self.update_application_settings(
                "show_nsfw_warning", show_nsfw_warning
            )
        self.toggle_nsfw_filter()
        self.api.art.unload_safety_checker()

    ###### End window handlers ######

    def show_update_message(self):
        self.api.application_status(
            f"New version available: {self.latest_version}"
        )

    def show_update_popup(self):
        self.update_popup = UpdateWindow()

    @staticmethod
    def show_setup_wizard():
        AppInstaller(close_on_cancel=False)

    def showEvent(self, event):
        """Override to update the tray menu text when window is shown."""
        super().showEvent(event)
        # Make sure we update the menu text whenever the window is shown
        if hasattr(self, "toggle_visibility_action"):
            self.toggle_visibility_action.setText("Hide Window")
            # Update the tray menu so it reflects the current state immediately
            self.tray_icon.setContextMenu(self.tray_menu)

        self.logger.debug("showEvent called, initializing window")
        self._initialize_window()
        self._initialize_default_buttons()
        self._initialize_filter_actions()
        self.initialized = True
        self.update_icons()
        self.logger.debug("Showing window")
        self._set_keyboard_shortcuts()

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def _set_keyboard_shortcuts(self):
        quit_key = ShortcutKeys.objects.filter_by_first(display_name="Quit")
        brush_key = ShortcutKeys.objects.filter_by_first(display_name="Brush")
        eraser_key = ShortcutKeys.objects.filter_by_first(
            display_name="Eraser"
        )
        move_tool_key = ShortcutKeys.objects.filter_by_first(
            display_name="Move Tool"
        )

        if quit_key is not None:
            key_sequence = QKeySequence(quit_key.key | quit_key.modifiers)
            self.ui.actionQuit.setShortcut(key_sequence)
            self.ui.actionQuit.setToolTip(
                f"{quit_key.display_name} ({quit_key.text})"
            )

        if brush_key is not None:
            key_sequence = QKeySequence(brush_key.key | brush_key.modifiers)
            self.ui.actionToggle_Brush.setShortcut(key_sequence)
            self.ui.actionToggle_Brush.setToolTip(
                f"{brush_key.display_name} ({brush_key.text})"
            )

        if eraser_key is not None:
            key_sequence = QKeySequence(eraser_key.key | eraser_key.modifiers)
            self.ui.actionToggle_Eraser.setShortcut(key_sequence)
            self.ui.actionToggle_Eraser.setToolTip(
                f"{eraser_key.display_name} ({eraser_key.text})"
            )

        if move_tool_key is not None:
            key_sequence = QKeySequence(
                move_tool_key.key | move_tool_key.modifiers
            )
            self.ui.actionToggle_Active_Grid_Area.setShortcut(key_sequence)
            self.ui.actionToggle_Active_Grid_Area.setToolTip(
                f"{move_tool_key.display_name} ({move_tool_key.text})"
            )

    def _initialize_workers(self):
        self.logger.debug("Initializing worker manager")
        self.logger.info("imported workers, initializing")
        self._mask_generator_worker = create_worker(MaskGeneratorWorker)
        self._sd_worker = create_worker(SDWorker)
        if AudioCaptureWorker is not None:
            self._stt_audio_capture_worker = create_worker(AudioCaptureWorker)
        if AudioProcessorWorker is not None:
            self._stt_audio_processor_worker = create_worker(
                AudioProcessorWorker
            )
        if TTSGeneratorWorker is not None:
            self._tts_generator_worker = create_worker(TTSGeneratorWorker)
        if TTSVocalizerWorker is not None:
            self._tts_vocalizer_worker = create_worker(TTSVocalizerWorker)
        self._llm_generate_worker = create_worker(LLMGenerateWorker)

        self.logger.info("INITIALIZE WORKERS COMPLETE")

    def _initialize_filter_actions(self):
        image_filters = ImageFilter.objects.all()
        try:
            for image_filter in image_filters:
                action = self.ui.menuFilters.addAction(
                    image_filter.display_name
                )
                action.triggered.connect(
                    partial(self.display_filter_window, image_filter)
                )
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.warning(f"Error setting SD status text: {e}")

    @staticmethod
    def display_filter_window(image_filter):
        FilterWindow(image_filter.id)

    def _initialize_default_buttons(self):
        self.ui.actionSafety_Checker.blockSignals(True)
        self.ui.actionSafety_Checker.setChecked(
            self.application_settings.nsfw_filter
        )
        self.ui.actionSafety_Checker.blockSignals(False)

    def toggle_tool(self, tool: CanvasToolName, active: bool):
        self.update_application_settings("current_tool", tool.value)
        self.api.art.canvas.tool_changed(tool, active)

    def _initialize_window(self):
        self.center()
        self.set_window_title()

    def center(self):
        available_geometry = (
            QGuiApplication.primaryScreen().availableGeometry()
        )
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(available_geometry.center())
        self.move(frame_geometry.topLeft())

    def set_window_title(self):
        """
        Overrides base method to set the window title
        :return:
        """
        self.setWindowTitle(self._window_title)

    def handle_unknown(self, message):
        self.logger.error(f"Unknown message code: {message}")

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        self.api.clear_prompts()

    def new_batch(self, index, image, data):
        self.generator_tab_widget.new_batch(index, image, data)

    def on_model_status_changed_signal(self, data):
        model = data["model"]
        status = data["status"]
        if self._model_status[model] is status:
            return
        self._model_status[model] = status
        if model is ModelType.SD:
            self.ui.actionToggle_Stable_Diffusion.setDisabled(
                status is ModelStatus.LOADING
            )
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Stable_Diffusion.setChecked(False)
        elif model is ModelType.CONTROLNET:
            self.ui.actionToggle_Controlnet.setDisabled(
                status is ModelStatus.LOADING
            )
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Controlnet.setChecked(False)
        elif model is ModelType.LLM:
            self.ui.actionToggle_LLM.setDisabled(status is ModelStatus.LOADING)
            if status is ModelStatus.FAILED:
                self.logger.warning("LLM failed to load")
                self.ui.actionToggle_LLM.setChecked(False)
        elif model is ModelType.TTS:
            self.ui.actionToggle_Text_to_Speech.setDisabled(
                status is ModelStatus.LOADING
            )
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Text_to_Speech.setChecked(False)
        elif model is ModelType.STT:
            self.ui.actionToggle_Speech_to_Text.setDisabled(
                status is ModelStatus.LOADING
            )
            if status is ModelStatus.FAILED:
                self.ui.actionToggle_Speech_to_Text.setChecked(False)
        self.initialize_widget_elements()
        QApplication.processEvents()

    def _generate_drawingpad_mask(self):
        width = self.application_settings.working_width
        height = self.application_settings.working_height
        img = Image.new("RGB", (width, height), (0, 0, 0))
        base64_image = convert_image_to_binary(img)

        drawing_pad_settings = DrawingPadSettings.objects.first()
        drawing_pad_settings.mask = base64_image
        drawing_pad_settings.save()

    def display_missing_models_error(self, data):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(data.get("title", "Error: Missing models"))
        msg_box.setText(data.get("message", "Something went wrong"))
        msg_box.exec()
