"""Menu/action slots for MainWindow."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMessageBox

from airunner.components.about.gui.windows.about.about import AboutWindow
from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.application.gui.windows.main.controllers.menu_controller import (
    MenuController,
)
from airunner.components.application.gui.windows.main.download_model_dialog import (
    show_download_model_dialog,
)
from airunner.components.application.gui.windows.main.nsfw_warning_dialog import (
    show_nsfw_warning_dialog,
)
from airunner.components.art.gui.windows.prompt_browser.prompt_browser import (
    PromptBrowser,
)
from airunner.enums import ModelStatus, ModelType, SignalCode
from airunner.utils.settings import get_qsettings
from airunner_common.settings import (
    AIRUNNER_BUG_REPORT_LINK,
    AIRUNNER_DISCUSSIONS_URL,
    AIRUNNER_VULNERABILITY_REPORT_LINK,
)


class ActionController(MenuController):
    """Auto-connected action slots for menus, tools, and downloads."""

    @Slot()
    def on_actionQuit_triggered(self):
        self.handle_close()

    @Slot()
    def on_actionReset_Settings_2_triggered(self):
        self._action_reset_settings()

    @Slot()
    def on_actionExport_image_button_triggered(self):
        if not self._has_art_canvas("Cannot export image."):
            return
        self.api.art.canvas.export_image()

    @Slot()
    def on_actionImport_image_triggered(self):
        if not self._has_art_canvas("Cannot import image."):
            return
        self.api.art.canvas.import_image()

    @Slot()
    def on_artActionNew_triggered(self):
        self._ensure_canvas_loaded()
        canvas = getattr(self, "canvas", None)
        if canvas is None or not hasattr(canvas, "start_new_document_flow"):
            self.logger.warning(
                "MainWindow: canvas widget is missing. Cannot create a new document."
            )
            return
        canvas.start_new_document_flow()

    @Slot()
    def on_actionCopy_triggered(self):
        if not self._has_art_canvas("Cannot copy image."):
            return
        self.api.art.canvas.copy_image()

    @Slot()
    def on_actionClear_all_prompts_triggered(self):
        self.clear_all_prompts()

    @Slot()
    def on_actionBrowse_AI_Runner_Path_triggered(self):
        pass

    @Slot()
    def on_actionDownload_Model_triggered(self):
        show_download_model_dialog(
            self, self.path_settings, self.application_settings
        )

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
    def on_actionDiscussions_triggered(self):
        if AIRUNNER_DISCUSSIONS_URL:
            webbrowser.open(AIRUNNER_DISCUSSIONS_URL)

    @Slot(bool)
    def action_outpaint_toggled(self, val: bool):
        self.update_outpaint_settings(enabled=val)

    @Slot()
    def action_outpaint_export(self):
        pass

    @Slot()
    def action_outpaint_import(self):
        pass

    @Slot()
    def on_actionRun_setup_wizard_2_triggered(self):
        self.show_setup_wizard()

    @Slot()
    def on_actionSettings_triggered(self):
        self._show_settings_window()

    @Slot()
    def on_actionBrowse_Images_Path_2_triggered(self):
        self.show_settings_path("image_path")

    @Slot()
    def on_actionPrompt_Browser_triggered(self):
        PromptBrowser()

    @Slot(bool)
    def on_speech_to_text_button_toggled(self, val: bool):
        if self._model_status[ModelType.STT] is ModelStatus.LOADING:
            val = not val
        self._update_action_button(
            ModelType.STT,
            getattr(self.ui, "speech_to_text_button", None),
            val,
            SignalCode.STT_LOAD_SIGNAL,
            SignalCode.STT_UNLOAD_SIGNAL,
            "stt_enabled",
        )

    @Slot(bool)
    def on_text_to_speech_button_toggled(self, val: bool):
        self.on_toggle_tts(val=val)

    @Slot(bool)
    def on_actionSafety_Checker_toggled(self, val: bool):
        """Handle safety checker toggle action."""
        if not val and not self._confirm_safety_checker_disabled():
            return
        self.update_application_settings(nsfw_filter=val)
        self.set_nsfw_filter_tooltip()
        if val:
            self.emit_signal(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, {})
        else:
            self.emit_signal(SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, {})

    def _confirm_safety_checker_disabled(self) -> bool:
        """Confirm disabling the safety checker, honoring hide preference."""
        settings = get_qsettings()
        show_warning = settings.value("nsfw_warning/show_again", True, type=bool)
        if not show_warning:
            return True
        confirmed, do_not_show_again = show_nsfw_warning_dialog(
            self, show_again_default=bool(show_warning)
        )
        if do_not_show_again:
            settings.setValue("nsfw_warning/show_again", False)
        if not confirmed and hasattr(self.ui, "actionSafety_Checker"):
            self.ui.actionSafety_Checker.blockSignals(True)
            self.ui.actionSafety_Checker.setChecked(True)
            self.ui.actionSafety_Checker.blockSignals(False)
        return confirmed

    def set_nsfw_filter_tooltip(self):
        """Update the safety checker button tooltip based on current state."""
        nsfw_filter = self.application_settings.nsfw_filter
        if hasattr(self.ui, "actionSafety_Checker"):
            self.ui.actionSafety_Checker.setToolTip(
                f"Click to {'enable' if not nsfw_filter else 'disable'} NSFW filter"
            )

    @Slot()
    def on_actionAbout_triggered(self):
        AboutWindow()

    @Slot()
    def on_actionNew_Conversation_triggered(self):
        if not self.api or not hasattr(self.api, "llm"):
            self.logger.warning(
                "MainWindow: self.api.llm is missing. Cannot clear LLM history."
            )
            return
        self.api.llm.clear_history()

    @Slot()
    def on_actionDelete_conversation_triggered(self):
        if not self.api or not hasattr(self.api, "llm"):
            self.logger.warning(
                "MainWindow: self.api.llm is missing. Cannot delete conversation."
            )
            return
        current_conversation = self.llm_generator_settings.current_conversation
        self.api.llm.converation_deleted(current_conversation.id)

    @Slot(bool)
    def on_settings_button_clicked(self, val: bool):
        del val
        self._show_settings_window()

    def _has_art_canvas(self, message: str) -> bool:
        """Return True when the API exposes an art canvas controller."""
        if (
            not self.api
            or not hasattr(self.api, "art")
            or not hasattr(self.api.art, "canvas")
        ):
            self.logger.warning(f"MainWindow: self.api.art.canvas is missing. {message}")
            return False
        return True
