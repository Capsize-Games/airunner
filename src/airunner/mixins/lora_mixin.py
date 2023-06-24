import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from PyQt6 import QtCore


class LoraMixin:
    lora_loaded = False

    total_lora_by_section = {}

    def toggle_all_lora(self, checked, tab):
        for i in range(tab.lora_scroll_area.widget().layout().count()):
            lora_widget = tab.lora_scroll_area.widget().layout().itemAt(i).widget()
            if lora_widget:
                lora_widget.enabledCheckbox.setChecked(checked)

    def initialize(self):
        self.initialize_lora()

    def tab_has_lora(self, tab):
        return tab not in ["upscale", "superresolution", "txt2vid"]

    def available_lora(self, action):
        available_lora = self.settings_manager.settings.available_loras.get()
        try:
            loras = available_lora[action]
        except KeyError:
            loras = []
        available_lora = []
        for lora in loras:
            if lora["enabled"] and lora["scale"] > 0:
                available_lora.append(lora)
        return available_lora

    def initialize_lora(self):
        self.lora_loaded = False
        self.settings_manager.settings.lora_path.my_signal.connect(self.refresh_lora)
        self.refresh_lora()

    def refresh_lora(self):
        # print available attributes on self
        if not self.tabs:
            return
        for tab_name in self.tabs.keys():
            tab = self.tabs[tab_name]
            if not self.tab_has_lora(tab_name):
                tab.PromptTabsSection.removeTab(2)
            else:
                self.load_lora_tab(tab, tab_name)
            if not self.tab_has_embeddings(tab_name):
                tab.PromptTabsSection.removeTab(1)
        self.initialize_lora_trigger_words()

    def available_loras(self, tab_name):
        base_path = self.settings_manager.settings.model_base_path.get()
        lora_path = self.settings_manager.settings.lora_path.get() or "lora"
        if lora_path == "lora":
            lora_path = os.path.join(base_path, lora_path)
        if not os.path.exists(lora_path):
            return []
        available_lora = self.settings_manager.settings.available_loras.get()
        if tab_name not in available_lora:
            available_lora[tab_name] = []
        self.settings_manager.enable_save()
        available_lora[tab_name] = self.get_list_of_available_loras(tab_name, lora_path, lora_names=available_lora[tab_name])
        self.settings_manager.settings.available_loras.set(available_lora)
        self.settings_manager.save_settings()
        return available_lora[tab_name]

    def get_list_of_available_loras(self, tab_name, lora_path, lora_names=None):
        self.total_lora_by_section[tab_name] = {
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
                # check if we have scale in self.settings_manager.settings.available_loras[tab_name]
                available_lora = self.settings_manager.settings.available_loras.get()
                if tab_name in available_lora:
                    loras = available_lora[tab_name] or []
                    for lora in loras:
                        if lora["name"] == name:
                            scale = lora["scale"]
                            enabled = lora["enabled"]
                            trigger_word = lora["trigger_word"] if trigger_word in lora else ""
                            self.total_lora_by_section[tab_name]["total"] += 1
                            if enabled:
                                self.total_lora_by_section[tab_name]["enabled"] += 1
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

    def load_lora_tab(self, tab, tab_name=None):
        container = QWidget()
        container.setLayout(QVBoxLayout())
        available_loras = self.available_loras(tab_name)
        for lora in available_loras:
            lora_widget = self.load_template("lora")
            lora_widget.enabledCheckbox.setText(lora["name"])
            # lora_widget.label.setText(lora["name"])
            enabled = lora["enabled"]
            lora_widget.enabledCheckbox.setChecked(enabled)
            container.layout().addWidget(lora_widget)
            # scale = lora["scale"]
            # lora_widget.scaleSlider.setValue(int(scale))
            # lora_widget.scaleSpinBox.setValue(scale / 100)
            # lora_widget.scaleSlider.valueChanged.connect(
            #     lambda value, _lora_widget=lora_widget, _lora=lora, _tab_name=tab_name: self.handle_lora_slider(
            #         _lora, _lora_widget, value, _tab_name))
            # lora_widget.scaleSpinBox.valueChanged.connect(
            #     lambda value, _lora_widget=lora_widget, _lora=lora, _tab_name=tab_name: self.handle_lora_spinbox(
            #         _lora, _lora_widget, value, _tab_name))
            lora_widget.enabledCheckbox.stateChanged.connect(
                lambda value, _lora=lora, _tab_name=tab_name: self.toggle_lora(_lora, value, _tab_name))
        # add a vertical spacer to the end of the container
        container.layout().addStretch()
        # display tabs of tab.PromptTabsSection which is a QTabWidget
        tab.lora_scroll_area.setWidget(container)

        # if all lora are checked set toggleAllLora
        if tab_name in self.total_lora_by_section:
            if self.total_lora_by_section[tab_name]["total"] == self.total_lora_by_section[tab_name]["enabled"]:
                tab.toggleAllLora.setChecked(True)

        # set the tab name
        self.update_lora_tab_name(tab_name)

    def initialize_lora_trigger_words(self):
        available_loras = self.settings_manager.settings.available_loras.get()
        try:
            available_loras = available_loras['txt2img']
        except KeyError:
            available_loras = []

        for lora in available_loras:
            trigger_word = lora["trigger_word"] if "trigger_word" in lora else ""
            for tab_name in self.tabs.keys():
                tab = self.tabs[tab_name]
                if not self.tab_has_lora(tab_name):
                    continue
                for i in range(tab.lora_scroll_area.widget().layout().count()):
                    lora_widget = tab.lora_scroll_area.widget().layout().itemAt(i).widget()
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
        available_loras = self.settings_manager.settings.available_loras.get()
        for tab_name in self.tabs.keys():
            if not self.tab_has_lora(tab_name):
                continue
            for n in range(len(available_loras[tab_name])):
                if available_loras[tab_name][n]["name"] == lora["name"]:
                    available_loras[tab_name][n]["trigger_word"] = value
        self.settings_manager.settings.available_loras.set(available_loras)
        self.settings_manager.save_settings()

    def toggle_lora(self, lora, value, tab_name):
        available_loras = self.settings_manager.settings.available_loras.get()
        for n in range(len(available_loras[tab_name])):
            if available_loras[tab_name][n]["name"] == lora["name"]:
                available_loras[tab_name][n]["enabled"] = value == 2
                if value == 2:
                    self.total_lora_by_section[tab_name]["enabled"] += 1
                else:
                    self.total_lora_by_section[tab_name]["enabled"] -= 1
                self.update_lora_tab_name(tab_name)
        self.settings_manager.settings.available_loras.set(available_loras)
        self.settings_manager.save_settings()

    def update_lora_tab_name(self, tab_name):
        if tab_name not in self.total_lora_by_section:
            self.total_lora_by_section[tab_name] = {"total": 0, "enabled": 0}
        self.tabs[tab_name].PromptTabsSection.setTabText(
            2,
            f'LoRA ({self.total_lora_by_section[tab_name]["enabled"]}/{self.total_lora_by_section[tab_name]["total"]})'
        )

    def handle_lora_slider(self, lora, lora_widget, value, tab_name):
        available_loras = self.settings_manager.settings.available_loras.get()
        float_val = value / 100
        for n in range(len(available_loras[tab_name])):
            if available_loras[tab_name][n]["name"] == lora["name"]:
                available_loras[tab_name][n]["scale"] = float_val
        lora_widget.scaleSpinBox.setValue(float_val)
        self.settings_manager.settings.available_loras.set(available_loras)
        self.settings_manager.save_settings()

    def handle_lora_spinbox(self, lora, lora_widget, value, tab_name):
        available_loras = self.settings_manager.settings.available_loras.get()
        for n in range(len(available_loras[tab_name])):
            if available_loras[tab_name][n]["name"] == lora["name"]:
                available_loras[tab_name][n]["scale"] = value
        lora_widget.scaleSlider.setValue(int(value * 100))
        self.settings_manager.settings.available_loras.set(available_loras)
        self.settings_manager.save_settings()
