"""Toggle, splitter, and deferred-startup signal handlers for MainWindow."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Slot

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)


class PanelToggleController(MainWindowBase):
    """Auto-connected panel toggle slots and deferred-startup handlers."""

    @Slot(bool)
    def on_chat_button_toggled(self, val: bool):
        self._toggle_splitter_section(
            val,
            self._chat_splitter_index,
            self.ui.main_window_splitter,
            50,
        )

    @Slot(bool)
    def on_knowledgebase_button_toggled(self, val: bool):
        self._toggle_left_panel_page(self._left_documents_panel_index, val)

    @Slot(bool)
    def on_history_sidebar_button_toggled(self, val: bool):
        self._toggle_left_panel_page(self._left_history_panel_index, val)

    @Slot(bool)
    def on_llm_settings_sidebar_button_toggled(self, val: bool):
        self._toggle_left_panel_page(self._left_llm_settings_panel_index, val)

    @Slot(bool)
    def on_canvas_button_toggled(self, val: bool):
        self._toggle_canvas_panel(val)

    @Slot(bool)
    def on_prompt_editor_button_toggled(self, val: bool):
        self._toggle_prompt_panel(val)

    @Slot(bool)
    def on_art_model_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_model_tab_index, val)

    @Slot(bool)
    def on_lora_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_lora_tab_index, val)

    @Slot(bool)
    def on_embeddings_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_embeddings_tab_index, val)

    @Slot(bool)
    def on_layers_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_layers_tab_index, val)

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(self._art_tools_grid_tab_index, val)

    @Slot(bool)
    def on_image_browser_button_toggled(self, val: bool):
        self._toggle_art_tools_tab(
            self._art_tools_image_browser_tab_index,
            val,
        )

    @Slot(bool)
    def on_stats_button_toggled(self, val: bool):
        self._toggle_sidebar_page(self._stats_sidebar_index, val)

    def on_main_window_loaded_signal(self, _data=None) -> None:
        """Restore deferred startup UI once the main window is visible."""
        self._ensure_canvas_loaded()
        if self._prompt_panel_is_visible():
            self._ensure_art_prompt_loaded()
        self._restore_deferred_panel_pages()
        self._schedule_lazy_panel_prewarm()
        if self._post_startup_status_refresh_requested:
            return
        self._post_startup_status_refresh_requested = True
        self._refresh_model_status_from_daemon()

    def _restore_deferred_panel_pages(self) -> None:
        """Restore the left/sidebar pages deferred until startup."""
        if self._restore_left_panel_page_after_startup is not None:
            page_index = int(self._restore_left_panel_page_after_startup)
            self._restore_left_panel_page_after_startup = None
            self._ensure_left_panel_page_loaded(page_index)
            self.ui.left_panel_tab.setCurrentIndex(page_index)
            self._sync_left_panel_button_states()

        if self._restore_sidebar_page_after_startup is not None:
            page_index = int(self._restore_sidebar_page_after_startup)
            self._restore_sidebar_page_after_startup = None
            self._ensure_sidebar_page_loaded(page_index)
            self.ui.sidebar_tab.setCurrentIndex(page_index)
            self._sync_sidebar_button_states()

    def _schedule_lazy_panel_prewarm(self) -> None:
        """Preload slow panel widgets after the window becomes interactive."""
        if getattr(self, "_lazy_panel_prewarm_scheduled", False):
            return
        self._lazy_panel_prewarm_scheduled = True
        QTimer.singleShot(0, self._prewarm_history_panel)

    def _prewarm_history_panel(self) -> None:
        """Build the history panel outside the first-click path."""
        try:
            widget = self._ensure_left_history_loaded()
            preload = getattr(widget, "preload_content", None)
            if callable(preload):
                preload()
        except Exception:
            self.logger.exception("Failed to prewarm history panel")

    def _schedule_main_window_loaded_signal(self) -> None:
        """Schedule the post-startup signal once after the window is shown."""
        if getattr(self, "_main_window_loaded_signal_scheduled", False):
            return
        self._main_window_loaded_signal_scheduled = True
        QTimer.singleShot(0, self._emit_main_window_loaded_signal_if_ready)

    def _emit_main_window_loaded_signal_if_ready(self) -> None:
        """Emit the post-startup signal when a live API is available."""
        if getattr(self, "_main_window_loaded_signal_emitted", False):
            return
        api = getattr(self, "api", None) or self.refresh_api_reference()
        if api is None:
            self._main_window_loaded_signal_scheduled = False
            return
        self._main_window_loaded_signal_emitted = True
        api.main_window_loaded(self)

    def on_splitter_changed_sizes(self):
        if self._sidebar_is_visible():
            self._ensure_sidebar_page_loaded(self._current_sidebar_index())
        if self._prompt_panel_is_visible():
            self._ensure_art_prompt_loaded()
        if self._left_panel_is_visible():
            self._ensure_left_panel_page_loaded(
                self.ui.left_panel_tab.currentIndex()
            )
        self.set_chat_button_checked()
        self._sync_left_panel_button_states()
        self._sync_sidebar_button_states()
        canvas = getattr(self, "canvas", None)
        refresh_layout = getattr(canvas, "refresh_layout_after_host_resize", None)
        if callable(refresh_layout):
            refresh_layout()

    def on_left_panel_tab_current_changed(self, index: int) -> None:
        """Persist the active left panel page and refresh toggle state."""
        self._ensure_left_panel_page_loaded(index)
        self._store_active_left_panel_tab_index(index)
        self._sync_left_panel_button_states()

    def on_sidebar_tab_current_changed(self, index: int) -> None:
        """Persist the active sidebar page and refresh toggle state."""
        self._ensure_sidebar_page_loaded(index)
        self._store_active_sidebar_tab_index(index)
        self._sync_sidebar_button_states()
