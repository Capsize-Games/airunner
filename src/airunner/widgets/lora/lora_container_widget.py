import os

from PyQt6.QtWidgets import QWidget, QSizePolicy

from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.lora_widget import LoraWidget
from airunner.widgets.lora.templates.lora_container_ui import Ui_lora_container


class LoraContainerWidget(BaseWidget):
    widget_class_ = Ui_lora_container
    lora_loaded = False
    total_lora_by_section = {}
    search_filter = ""
    spacer = None

    def toggle_all(self, val):
        for widget in self.ui.scrollAreaWidgetContents.children():
            if isinstance(widget, LoraWidget):
                widget.set_enabled(val)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.loars = None
        self.scan_for_lora()
        self.load_lora()

    def load_lora(self):
        for lora in self.settings["lora"]:
            if self.search_filter != "":
                if self.search_filter.lower() not in lora["name"].lower():
                    continue
            self.add_lora(lora)
        
        # add spacer to end of self.ui.scrollAreaWidgetContents.layout()
        if not self.spacer:
            self.spacer = QWidget()
            self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.spacer)

    def add_lora(self, lora):
        if lora is None:
            return
        lora_widget = LoraWidget(lora=lora)
        self.ui.scrollAreaWidgetContents.layout().addWidget(lora_widget)

    def scan_for_lora(self):
        lora_path = self.settings["path_settings"]["lora_model_path"]
        for dirpath, dirnames, filenames in os.walk(lora_path):
            # get version from dirpath
            version = dirpath.split("/")[-1]
            for file in filenames:
                if file.endswith(".ckpt") or file.endswith(".safetensors") or file.endswith(".pt"):
                    name = file.replace(".ckpt", "").replace(".safetensors", "").replace(".pt", "")
                    self.emit(SignalCode.LORA_ADD_SIGNAL, {
                        'name': name,
                        'path': os.path.join(dirpath, file),
                        'enabled': True,
                        'scale': 100.0,
                        'version': version
                    })

    def toggle_all_lora(self, checked):
        for i in range(self.ui.lora_scroll_area.widget().layout().count()):
            lora_widget = self.ui.lora_scroll_area.widget().layout().itemAt(i).widget()
            if lora_widget:
                lora_widget.enabledCheckbox.setChecked(checked)

    def tab_has_lora(self, tab):
        return tab not in ["upscale", "superresolution", "txt2vid"]

    def available_lora(self, action):
        available_lora = []
        for lora in self.settings["lora"]:
            if lora["enabled"] and lora["scale"] > 0:
                available_lora.append(lora)
        return available_lora

    def get_available_loras(self, tab_name):
        base_path = self.settings["path_settings"]["base_path"]
        lora_path = self.settings["path_settings"]["lora_model_path"]
        if lora_path == "lora":
            lora_path = os.path.join(base_path, lora_path)
        if not os.path.exists(lora_path):
            return []
        available_lora = self.get_list_of_available_loras(tab_name, lora_path, lora_names=self.settings["lora"])
        return available_lora

    def get_list_of_available_loras(self, tab_name, lora_path, lora_names=None):
        self.total_lora_by_section = {
            "total": 0,
            "enabled": 0
        }

        if lora_names is None:
            lora_names = []
        if not os.path.exists(lora_path):
            return lora_names
        possible_line_endings = ["ckpt", "safetensors", "bin"]
        new_loras = []
        for lora_file in os.listdir(lora_path):
            if os.path.isdir(os.path.join(lora_path, lora_file)):
                lora_names = self.get_list_of_available_loras(tab_name, os.path.join(lora_path, lora_file), lora_names)
            if lora_file.split(".")[-1] in possible_line_endings:
                name = lora_file.split(".")[0]
                scale = 100.0
                enabled = True
                trigger_word = ""
                available_lora = self.settings["lora"]
                for lora in available_lora:
                    if lora["name"] == name:
                        scale = lora["scale"]
                        enabled = lora["enabled"]
                        trigger_word = lora["trigger_word"] if trigger_word in lora else ""
                        self.total_lora_by_section["total"] += 1
                        if enabled:
                            self.total_lora_by_section["enabled"] += 1
                        break
                new_loras.append({
                    "name": name,
                    "scale": scale,
                    "enabled": enabled,
                    "loaded": False,
                    "trigger_word": trigger_word
                })
        # check if name already in lora_names:
        for old_lora in lora_names:
            name = old_lora["name"]
            found = False
            for new_lora in new_loras:
                if new_lora["name"] == name:
                    found = True
                    break
            if not found:
                lora_names.remove(old_lora)
        merge_lora = []
        for new_lora in new_loras:
            name = new_lora["name"]
            found = False
            for current_lora in lora_names:
                if current_lora["name"] == name:
                    found = True
            if not found:
                merge_lora.append(new_lora)
        lora_names.extend(merge_lora)
        return lora_names

    lora_tab_container = None

    def initialize_lora_trigger_words(self):
        for lora in self.settings["lora"]:
            trigger_word = lora["trigger_word"] if "trigger_word" in lora else ""
            for tab_name in self.tabs.keys():
                tab = self.tabs[tab_name]
                if not self.tab_has_lora(tab_name):
                    continue
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
        available_loras = self.settings["lora"]
        for n in range(len(available_loras)):
            if available_loras[n]["name"] == lora["name"]:
                available_loras[n]["trigger_word"] = value
        settings = self.settings
        settings["lora"] = available_loras
        self.settings = settings

    def toggle_lora(self, lora, value, tab_name):
        available_loras = self.settings["lora"]
        for n in range(len(available_loras)):
            if available_loras[n]["name"] == lora["name"]:
                available_loras[n]["enabled"] = value == 2
                if value == 2:
                    self.total_lora_by_section["enabled"] += 1
                else:
                    self.total_lora_by_section["enabled"] -= 1
                self.update_lora_tab_name(tab_name)
        settings = self.settings
        settings["lora"] = available_loras
        self.settings = settings

    def update_lora_tab_name(self, tab_name):
        # if tab_name not in self.total_lora_by_section:
        #     self.total_lora_by_section[tab_name] = {"total": 0, "enabled": 0}
        # self.tabs[tab_name].PromptTabsSection.setTabText(
        #     2,
        #     f'LoRA ({self.total_lora_by_section[tab_name]["enabled"]}/{self.total_lora_by_section[tab_name]["total"]})'
        # )
        pass

    def handle_lora_slider(self, lora, lora_widget, value, tab_name):
        available_loras = self.settings["lora"]
        float_val = value / 100
        for n in range(len(available_loras)):
            if available_loras[n]["name"] == lora["name"]:
                available_loras[n]["scale"] = float_val
        lora_widget.scaleSpinBox.setValue(float_val)
        settings = self.settings
        settings["lora"] = available_loras
        self.settings = settings

    def handle_lora_spinbox(self, lora, lora_widget, value, tab_name):
        settings = self.settings
        for n in range(len(settings["lora"])):
            if settings["lora"][n]["name"] == lora["name"]:
                settings["lora"][n]["scale"] = value
        lora_widget.scaleSlider.setValue(int(value * 100))
        self.loars = settings["lora"]
        self.settings = settings

    def search_text_changed(self, val):
        print("search text changed", val)
        self.search_filter = val
        self.clear_lora_widgets()
        self.load_lora()
    
    def clear_lora_widgets(self):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeWidget(self.spacer)
        for i in reversed(range(self.ui.scrollAreaWidgetContents.layout().count())):
            widget = self.ui.scrollAreaWidgetContents.layout().itemAt(i).widget()
            if isinstance(widget, LoraWidget):
                widget.deleteLater()