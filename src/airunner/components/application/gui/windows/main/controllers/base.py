"""Shared constants and small helpers for the decomposed MainWindow."""

from __future__ import annotations

from airunner.enums import ModelType


class MainWindowBase:
    """Shared layout constants and tiny helpers used by the controllers.

    These were previously class attributes and ``@staticmethod`` helpers on the
    3,244-line ``MainWindow``. They live here so each per-concern controller
    can reference them without re-declaring them.
    """

    _window_title = "AI Runner"
    _daemon_status_request_timeout_seconds = 0.75
    _runtime_preference_retry_seconds = 5.0
    _documents_splitter_index = 0
    _chat_splitter_index = 1
    _center_splitter_index = 2
    _stats_splitter_index = 3
    _canvas_panel_index = 0
    _prompt_panel_index = 1
    _left_panel_target_width = 360
    _chat_panel_target_width = 250
    _stats_sidebar_index = 0
    _art_tools_sidebar_index = 1
    _art_tools_model_tab_index = 0
    _art_tools_lora_tab_index = 1
    _art_tools_embeddings_tab_index = 2
    _art_tools_layers_tab_index = 3
    _art_tools_grid_tab_index = 4
    _art_tools_image_browser_tab_index = 5
    _left_documents_panel_index = 0
    _left_history_panel_index = 1
    _left_llm_settings_panel_index = 2
    _last_reload_time = 0
    _reload_debounce_seconds = 1.0

    icons = [
        ("settings", "actionSettings"),
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
        ("delete", "actionClear_all_prompts"),
        ("settings", "actionSettings"),
        ("book-open", "actionPrompt_Browser"),
        ("folder", "actionBrowse_AI_Runner_Path"),
        ("folder", "actionBrowse_Images_Path_2"),
        ("image", "menuStable_Diffusion"),
        ("edit-3", "actionPrompt_Builder"),
        ("zap", "actionRun_setup_wizard_2"),
        ("external-link", "actionBug_report"),
        ("external-link", "actionReport_vulnerability"),
        ("message-square", "actionDiscussions"),
        ("download", "actionImport_image"),
        ("upload", "actionExport_image_button"),
        ("settings", "settings_button"),
        ("message-square-text", "chat_button"),
        ("speaker", "text_to_speech_button"),
        ("mic", "speech_to_text_button"),
        ("arrow-down-circle", "actionDownload_Model"),
        ("book", "knowledgebase_button"),
        ("history", "history_sidebar_button"),
        ("settings-2", "llm_settings_sidebar_button"),
        ("message-square-heart", "prompt_editor_button"),
        ("sparkles", "art_model_button"),
        ("activity", "stats_button"),
        ("image", "canvas_button"),
        ("puzzle", "lora_button"),
        ("scan-text", "embeddings_button"),
        ("layers", "layers_button"),
        ("grid-2x2-check", "grid_button"),
        ("images", "image_browser_button"),
    ]

    @staticmethod
    def _set_action_checked_state(action, checked: bool) -> None:
        """Update one toggle without re-triggering its signal."""
        action.blockSignals(True)
        action.setChecked(checked)
        action.blockSignals(False)

    @staticmethod
    def _allows_loading_toggle(model_type: ModelType) -> bool:
        """Return True when a loading toggle may still change preference."""
        return model_type in (ModelType.TTS, ModelType.STT)

    @staticmethod
    def _modifier_value(modifiers: object) -> int:
        """Return a stable integer value for Qt keyboard modifiers."""
        if modifiers is None:
            return 0
        value = getattr(modifiers, "value", modifiers)
        if isinstance(value, int):
            return value
        return 0
