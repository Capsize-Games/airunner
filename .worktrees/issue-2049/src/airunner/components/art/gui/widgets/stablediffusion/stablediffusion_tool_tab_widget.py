import importlib
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGridLayout, QSplitter

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.templates.stablediffusion_tool_tab_ui import (
    Ui_stablediffusion_tool_tab_widget,
)
from airunner.utils.settings.get_qsettings import get_qsettings


class StablediffusionToolTabWidget(BaseWidget):
    ui: Ui_stablediffusion_tool_tab_widget  # type: ignore[assignment]
    widget_class_ = Ui_stablediffusion_tool_tab_widget
    _min_tab_index = 0
    _max_tab_index = 5
    _page_widget_specs = {
        0: (
            (
                "stable_diffusion_widget_placeholder",
                "stable_diffusion_widget",
                "airunner.components.art.gui.widgets.stablediffusion."
                "stable_diffusion_settings_widget",
                "StableDiffusionSettingsWidget",
            ),
        ),
        1: (
            (
                "lora_container_widget_placeholder",
                "lora_container_widget",
                "airunner.components.art.gui.widgets.lora."
                "lora_container_widget",
                "LoraContainerWidget",
            ),
        ),
        2: (
            (
                "embeddings_container_widget_placeholder",
                "embeddings_container_widget",
                "airunner.components.art.gui.widgets.embeddings."
                "embeddings_container_widget",
                "EmbeddingsContainerWidget",
            ),
        ),
        3: (
            (
                "canvas_layer_container_placeholder",
                "canvas_layer_container",
                "airunner.components.art.gui.widgets.canvas."
                "canvas_layer_container_widget",
                "CanvasLayerContainerWidget",
            ),
        ),
        4: (
            (
                "grid_preferences_placeholder",
                "grid_preferences",
                "airunner.components.art.gui.widgets.grid_preferences."
                "grid_preferences_widget",
                "GridPreferencesWidget",
            ),
            (
                "active_grid_settings_widget_placeholder",
                "active_grid_settings_widget",
                "airunner.components.art.gui.widgets.active_grid_settings."
                "active_grid_settings_widget",
                "ActiveGridSettingsWidget",
            ),
        ),
        5: (
            (
                "batch_container_placeholder",
                "widget",
                "airunner.components.art.gui.widgets.canvas."
                "batch_container",
                "BatchContainer",
            ),
        ),
    }

    def __init__(self, *args, **kwargs):
        self._splitters = ["layer_tab_splitter"]
        self._requested_active_index: Optional[int] = None
        super().__init__(*args, **kwargs)
        self.qsettings = get_qsettings()
        self._configure_tool_tab_widget()

    def _configure_tool_tab_widget(self) -> None:
        """Hide the visible tab bar and wire persistence hooks."""
        tab_widget = self.ui.tool_tab_widget_container
        tab_widget.tabBar().hide()
        tab_widget.currentChanged.connect(
            self.on_tool_tab_widget_container_currentChanged
        )

    @classmethod
    def _clamp_tool_tab_index(cls, index: int) -> int:
        """Clamp one requested tool-tab index to the supported range."""
        return max(cls._min_tab_index, min(index, cls._max_tab_index))

    def current_tool_page_index(self) -> int:
        """Return the active tool-tab index."""
        return self._clamp_tool_tab_index(
            self.ui.tool_tab_widget_container.currentIndex()
        )

    def _ensure_tool_page_loaded(self, index: int) -> None:
        """Instantiate the selected tab page the first time it is shown."""
        for spec in self._page_widget_specs.get(index, ()):  # pragma: no branch
            self._attach_lazy_widget(*spec)

    def _attach_lazy_widget(
        self,
        placeholder_attr: str,
        widget_attr: str,
        module_path: str,
        class_name: str,
    ):
        """Replace one placeholder with its real child widget."""
        widget = getattr(self.ui, widget_attr, None)
        if widget is not None:
            return widget
        placeholder = getattr(self.ui, placeholder_attr, None)
        if placeholder is None:
            return None
        parent = placeholder.parent()
        widget = self._create_lazy_widget(module_path, class_name, parent)
        widget.setObjectName(widget_attr)
        self._replace_placeholder(placeholder, widget)
        setattr(self.ui, placeholder_attr, None)
        setattr(self.ui, widget_attr, widget)
        return widget

    def _create_lazy_widget(self, module_path: str, class_name: str, parent):
        """Import and instantiate one deferred tool-tab widget."""
        module = importlib.import_module(module_path)
        factory = getattr(module, class_name)
        return factory(parent)

    def _replace_placeholder(self, placeholder, widget) -> None:
        """Insert one widget where a placeholder currently lives."""
        parent = placeholder.parent()
        if isinstance(parent, QSplitter):
            index = parent.indexOf(placeholder)
            placeholder.hide()
            placeholder.setParent(None)
            parent.insertWidget(index, widget)
            placeholder.deleteLater()
            return
        layout = parent.layout() or QGridLayout(parent)
        index = layout.indexOf(placeholder)
        row, column, row_span, column_span = 0, 0, 1, 1
        if index >= 0:
            row, column, row_span, column_span = layout.getItemPosition(index)
            layout.removeWidget(placeholder)
        placeholder.hide()
        placeholder.setParent(None)
        layout.addWidget(widget, row, column, row_span, column_span)
        placeholder.deleteLater()

    def show_tool_page(self, index: int) -> None:
        """Select one tool-tab page and persist the choice."""
        clamped_index = self._clamp_tool_tab_index(index)
        self._ensure_tool_page_loaded(clamped_index)
        self._requested_active_index = clamped_index
        self.ui.tool_tab_widget_container.setCurrentIndex(clamped_index)
        self.qsettings.setValue(
            "tabs/stablediffusion_tool_tab/active_index",
            clamped_index,
        )

    @Slot(int)
    def on_tool_tab_widget_container_currentChanged(self, index: int):
        index = self._clamp_tool_tab_index(index)
        self._ensure_tool_page_loaded(index)
        self._requested_active_index = index
        self.qsettings.setValue(
            "tabs/stablediffusion_tool_tab/active_index", index
        )

    def showEvent(self, event):
        super().showEvent(event)
        active_index = self._requested_active_index
        if active_index is None:
            saved_index = self.qsettings.value(
                "tabs/stablediffusion_tool_tab/active_index",
                self._min_tab_index,
            )
            try:
                active_index = int(saved_index)
            except (TypeError, ValueError):
                active_index = self._min_tab_index
        self.show_tool_page(active_index)
