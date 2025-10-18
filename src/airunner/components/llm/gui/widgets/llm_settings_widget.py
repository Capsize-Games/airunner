import os
import json
from PySide6.QtCore import Slot, Qt, QTimer
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QCheckBox, QHBoxLayout

from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.gui.widgets.templates.llm_settings_ui import (
    Ui_llm_settings_widget,
)
from airunner.components.application.gui.windows.main.ai_model_mixin import (
    AIModelMixin,
)
from airunner.enums import ModelService, SignalCode
from airunner.utils.settings.get_qsettings import get_qsettings


class LLMSettingsWidget(BaseWidget, AIModelMixin):
    widget_class_ = Ui_llm_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_form()
        self._toggle_model_path_visibility(
            self.llm_generator_settings.model_service
            != ModelService.LOCAL.value
        )
        self.register(
            SignalCode.LLM_MODEL_DOWNLOAD_PROGRESS,
            self.on_llm_model_download_progress,
        )
        self.ui.progressBar.setVisible(False)
        self._setup_adapters_table()
        self._load_adapters()
        self.ui.refresh_adapters_button.clicked.connect(
            self.on_refresh_adapters_clicked
        )

    @Slot(str)
    def on_model_path_textChanged(self, val: str):
        self.update_llm_generator_settings(model_path=val)

    @Slot(str)
    def on_model_service_currentTextChanged(self, model_service: str):
        self.api.llm.model_changed(model_service)
        self._toggle_model_path_visibility(
            model_service != ModelService.LOCAL.value
        )

    @Slot(bool)
    def toggle_use_cache(self, val: bool):
        self.update_chatbot("use_cache", val)

    def _toggle_model_path_visibility(self, val: bool):
        if val:
            self.ui.remote_model_path.show()
        else:
            self.ui.remote_model_path.hide()

    def showEvent(self, event):
        super().showEvent(event)

    def early_stopping_toggled(self, val):
        self.update_chatbot("early_stopping", val)

    def do_sample_toggled(self, val):
        self.update_chatbot("do_sample", val)

    def toggle_leave_model_in_vram(self, val):
        if val:
            self.update_memory_settings(
                unload_unused_models=False, move_unused_model_to_cpu=False
            )

    def initialize_form(self):
        elements = [
            self.ui.random_seed,
            self.ui.do_sample,
            self.ui.early_stopping,
            self.ui.override_parameters,
            self.ui.use_cache,
            self.ui.model_service,
            self.ui.model_path,
        ]

        for element in elements:
            element.blockSignals(True)

        self.ui.model_service.clear()
        self.ui.model_service.addItems([item.value for item in ModelService])

        self.ui.model_service.setCurrentText(
            self.llm_generator_settings.model_service
        )
        # QLineEdit requires setText, not setCurrentText
        self.ui.model_path.setText(self.llm_generator_settings.model_path)

        self.ui.top_p.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.top_p,
        )
        self.ui.max_new_tokens.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.max_new_tokens,
        )
        self.ui.repetition_penalty.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.repetition_penalty,
        )
        self.ui.min_length.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.min_length,
        )
        self.ui.length_penalty.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.length_penalty,
        )
        self.ui.num_beams.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.num_beams,
        )
        self.ui.ngram_size.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.ngram_size,
        )
        self.ui.temperature.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.temperature,
        )
        self.ui.sequences.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.sequences,
        )
        self.ui.top_k.init(
            slider_callback=self.callback,
            current_value=self.llm_generator_settings.top_k,
        )

        self.ui.override_parameters.setChecked(
            self.llm_generator_settings.override_parameters
        )

        self.ui.use_cache.setChecked(self.chatbot.use_cache)

        self.ui.random_seed.setChecked(self.chatbot.random_seed)
        self.ui.do_sample.setChecked(self.chatbot.do_sample)
        self.ui.early_stopping.setChecked(self.chatbot.early_stopping)

        for element in elements:
            element.blockSignals(False)

    def callback(self, attr_name, value, _widget=None):
        keys = attr_name.split(".")
        self.update_llm_generator_settings(**{keys[1]: value})

    def model_text_changed(self, val):
        self.update_application_settings(current_llm_generator=val)
        self.initialize_form()

    def toggle_move_model_to_cpu(self, val):
        data = {
            "move_unused_model_to_cpu": val,
        }
        if val:
            data["unload_unused_models"] = False
        self.update_memory_settings(**data)

    def override_parameters_toggled(self, val):
        self.update_llm_generator_settings(override_parameters=val)

    def random_seed_toggled(self, val):
        self.update_chatbot("random_seed", val)

    def seed_changed(self, val):
        self.update_chatbot("seed", val)

    def toggle_unload_model(self, val):
        data = {
            "unload_unused_models": val,
        }
        if val:
            data["move_unused_model_to_cpu"] = False
        self.update_memory_settings(**data)

    def reset_settings_to_default_clicked(self):
        self.initialize_form()
        chatbot = self.chatbot
        self.ui.top_p.set_slider_and_spinbox_values(chatbot.top_p)
        self.ui.repetition_penalty.set_slider_and_spinbox_values(
            chatbot.repetition_penalty
        )
        self.ui.min_length.set_slider_and_spinbox_values(chatbot.min_length)
        self.ui.length_penalty.set_slider_and_spinbox_values(
            chatbot.length_penalty
        )
        self.ui.num_beams.set_slider_and_spinbox_values(chatbot.num_beams)
        self.ui.ngram_size.set_slider_and_spinbox_values(chatbot.ngram_size)
        self.ui.temperature.set_slider_and_spinbox_values(chatbot.temperature)
        self.ui.sequences.set_slider_and_spinbox_values(chatbot.sequences)
        self.ui.top_k.set_slider_and_spinbox_values(chatbot.top_k)
        self.ui.random_seed.setChecked(chatbot.random_seed)

    def set_tab(self, tab_name):
        index = self.ui.tabWidget.indexOf(
            self.ui.tabWidget.findChild(QWidget, tab_name)
        )
        self.ui.tabWidget.setCurrentIndex(index)

    def update_chatbot(self, key, val):
        chatbot = self.chatbot
        try:
            setattr(chatbot, key, val)
        except TypeError:
            self.logger.error(f"Attribute {key} does not exist in Chatbot")
            return
        Chatbot.objects.update(pk=chatbot.id, **{key: val})

    def on_llm_model_download_progress(self, data):
        percent = data.get("percent", 0)
        if percent == 0 or percent == 100:
            self.ui.progressBar.setVisible(False)
        else:
            self.ui.progressBar.setVisible(True)
            self.ui.progressBar.setValue(percent)

    def _setup_adapters_table(self):
        """Configure the adapters table columns and behavior."""
        self.ui.adapters_table.horizontalHeader().setStretchLastSection(True)
        self.ui.adapters_table.setColumnWidth(0, 80)
        self.ui.adapters_table.setColumnWidth(1, 200)

    @Slot()
    def on_refresh_adapters_clicked(self):
        """Refresh the adapters list when button is clicked."""
        self._load_adapters()

    def _load_adapters(self):
        """Load available adapters from database and populate table."""
        self.ui.adapters_table.setRowCount(0)

        try:
            adapters = FineTunedModel.objects.all()
            enabled_adapters = self._get_enabled_adapters()

            for adapter in adapters:
                if not adapter.adapter_path or not os.path.exists(
                    adapter.adapter_path
                ):
                    continue

                row = self.ui.adapters_table.rowCount()
                self.ui.adapters_table.insertRow(row)

                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox = QCheckBox()
                checkbox.setChecked(adapter.name in enabled_adapters)
                checkbox.stateChanged.connect(
                    lambda state, name=adapter.name: self._on_adapter_toggled(
                        name, state
                    )
                )
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)

                self.ui.adapters_table.setCellWidget(row, 0, checkbox_widget)

                name_item = QTableWidgetItem(adapter.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.ui.adapters_table.setItem(row, 1, name_item)

                path_item = QTableWidgetItem(adapter.adapter_path)
                path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
                self.ui.adapters_table.setItem(row, 2, path_item)

        except Exception as e:
            self.logger.error(f"Error loading adapters: {e}")

    def _on_adapter_toggled(self, adapter_name: str, state: int):
        """Handle adapter checkbox toggle."""
        self.logger.debug(
            f"Adapter '{adapter_name}' toggled: state={state}, Qt.Checked={Qt.CheckState.Checked.value}, Qt.Unchecked={Qt.CheckState.Unchecked.value}"
        )
        enabled_adapters = self._get_enabled_adapters()
        self.logger.debug(
            f"Current enabled adapters before toggle: {enabled_adapters}"
        )

        if state == Qt.CheckState.Checked.value:
            if adapter_name not in enabled_adapters:
                enabled_adapters.append(adapter_name)
                self.logger.info(f"Enabled adapter: {adapter_name}")
        else:
            if adapter_name in enabled_adapters:
                enabled_adapters.remove(adapter_name)
                self.logger.info(f"Disabled adapter: {adapter_name}")

        self._save_enabled_adapters(enabled_adapters)
        self.logger.debug(f"Saved enabled adapters: {enabled_adapters}")

    def _get_enabled_adapters(self) -> list:
        """Get list of enabled adapter names from QSettings."""
        qs = get_qsettings()
        adapters_json = qs.value("llm_settings/enabled_adapters", "[]")
        self.logger.debug(
            f"Reading enabled adapters from QSettings: {adapters_json}"
        )
        try:
            adapters = json.loads(adapters_json)
            self.logger.debug(f"Parsed enabled adapters: {adapters}")
            return adapters
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing enabled adapters JSON: {e}")
            return []

    def _save_enabled_adapters(self, adapters: list):
        """Save list of enabled adapter names to QSettings."""
        qs = get_qsettings()
        adapters_json = json.dumps(adapters)
        self.logger.debug(
            f"Saving enabled adapters to QSettings: {adapters_json}"
        )
        qs.setValue("llm_settings/enabled_adapters", adapters_json)
        qs.sync()

        # Verify save
        saved = qs.value("llm_settings/enabled_adapters", "[]")
        self.logger.debug(f"Verified saved value: {saved}")
