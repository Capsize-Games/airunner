import os

from PySide6.QtCore import Slot, QSize, QThread
from PySide6.QtWidgets import QWidget, QSizePolicy

from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.utils.models.scan_path_for_items import scan_path_for_lora
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.lora_widget import LoraWidget
from airunner.widgets.lora.templates.lora_container_ui import Ui_lora_container
from airunner.workers.directory_watcher import DirectoryWatcher


class LoraContainerWidget(BaseWidget):
    widget_class_ = Ui_lora_container
    search_filter = ""
    spacer = None

    def __init__(self, *args, **kwargs):
        self._version = None
        super().__init__(*args, **kwargs)
        self.initialized = False
        self._deleting = False
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.register(SignalCode.LORA_UPDATED_SIGNAL, self.on_lora_updated_signal)
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)
        self.register(SignalCode.LORA_STATUS_CHANGED, self.on_lora_modified)
        self.register(SignalCode.LORA_DELETE_SIGNAL, self.delete_lora)
        self.ui.loading_icon.hide()
        self.ui.loading_icon.set_size(spinner_size=QSize(30, 30), label_size=QSize(24, 24))
        self._apply_button_enabled = False
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)
        self._scanner_worker = DirectoryWatcher(self.path_settings.base_path, self._scan_path_for_lora)
        self._scanner_worker.scan_completed.connect(self.on_scan_completed)
        self._scanner_thread = QThread()
        self._scanner_worker.moveToThread(self._scanner_thread)
        self._scanner_thread.started.connect(self._scanner_worker.run)
        self._scanner_thread.start()

    def _scan_path_for_lora(self, path) -> bool:
        if self._deleting:
            return False
        return scan_path_for_lora(path)

    @Slot(bool)
    def on_scan_completed(self, force_reload: bool):
        self.load_lora(force_reload=force_reload)

    @Slot()
    def scan_for_lora(self):
        # clear all lora widgets
        force_reload = scan_path_for_lora(self.path_settings.base_path)
        self.load_lora(force_reload=force_reload)

    @Slot()
    def apply_lora(self):
        self._apply_button_enabled = False
        self.emit_signal(SignalCode.LORA_UPDATE_SIGNAL)

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
            lora_widget = self.ui.lora_scroll_area.widget().layout().itemAt(i).widget()
            if isinstance(lora_widget, LoraWidget):
                if enable:
                    lora_widget.enable_lora_widget()
                else:
                    lora_widget.disable_lora_widget()

    def on_application_settings_changed_signal(self):
        self.load_lora()

    def on_lora_updated_signal(self):
        self._enable_form()

    def toggle_all(self, val):
        lora_widgets = [
            self.ui.lora_scroll_area.widget().layout().itemAt(i).widget()
            for i in range(self.ui.lora_scroll_area.widget().layout().count())
            if isinstance(self.ui.lora_scroll_area.widget().layout().itemAt(i).widget(), LoraWidget)
        ]
        for lora_widget in lora_widgets:
            lora_widget.ui.enabledCheckbox.blockSignals(True)
            lora_widget.action_toggled_lora_enabled(val)
            lora_widget.ui.enabledCheckbox.blockSignals(False)

    def showEvent(self, event):
        if not self.initialized:
            self.scan_for_lora()
            self.initialized = True
        self.load_lora()

    def load_lora(self, force_reload=False):
        version = self.generator_settings.version

        if self._version is None or self._version != version or force_reload:
            self._version = version
            self.clear_lora_widgets()
            loras = self.get_lora_by_version(self._version)
            if loras:
                self.remove_spacer()
                filtered_loras = [
                    lora for lora in loras
                    if self.search_filter.lower() in lora.name.lower()
                ]
                for lora in filtered_loras:
                    self.add_lora(lora)
                self.add_spacer()

    def remove_spacer(self):
        # remove spacer from end of self.ui.scrollAreaWidgetContents.layout()
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(self.spacer)

    def add_spacer(self):
        # add spacer to end of self.ui.scrollAreaWidgetContents.layout()
        if not self.spacer:
            self.spacer = QWidget()
            self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self.remove_spacer()
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)

    def add_lora(self, lora):
        if lora is None:
            return
        lora_widget = LoraWidget(lora=lora)
        self.ui.scrollAreaWidgetContents.layout().addWidget(lora_widget)

    def delete_lora(self, data: dict):
        self._deleting = True
        lora_widget = data["lora_widget"]

        # Delete the lora from disc
        lora_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                self._version,
                "lora"
            )
        )
        lora_file = lora_widget.current_lora.name
        for dirpath, dirnames, filenames in os.walk(lora_path):
            for file in filenames:
                if file.startswith(lora_file):
                    os.remove(os.path.join(dirpath, file))
                    break

        # Remove lora from database
        session = self.db_handler.get_db_session()
        session.delete(lora_widget.current_lora)
        session.commit()
        session.close()

        self._apply_button_enabled = True
        self.ui.apply_lora_button.setEnabled(self._apply_button_enabled)
        self.load_lora(force_reload=True)
        self._deleting = False

    def available_lora(self, action):
        available_lora = []
        for lora in self.lora:
            if lora.enabled and lora.scale > 0:
                available_lora.append(lora)
        return available_lora

    def initialize_lora_trigger_words(self):
        for lora in self.lora:
            trigger_word = lora["trigger_word"] if "trigger_word" in lora else ""
            for tab_name in self.tabs.keys():
                tab = self.tabs[tab_name]
                for i in range(self.tool_menu_widget.lora_container_widget.lora_scroll_area.widget().layout().count()):
                    lora_widget = self.tool_menu_widget.lora_container_widget.lora_scroll_area.widget().layout().itemAt(
                        i).widget()
                    if not lora_widget:
                        continue
                    if lora_widget.enabledCheckbox.text() == lora["name"]:
                        if trigger_word != "":
                            lora_widget.trigger_word.setText(trigger_word)
                        lora_widget.trigger_word.textChanged.connect(
                            lambda value, _lora_widget=lora_widget, _lora=lora,
                                   _tab_name=tab_name: self.handle_lora_trigger_word(_lora, _lora_widget, value))
                        break

    def handle_lora_trigger_word(self, lora, lora_widget, value):
        for n in range(len(self.lora)):
            lora_object = self.lora[n]
            if lora_object.name == lora.name:
                lora_object.trigger_word = value
                self.update_lora(lora_object)

    def handle_lora_slider(self, lora, lora_widget, value, tab_name):
        float_val = value / 100
        for n in range(len(self.lora)):
            lora_object = self.lora[n]
            if lora_object.name == lora.name:
                lora_object.scale = float_val
                self.update_lora(lora_object)
        lora_widget.scaleSpinBox.setValue(float_val)

    def handle_lora_spinbox(self, lora, lora_widget, value, tab_name):
        for n in range(len(self.lora)):
            lora_object = self.lora[n]
            if lora_object.name == lora.name:
                lora_object.scale = value
                self.update_lora(lora_object)
        lora_widget.scaleSlider.setValue(int(value * 100))

    def search_text_changed(self, val):
        self.search_filter = val
        self.load_lora(force_reload=True)
    
    def clear_lora_widgets(self):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(self.spacer)
        for i in reversed(range(self.ui.scrollAreaWidgetContents.layout().count())):
            widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
            if isinstance(widget, LoraWidget):
                widget.deleteLater()
