"""Lazy page construction and the left-panel tab host for MainWindow."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGridLayout, QPushButton, QTabWidget, QWidget

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)


class PanelBuilderController(MainWindowBase):
    """Construct lazy panel pages and manage the left panel tab host."""

    def _attach_lazy_widget(
        self,
        parent_attr,
        widget_attr,
        object_name,
        factory,
        placeholder_attr=None,
    ):
        widget = getattr(self.ui, widget_attr, None)
        if widget is not None:
            return widget
        parent = getattr(self.ui, parent_attr)
        layout = self._ensure_parent_layout(parent)
        widget = factory(parent)
        widget.setObjectName(object_name)
        self._remove_placeholder(layout, placeholder_attr)
        layout.addWidget(widget, 0, 0, 1, 1)
        setattr(self.ui, widget_attr, widget)
        return widget

    def _ensure_parent_layout(self, parent):
        """Return the parent's grid layout, creating one when missing."""
        layout = parent.layout()
        if layout is None:
            layout = QGridLayout(parent)
            layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def _remove_placeholder(self, layout, placeholder_attr) -> None:
        """Remove one placeholder widget before attaching the real one."""
        placeholder = getattr(self.ui, placeholder_attr, None)
        if placeholder is None:
            return
        layout.removeWidget(placeholder)
        placeholder.deleteLater()
        setattr(self.ui, placeholder_attr, None)

    def _ensure_canvas_loaded(self) -> None:
        """Create the main canvas once after the window is shown."""
        from airunner.components.art.gui.widgets.canvas.canvas_widget import (
            CanvasWidget,
        )

        self.canvas = self._attach_lazy_widget(
            "center_tab_container",
            "canvas",
            "canvas",
            CanvasWidget,
            placeholder_attr="canvas_placeholder",
        )

    def _ensure_knowledgebase_loaded(self) -> None:
        """Create the documents sidebar page only when it is shown."""
        from airunner.components.documents.gui.widgets.documents import (
            DocumentsWidget,
        )

        self._ensure_left_panel_host()
        self._attach_lazy_widget(
            "left_documents_page",
            "documents",
            "documents",
            DocumentsWidget,
            placeholder_attr="left_documents_placeholder",
        )

    def _ensure_left_history_loaded(self) -> None:
        """Create the history left-panel page only when it is shown."""
        from airunner.components.llm.gui.widgets.llm_history_widget import (
            LLMHistoryWidget,
        )

        self._ensure_left_panel_host()
        return self._attach_lazy_widget(
            "left_history_page",
            "left_history_widget",
            "left_history_widget",
            LLMHistoryWidget,
            placeholder_attr="left_history_placeholder",
        )

    def _ensure_left_llm_settings_loaded(self) -> None:
        """Create the LLM settings left-panel page only when it is shown."""
        from airunner.components.llm.gui.widgets.llm_settings_widget import (
            LLMSettingsWidget,
        )

        self._ensure_left_panel_host()
        widget = self._attach_lazy_widget(
            "left_llm_settings_page",
            "left_llm_settings_widget",
            "left_llm_settings_widget",
            LLMSettingsWidget,
            placeholder_attr="left_llm_settings_placeholder",
        )
        handle_loaded = getattr(widget, "handle_main_window_loaded", None)
        if callable(handle_loaded):
            handle_loaded()

    def _create_left_sidebar_buttons(self) -> None:
        """Ensure left-rail history/settings buttons exist and are wired."""
        history_button = self._ensure_left_sidebar_button(
            "history_sidebar_button", "Chat history", 2
        )
        llm_settings_button = self._ensure_left_sidebar_button(
            "llm_settings_sidebar_button", "LLM generator settings", 3
        )
        if getattr(self, "_left_sidebar_buttons_connected", False):
            return
        history_button.toggled.connect(self.on_history_sidebar_button_toggled)
        llm_settings_button.toggled.connect(
            self.on_llm_settings_sidebar_button_toggled
        )
        self._left_sidebar_buttons_connected = True

    def _ensure_left_sidebar_button(
        self, attr: str, tooltip: str, position: int
    ) -> QPushButton:
        """Return one left-rail sidebar button, creating it when missing."""
        button = getattr(self.ui, attr, None)
        if button is not None:
            return button
        button = QPushButton(self.ui.actionsidebar)
        button.setObjectName(attr)
        button.setMinimumSize(35, 35)
        button.setMaximumSize(35, 35)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setCheckable(True)
        button.setFlat(True)
        button.setToolTip(tooltip)
        self.ui.action_sidebar.insertWidget(position, button)
        setattr(self.ui, attr, button)
        return button

    def _ensure_left_panel_host(self) -> None:
        """Replace the single documents placeholder with a hidden tab host."""
        existing_tab_widget = getattr(self.ui, "left_panel_tab", None)
        if existing_tab_widget is not None:
            existing_tab_widget.tabBar().hide()
            self._connect_left_panel_tab(existing_tab_widget)
            return

        container = self.ui.documents_sidebar
        layout = self._ensure_parent_layout(container)
        tab_widget = self._build_left_panel_tab_host(container)
        self._remove_placeholder(layout, "documents_placeholder")
        if isinstance(layout, QGridLayout):
            layout.addWidget(tab_widget, 0, 0, 1, 1)
        else:
            layout.addWidget(tab_widget)
        self.ui.left_panel_tab = tab_widget
        self._connect_left_panel_tab(tab_widget)
        self._left_panel_host_connected = True

    def _connect_left_panel_tab(self, tab_widget) -> None:
        """Wire the left panel tab's currentChanged signal once."""
        if getattr(self, "_left_panel_host_connected", False):
            return
        tab_widget.currentChanged.connect(self.on_left_panel_tab_current_changed)
        self._left_panel_host_connected = True

    def _build_left_panel_tab_host(self, container) -> QTabWidget:
        """Create the hidden left-panel tab host and its pages."""
        tab_widget = QTabWidget(container)
        tab_widget.setObjectName("left_panel_tab")
        tab_widget.tabBar().hide()
        self._build_left_panel_tab_pages(tab_widget)
        return tab_widget

    def _build_left_panel_tab_pages(self, tab_widget: QTabWidget) -> None:
        """Create the hidden tab host pages for the left panel."""
        self._add_left_panel_page(
            tab_widget, "left_documents_page", "left_documents_placeholder"
        )
        self._add_left_panel_page(
            tab_widget, "left_history_page", "left_history_placeholder"
        )
        self._add_left_panel_page(
            tab_widget, "left_llm_settings_page", "left_llm_settings_placeholder"
        )

    def _add_left_panel_page(
        self, tab_widget: QTabWidget, page_name: str, placeholder_name: str
    ) -> None:
        """Add one hidden page to the left panel tab host."""
        page = QWidget(tab_widget)
        page.setObjectName(page_name)
        page_layout = QGridLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        placeholder = QWidget(page)
        placeholder.setObjectName(placeholder_name)
        page_layout.addWidget(placeholder, 0, 0, 1, 1)
        tab_widget.addTab(page, "")
        setattr(self.ui, page_name, page)
        setattr(self.ui, placeholder_name, placeholder)

    def _ensure_stats_loaded(self) -> None:
        """Create the stats sidebar page only when it is shown."""
        from airunner.components.model_management.gui.model_status_widget import (
            ModelStatusWidget,
        )

        self._attach_lazy_widget(
            "stats_page",
            "model_status_widget",
            "model_status_widget",
            ModelStatusWidget,
            placeholder_attr="stats_placeholder",
        )

    def _ensure_art_prompt_loaded(self) -> None:
        """Create the art prompt page only when it is shown."""
        from airunner.components.art.gui.widgets.stablediffusion.stablediffusion_generator_form import (
            StableDiffusionGeneratorForm,
        )

        self._attach_lazy_widget(
            "prompt_sidebar",
            "art_prompt_widget",
            "art_prompt_widget",
            StableDiffusionGeneratorForm,
            placeholder_attr="art_prompt_placeholder",
        )

    def _ensure_art_tools_loaded(self, tab_index: int | None = None) -> None:
        """Create the art settings page only when it is shown."""
        from airunner.components.art.gui.widgets.stablediffusion.stablediffusion_tool_tab_widget import (
            StablediffusionToolTabWidget,
        )

        widget = self._attach_lazy_widget(
            "art_tools_page",
            "art_tools_widget",
            "art_tools_widget",
            StablediffusionToolTabWidget,
            placeholder_attr="art_tools_placeholder",
        )
        show_tool_page = getattr(widget, "show_tool_page", None)
        if callable(show_tool_page) and tab_index is not None:
            show_tool_page(self._clamp_art_tools_tab_index(tab_index))
        return widget
