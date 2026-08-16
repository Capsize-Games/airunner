"""Panel/splitter toggle and maximize behavior for MainWindow."""

from __future__ import annotations

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.application.gui.windows.main.controllers.panel_builder_controller import (
    PanelBuilderController,
)


class PanelLayoutController(PanelBuilderController):
    """Show/hide splitters and maximize the canvas workspace."""

    def _ensure_left_panel_page_loaded(self, page_index: int) -> bool:
        """Load left-panel content lazily for the requested page."""
        try:
            if page_index == self._left_documents_panel_index:
                self._ensure_knowledgebase_loaded()
            elif page_index == self._left_history_panel_index:
                self._ensure_left_history_loaded()
            elif page_index == self._left_llm_settings_panel_index:
                self._ensure_left_llm_settings_loaded()
        except Exception:
            self.logger.exception("Failed to load left panel page %s", page_index)
            return False
        return True

    def _ensure_sidebar_page_loaded(self, page_index: int) -> bool:
        """Load sidebar content lazily for the requested page."""
        try:
            if page_index == self._stats_sidebar_index:
                self._ensure_stats_loaded()
            elif page_index == self._art_tools_sidebar_index:
                self._ensure_art_tools_loaded(self._saved_art_tools_tab_index())
        except Exception:
            self.logger.exception("Failed to load sidebar page %s", page_index)
            return False
        return True

    def _toggle_sidebar_page(self, page_index: int, visible: bool) -> None:
        """Switch or hide the VS Code style right sidebar page."""
        if visible:
            if not self._ensure_sidebar_page_loaded(page_index):
                self._sync_sidebar_button_states()
                return
            self.ui.sidebar_tab.setCurrentIndex(page_index)
            self._toggle_splitter_section(
                True,
                self._stats_splitter_index,
                self.ui.main_window_splitter,
                self._sidebar_page_min_size(page_index),
            )
        elif self._sidebar_is_visible() and self._current_sidebar_index() == page_index:
            self._toggle_splitter_section(
                False,
                self._stats_splitter_index,
                self.ui.main_window_splitter,
                self._sidebar_page_min_size(page_index),
            )
        self._sync_sidebar_button_states()

    def _toggle_art_tools_tab(self, tab_index: int, visible: bool) -> None:
        """Show or hide one nested art-tools tab from the right sidebar."""
        tab_index = self._clamp_art_tools_tab_index(tab_index)
        if visible:
            try:
                self._ensure_art_tools_loaded(tab_index)
            except Exception:
                self.logger.exception("Failed to load art tools tab %s", tab_index)
                self._sync_sidebar_button_states()
                return
            self._toggle_sidebar_page(self._art_tools_sidebar_index, True)
            return
        if self._art_tools_tab_is_active(tab_index):
            self._toggle_sidebar_page(self._art_tools_sidebar_index, False)
            return
        self._sync_sidebar_button_states()

    def _art_tools_tab_is_active(self, tab_index: int) -> bool:
        """Return True when the requested art-tools tab is currently shown."""
        return (
            self._sidebar_is_visible()
            and self._current_sidebar_index() == self._art_tools_sidebar_index
            and self._current_art_tools_tab_index() == tab_index
        )

    def _sidebar_page_min_size(self, page_index: int) -> int:
        """Return a sensible opening width for one right-panel page."""
        if page_index == self._art_tools_sidebar_index:
            return 320
        return 280

    def _toggle_canvas_panel(self, visible: bool) -> None:
        """Show or hide the canvas panel within the center splitter."""
        min_size = 320
        if visible:
            self._show_canvas_panel(min_size)
        elif self._canvas_panel_is_visible():
            self._hide_canvas_panel(min_size)
        self._sync_sidebar_button_states()

    def _show_canvas_panel(self, min_size: int) -> None:
        """Open the canvas panel and maximize the canvas workspace."""
        if not self._center_section_is_visible():
            self._toggle_splitter_section(
                True,
                self._center_splitter_index,
                self.ui.main_window_splitter,
                min_size,
            )
        self._maximize_canvas_workspace()
        self._maximize_canvas_panel()

    def _hide_canvas_panel(self, min_size: int) -> None:
        """Collapse the canvas panel, and the center splitter if empty."""
        self._toggle_splitter_section(
            False,
            self._canvas_panel_index,
            self.ui.center_splitter,
            min_size,
        )
        if not self._prompt_panel_is_visible():
            self._toggle_splitter_section(
                False,
                self._center_splitter_index,
                self.ui.main_window_splitter,
                min_size,
            )

    def _maximize_canvas_workspace(self) -> None:
        """Shrink visible left panels so the center workspace can expand."""
        splitter = getattr(self.ui, "main_window_splitter", None)
        if splitter is None or len(splitter.sizes()) <= self._center_splitter_index:
            return
        sizes = splitter.sizes()
        total_width = sum(max(size, 0) for size in sizes)
        if total_width <= 0:
            return
        target_sizes = list(sizes)
        fixed_width = self._fixed_panel_width(target_sizes, sizes)
        target_sizes[self._center_splitter_index] = max(1, total_width - fixed_width)
        splitter.setSizes(target_sizes)

    def _fixed_panel_width(self, target_sizes, sizes) -> int:
        """Compute the fixed width reserved for left/chat/stats panels."""
        fixed_width = self._left_panel_reserved_width(target_sizes)
        if len(sizes) > self._chat_splitter_index and sizes[self._chat_splitter_index] > 0:
            target_sizes[self._chat_splitter_index] = self._chat_panel_target_width
        else:
            target_sizes[self._chat_splitter_index] = 0
        fixed_width += target_sizes[self._chat_splitter_index]
        if len(sizes) > self._stats_splitter_index and sizes[self._stats_splitter_index] <= 0:
            target_sizes[self._stats_splitter_index] = 0
        fixed_width += target_sizes[self._stats_splitter_index]
        return fixed_width

    def _left_panel_reserved_width(self, target_sizes) -> int:
        """Return the width reserved for the left panel."""
        if self._left_panel_is_visible():
            target_sizes[self._documents_splitter_index] = self._left_panel_target_width
        else:
            target_sizes[self._documents_splitter_index] = 0
        return target_sizes[self._documents_splitter_index]

    def _maximize_canvas_panel(self) -> None:
        """Let the canvas take the remaining width in the center splitter."""
        splitter = getattr(self.ui, "center_splitter", None)
        if splitter is None:
            return
        prompt_size = 1 if self._prompt_panel_is_visible() else 0
        splitter.setSizes([10000, prompt_size])

    def _toggle_prompt_panel(self, visible: bool) -> None:
        """Show or hide the dedicated prompt panel."""
        min_size = 350
        if visible:
            self._show_prompt_panel(min_size)
        elif self._prompt_panel_is_visible():
            self._hide_prompt_panel(min_size)
        self._sync_sidebar_button_states()

    def _show_prompt_panel(self, min_size: int) -> None:
        """Open the prompt panel within the center splitter."""
        self._ensure_art_prompt_loaded()
        if not self._center_section_is_visible():
            self._toggle_splitter_section(
                True,
                self._center_splitter_index,
                self.ui.main_window_splitter,
                min_size,
            )
        self._toggle_splitter_section(
            True,
            self._prompt_panel_index,
            self.ui.center_splitter,
            min_size,
        )

    def _hide_prompt_panel(self, min_size: int) -> None:
        """Collapse the prompt panel, and the center splitter if empty."""
        self._toggle_splitter_section(
            False,
            self._prompt_panel_index,
            self.ui.center_splitter,
            min_size,
        )
        if not self._canvas_panel_is_visible():
            self._toggle_splitter_section(
                False,
                self._center_splitter_index,
                self.ui.main_window_splitter,
                min_size,
            )

    def _toggle_left_panel_page(self, page_index: int, visible: bool) -> None:
        """Switch or hide the shared left splitter panel page."""
        if visible:
            self._show_left_panel_page(page_index)
        elif (
            self._left_panel_is_visible()
            and self._current_left_panel_index() == page_index
        ):
            self._hide_left_panel_page()
        self._sync_left_panel_button_states()

    def _show_left_panel_page(self, page_index: int) -> None:
        """Open one left-panel page."""
        if not self._ensure_left_panel_page_loaded(page_index):
            self._sync_left_panel_button_states()
            return
        self.ui.left_panel_tab.setCurrentIndex(page_index)
        if not self._left_panel_is_visible():
            self._toggle_splitter_section(
                True,
                self._documents_splitter_index,
                self.ui.main_window_splitter,
                self._left_panel_target_width,
            )

    def _hide_left_panel_page(self) -> None:
        """Collapse the left panel splitter."""
        self._toggle_splitter_section(
            False,
            self._documents_splitter_index,
            self.ui.main_window_splitter,
            self._left_panel_target_width,
        )
