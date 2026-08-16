"""Panel visibility, index, and button-state helpers for MainWindow."""

from __future__ import annotations

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)


class PanelStateController(MainWindowBase):
    """Read/persist panel layout state and sync toggle-button states."""

    def _sidebar_is_visible(self) -> bool:
        """Return True when the right sidebar splitter area is visible."""
        sizes = self.ui.main_window_splitter.sizes()
        return len(sizes) > self._stats_splitter_index and (
            sizes[self._stats_splitter_index] > 0
        )

    def _center_section_is_visible(self) -> bool:
        """Return True when the shared center splitter area is visible."""
        sizes = self.ui.main_window_splitter.sizes()
        return len(sizes) > self._center_splitter_index and (
            sizes[self._center_splitter_index] > 0
        )

    def _canvas_panel_is_visible(self) -> bool:
        """Return True when the canvas panel is visible."""
        splitter = getattr(self.ui, "center_splitter", None)
        if splitter is None or not self._center_section_is_visible():
            return False
        sizes = splitter.sizes()
        return len(sizes) > self._canvas_panel_index and (
            sizes[self._canvas_panel_index] > 0
        )

    def _prompt_panel_is_visible(self) -> bool:
        """Return True when the prompt panel is visible."""
        splitter = getattr(self.ui, "center_splitter", None)
        if splitter is None or not self._center_section_is_visible():
            return False
        sizes = splitter.sizes()
        return len(sizes) > self._prompt_panel_index and (
            sizes[self._prompt_panel_index] > 0
        )

    def _knowledgebase_panel_is_visible(self) -> bool:
        """Return True when the left documents splitter area is visible."""
        return self._left_panel_is_visible()

    def _left_panel_is_visible(self) -> bool:
        """Return True when the shared left splitter area is visible."""
        sizes = self.ui.main_window_splitter.sizes()
        return len(sizes) > self._documents_splitter_index and (
            sizes[self._documents_splitter_index] > 0
        )

    def _current_left_panel_index(self) -> int:
        """Return the active left panel page index."""
        tab_widget = getattr(self.ui, "left_panel_tab", None)
        if tab_widget is None:
            return self._left_documents_panel_index
        return tab_widget.currentIndex()

    def _current_sidebar_index(self) -> int:
        """Return the active right panel page index."""
        tab_widget = getattr(self.ui, "sidebar_tab", None)
        if tab_widget is None:
            return self._stats_sidebar_index
        return tab_widget.currentIndex()

    def _saved_left_panel_tab_index(self) -> int:
        """Return the persisted left panel page index."""
        self.qsettings.beginGroup("window_settings")
        index = self.qsettings.value(
            "active_left_panel_tab_index",
            self._left_documents_panel_index,
            type=int,
        )
        self.qsettings.endGroup()
        if isinstance(index, int):
            return index
        return self._left_documents_panel_index

    def _saved_sidebar_tab_index(self) -> int:
        """Return the persisted sidebar page index."""
        self.qsettings.beginGroup("window_settings")
        index = self.qsettings.value(
            "active_sidebar_tab_index",
            self._stats_sidebar_index,
            type=int,
        )
        self.qsettings.endGroup()
        if not isinstance(index, int):
            return self._stats_sidebar_index
        return max(
            self._stats_sidebar_index,
            min(index, self._art_tools_sidebar_index),
        )

    def _clamp_art_tools_tab_index(self, index: int) -> int:
        """Clamp the nested art-tools tab index to the supported range."""
        return max(
            self._art_tools_model_tab_index,
            min(index, self._art_tools_image_browser_tab_index),
        )

    def _saved_art_tools_tab_index(self) -> int:
        """Return the persisted nested art-tools tab index."""
        index = self.qsettings.value(
            "tabs/stablediffusion_tool_tab/active_index",
            self._art_tools_model_tab_index,
            type=int,
        )
        if not isinstance(index, int):
            return self._art_tools_model_tab_index
        return self._clamp_art_tools_tab_index(index)

    def _current_art_tools_tab_index(self) -> int:
        """Return the active nested tab inside the art tools sidebar."""
        widget = getattr(self.ui, "art_tools_widget", None)
        if widget is None:
            return self._saved_art_tools_tab_index()

        current_index = getattr(widget, "current_tool_page_index", None)
        if callable(current_index):
            value = current_index()
            if isinstance(value, int):
                return self._clamp_art_tools_tab_index(value)
            return self._saved_art_tools_tab_index()

        tab_widget = getattr(
            getattr(widget, "ui", None),
            "tool_tab_widget_container",
            None,
        )
        if tab_widget is None:
            return self._saved_art_tools_tab_index()
        return self._clamp_art_tools_tab_index(tab_widget.currentIndex())

    def _store_active_left_panel_tab_index(self, index: int) -> None:
        """Persist the current left panel page index."""
        self.qsettings.beginGroup("window_settings")
        self.qsettings.setValue("active_left_panel_tab_index", int(index))
        self.qsettings.endGroup()
        self.qsettings.sync()

    def _store_active_sidebar_tab_index(self, index: int) -> None:
        """Persist the current sidebar page index."""
        self.qsettings.beginGroup("window_settings")
        self.qsettings.setValue("active_sidebar_tab_index", int(index))
        self.qsettings.endGroup()
        self.qsettings.sync()

    def _sync_left_panel_button_states(self) -> None:
        """Update left-panel toggle buttons from current panel state."""
        self.set_knowledgebase_button_checked()
        self.set_history_sidebar_button_checked()
        self.set_llm_settings_sidebar_button_checked()

    def _sync_sidebar_button_states(self) -> None:
        """Update the canvas and sidebar toggle buttons from panel state."""
        self.set_canvas_button_checked()
        self.set_prompt_editor_button_checked()
        self.set_art_model_button_checked()
        self.set_lora_button_checked()
        self.set_embeddings_button_checked()
        self.set_layers_button_checked()
        self.set_grid_button_checked()
        self.set_image_browser_button_checked()
        self.set_stats_button_checked()

    def set_chat_button_checked(self):
        self.ui.chat_button.blockSignals(True)
        self.ui.chat_button.setChecked(
            len(self.ui.main_window_splitter.sizes())
            > self._chat_splitter_index
            and self.ui.main_window_splitter.sizes()[
                self._chat_splitter_index
            ]
            > 0
        )
        self.ui.chat_button.blockSignals(False)

    def set_knowledgebase_button_checked(self):
        self.ui.knowledgebase_button.blockSignals(True)
        self.ui.knowledgebase_button.setChecked(
            self._left_panel_is_visible()
            and self._current_left_panel_index()
            == self._left_documents_panel_index
        )
        self.ui.knowledgebase_button.blockSignals(False)

    def set_canvas_button_checked(self):
        button = getattr(self.ui, "canvas_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(self._canvas_panel_is_visible())
        button.blockSignals(False)

    def set_history_sidebar_button_checked(self):
        button = getattr(self.ui, "history_sidebar_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(
            self._left_panel_is_visible()
            and self._current_left_panel_index()
            == self._left_history_panel_index
        )
        button.blockSignals(False)

    def set_llm_settings_sidebar_button_checked(self):
        button = getattr(self.ui, "llm_settings_sidebar_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(
            self._left_panel_is_visible()
            and self._current_left_panel_index()
            == self._left_llm_settings_panel_index
        )
        button.blockSignals(False)

    def set_prompt_editor_button_checked(self):
        button = getattr(self.ui, "prompt_editor_button", None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(self._prompt_panel_is_visible())
        button.blockSignals(False)

    def set_art_model_button_checked(self):
        self._set_art_tools_button_checked(
            "art_model_button", self._art_tools_model_tab_index
        )

    def set_lora_button_checked(self):
        self._set_art_tools_button_checked(
            "lora_button", self._art_tools_lora_tab_index
        )

    def set_embeddings_button_checked(self):
        self._set_art_tools_button_checked(
            "embeddings_button", self._art_tools_embeddings_tab_index
        )

    def set_layers_button_checked(self):
        self._set_art_tools_button_checked(
            "layers_button", self._art_tools_layers_tab_index
        )

    def set_grid_button_checked(self):
        self._set_art_tools_button_checked(
            "grid_button", self._art_tools_grid_tab_index
        )

    def set_image_browser_button_checked(self):
        self._set_art_tools_button_checked(
            "image_browser_button", self._art_tools_image_browser_tab_index
        )

    def _set_art_tools_button_checked(
        self,
        button_name: str,
        tab_index: int,
    ) -> None:
        """Sync one right-rail art-tools button with sidebar state."""
        button = getattr(self.ui, button_name, None)
        if button is None:
            return
        button.blockSignals(True)
        button.setChecked(
            self._sidebar_is_visible()
            and self._current_sidebar_index()
            == self._art_tools_sidebar_index
            and self._current_art_tools_tab_index() == tab_index
        )
        button.blockSignals(False)

    def set_stats_button_checked(self):
        self.ui.stats_button.blockSignals(True)
        self.ui.stats_button.setChecked(
            self._sidebar_is_visible()
            and self._current_sidebar_index() == self._stats_sidebar_index
        )
        self.ui.stats_button.blockSignals(False)
