import os
from typing import Any, Dict, List
from PySide6.QtCore import Slot, QSize, QTimer, Qt
from PySide6.QtWidgets import QWidget, QSizePolicy, QApplication

from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.lora.lora_widget import LoraWidget
from airunner.components.art.gui.widgets.lora.templates.lora_container_ui import (
    Ui_lora_container,
)


class LoraContainerWidget(BaseWidget):
    ui: Ui_lora_container  # type: ignore[assignment]
    widget_class_ = Ui_lora_container
    search_filter = ""
    spacer = None

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LORA_UPDATED_SIGNAL: (
                self.on_lora_updated_signal
            ),
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: (
                self.on_model_status_changed_signal
            ),
            SignalCode.LORA_STATUS_CHANGED: self.on_lora_modified,
            SignalCode.LORA_DELETE_SIGNAL: self._delete_lora,
        }
        self._version = None
        super().__init__(*args, **kwargs)
        self.initialized = False
        self._deleting = False
        self.ui.loading_icon.hide()
        self.ui.loading_icon.set_size(
            spinner_size=QSize(30, 30), label_size=QSize(24, 24)
        )
        self._apply_button_enabled = False
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)

    @property
    def lora(self) -> List[Any]:
        return self.load_lora()

    @Slot()
    def scan_for_lora(self):
        self._load_lora(force_reload=True)

    @Slot()
    def on_apply_lora_button_clicked(self):
        self._apply_button_enabled = False
        self.api.art.lora.update()

    def on_lora_modified(self):
        self._apply_button_enabled = True
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)

    def on_model_status_changed_signal(self, data):
        model = data["model"]
        status = data["status"]
        if model is ModelType.SD:
            if status is ModelStatus.LOADING:
                self._disable_form()
            else:
                self._enable_form()

    def _disable_form(self):
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)
        self.ui.lora_scale_slider.setEnabled(False)
        self.ui.toggleAllLora.setEnabled(False)
        self.ui.loading_icon.show()
        self._toggle_lora_widgets(False)

    def _enable_form(self):
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)
        self.ui.lora_scale_slider.setEnabled(True)
        self.ui.toggleAllLora.setEnabled(True)
        self.ui.loading_icon.hide()
        self._toggle_lora_widgets(True)

    def _toggle_lora_widgets(self, enable: bool):
        for i in range(self.ui.lora_scroll_area.widget().layout().count()):
            lora_widget = (
                self.ui.lora_scroll_area.widget()
                .layout()
                .itemAt(i)
                .widget()
            )
            if isinstance(lora_widget, LoraWidget):
                if enable:
                    lora_widget.enable_lora_widget()
                else:
                    lora_widget.disable_lora_widget()

    def on_application_settings_changed_signal(self):
        self._load_lora()

    def on_lora_updated_signal(self):
        self._enable_form()

    def toggle_all(self, val):
        lora_widgets = [
            self.ui.lora_scroll_area.widget().layout().itemAt(i).widget()
            for i in range(self.ui.lora_scroll_area.widget().layout().count())
            if isinstance(
                self.ui.lora_scroll_area.widget()
                .layout()
                .itemAt(i)
                .widget(),
                LoraWidget,
            )
        ]
        for lora_widget in lora_widgets:
            lora_widget.ui.enabledCheckbox.blockSignals(True)
            lora_widget.action_toggled_lora_enabled(val)
            lora_widget.ui.enabledCheckbox.blockSignals(False)

    def showEvent(self, event):
        if not self.initialized:
            self.scan_for_lora()
            self.initialized = True
        self._load_lora(force_reload=True)

    def _load_lora(self, force_reload=False):
        version = self.generator_settings.version

        if self._version is None or self._version != version or force_reload:
            self._version = version
            self.clear_lora_widgets()
            loras = self._safe_lora_query(version)
            if loras:
                filtered_loras = [
                    lora
                    for lora in loras
                    if self.search_filter.lower() in lora.name.lower()
                ]
                for lora in filtered_loras:
                    self._add_lora(lora)
                self.add_spacer()

    def _safe_lora_query(self, version: str):
        """Query lora from daemon, returning empty list on error."""
        try:
            result = self.resource_store.query(
                "Lora",
                filters={"version": version},
            )
            return result if result is not None else []
        except Exception as e:
            self.logger.warning(
                "Lora query against daemon failed: %s", e
            )
            return []

    def remove_spacer(self):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(
                self.spacer
            )
            self.spacer.setParent(None)
            self.spacer.deleteLater()
            self.spacer = None

    def add_spacer(self):
        self.remove_spacer()

        self.spacer = QWidget()
        self.spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.spacer.setMinimumHeight(100)

        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)
        self.ui.scrollAreaWidgetContents.layout().update()
        QApplication.processEvents()
        QTimer.singleShot(
            50,
            lambda: self.ui.scrollAreaWidgetContents.layout().update(),
        )

    def _add_lora(self, lora):
        if lora is None:
            return
        lora_widget = LoraWidget(lora=lora)
        self.ui.scrollAreaWidgetContents.layout().addWidget(lora_widget)

    def _delete_lora(self, data: Dict):
        self._deleting = True
        lora_widget = data["lora_widget"]

        # Delete lora from database via daemon
        self.resource_store.delete(
            "Lora", lora_widget.current_lora.id
        )

        self._apply_button_enabled = True
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)
        self._load_lora(force_reload=True)
        self._deleting = False

    def available_lora(self, _action):
        available_lora = []
        for lora in self.lora:
            if lora.enabled and lora.scale > 0:
                available_lora.append(lora)
        return available_lora

    def search_text_changed(self, val):
        self.search_filter = val
        self._load_lora(force_reload=True)

    def clear_lora_widgets(self):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(
                self.spacer
            )
        for i in reversed(
            range(self.ui.scrollAreaWidgetContents.layout().count())
        ):
            widget = (
                self.ui.scrollAreaWidgetContents.layout()
                .itemAt(i)
                .widget()
            )
            if isinstance(widget, LoraWidget):
                widget.deleteLater()
