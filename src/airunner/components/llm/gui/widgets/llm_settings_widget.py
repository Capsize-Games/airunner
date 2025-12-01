import os
import json
from PySide6.QtCore import Slot, Qt
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
from airunner.components.llm.config.provider_config import LLMProviderConfig


class LLMSettingsWidget(BaseWidget, AIModelMixin):
    widget_class_ = Ui_llm_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.download_manager = None
        self.quantization_dialog = None
        self.initialize_form()
        
        # Hide model/provider controls - they're now in the chat prompt widget
        self._hide_model_provider_controls()
        
        self.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
            self.on_download_complete,
        )
        self.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
            self.on_download_failed,
        )
        self.register(
            SignalCode.LLM_QUANTIZATION_PROGRESS,
            self.on_quantization_progress,
        )
        self.register(
            SignalCode.LLM_QUANTIZATION_COMPLETE,
            self.on_quantization_complete,
        )
        self.register(
            SignalCode.LLM_QUANTIZATION_FAILED,
            self.on_quantization_failed,
        )
        self._setup_adapters_table()
        self._load_adapters()
        self._setup_quantization_dropdown()
        self._update_quantize_button_state()  # Initialize button state

    def _hide_model_provider_controls(self) -> None:
        """Hide model and provider controls since they're now in chat prompt widget."""
        # Hide provider group box (contains model_service)
        if hasattr(self.ui, "groupBox"):
            self.ui.groupBox.setVisible(False)
        # Hide model selection group (contains model_dropdown, model_path, etc.)
        if hasattr(self.ui, "model_selection_group"):
            self.ui.model_selection_group.setVisible(False)
        # Hide the LLM Settings title since this panel now only has advanced settings
        if hasattr(self.ui, "llm_settings_title"):
            self.ui.llm_settings_title.setVisible(False)
        # Hide the line separator below title
        if hasattr(self.ui, "line_2"):
            self.ui.line_2.setVisible(False)

    @Slot(str)
    def on_model_path_textChanged(self, val: str):
        self.update_llm_generator_settings(model_path=val)
        self._update_quantize_button_state()  # Update when path changes

    @Slot(str)
    def on_model_service_currentTextChanged(self, model_service: str):
        self.api.llm.model_changed(model_service)
        self._update_model_dropdown_visibility()
        self._populate_model_dropdown(model_service)

    @Slot(str)
    def on_model_dropdown_currentTextChanged(self, display_text: str):
        """Handle model selection from dropdown."""
        provider = self.ui.model_service.currentText()

        # Get the actual model_id from the current item's data
        current_index = self.ui.model_dropdown.currentIndex()
        if current_index < 0:
            return

        model_id = self.ui.model_dropdown.itemData(current_index)
        if not model_id:
            model_id = display_text  # Fallback to display text

        # Update model path based on selection
        if provider == ModelService.LOCAL.value:
            if model_id == "custom":
                # Allow user to enter custom path
                self.ui.model_path.setEnabled(True)
                self.ui.model_path.setPlaceholderText(
                    "Enter custom model path"
                )
                self.ui.download_model_button.setVisible(False)
            else:
                # Use standard path for known models
                model_info = LLMProviderConfig.get_model_info(
                    provider, model_id
                )
                if model_info:
                    model_name = model_info["name"]
                    self.update_llm_generator_settings(
                        model_version=model_name
                    )
                    model_path = os.path.join(
                        os.path.expanduser(self.path_settings.base_path),
                        f"text/models/llm/causallm/{model_name}",
                    )
                    print(f"  Setting model_path to: {model_path}")
                    self.ui.model_path.setText(model_path)
                    self.ui.model_path.setEnabled(False)

                    # Download button visibility/state handled by _update_quantize_button_state
                    self.ui.download_model_button.setVisible(True)
                    self.ui.download_model_button.setText(
                        f"Download {model_info['name']}"
                    )
                else:
                    self.logger.warning(
                        f"No model_info found for model_id: {model_id}"
                    )
        else:
            # For remote providers, allow custom input
            self.ui.model_path.setEnabled(True)
            if model_id != "custom":
                self.ui.model_path.setText(model_id)
            self.ui.download_model_button.setVisible(False)

        # Update model info label
        self._update_model_info_label()

        # Update quantize button state
        self._update_quantize_button_state()

    @Slot()
    def on_download_model_button_clicked(self):
        """Handle download button click - show download dialog."""
        provider = self.ui.model_service.currentText()

        # Get the actual model_id from the current item's data
        current_index = self.ui.model_dropdown.currentIndex()
        if current_index < 0:
            return

        model_id = self.ui.model_dropdown.itemData(current_index)
        if not model_id:
            model_id = self.ui.model_dropdown.currentText()  # Fallback

        if provider != ModelService.LOCAL.value:
            return

        model_info = LLMProviderConfig.get_model_info(provider, model_id)
        if not model_info or not model_info.get("repo_id"):
            self.logger.error(f"No repo_id found for model: {model_id}")
            return

        # Get quantization type from dropdown
        quant_index = self.ui.quantization_dropdown.currentIndex()
        
        # Check if GGUF is selected (index 3)
        if quant_index == 3:
            # GGUF download - check if GGUF is available for this model
            if not LLMProviderConfig.has_gguf_support(provider, model_id):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "GGUF Not Available",
                    f"GGUF format is not available for {model_info['name']}.\n\n"
                    "Please select a different quantization option.",
                )
                return
            
            gguf_info = LLMProviderConfig.get_gguf_info(provider, model_id)
            model_name = model_info["name"]
            model_path = os.path.join(
                os.path.expanduser(self.settings.base_path),
                f"text/models/llm/causallm/{model_name}",
            )
            
            # Emit signal for GGUF download
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                {
                    "model_name": model_name,
                    "model_path": model_path,
                    "repo_id": gguf_info["repo_id"],
                    "model_type": "gguf",  # Special type for GGUF
                    "gguf_filename": gguf_info["filename"],
                    "quantization_bits": 0,  # Not used for GGUF
                },
            )
            return

        # Standard HuggingFace download
        index_to_quant = {0: 2, 1: 4, 2: 8}
        quantization_bits = index_to_quant.get(quant_index, 4)

        model_name = model_info["name"]
        model_path = os.path.join(
            os.path.expanduser(self.settings.base_path),
            f"text/models/llm/causallm/{model_name}",
        )

        # Emit signal to show download dialog (same as when model is required during chat)
        self.emit_signal(
            SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
            {
                "model_name": model_name,
                "model_path": model_path,
                "repo_id": model_info["repo_id"],
                "model_type": model_info.get("model_type", "llm"),
                "quantization_bits": quantization_bits,
            },
        )

    @Slot()
    def on_start_quantize_button_clicked(self):
        """Handle manual quantize button click - start disk-based quantization or GGUF download."""
        from PySide6.QtWidgets import QMessageBox

        model_path = self.ui.model_path.text()

        # Get selected quantization level
        quant_index = self.ui.quantization_dropdown.currentIndex()
        self.logger.info(f"Quantization button clicked, quant_index={quant_index}")
        
        # Check if GGUF is selected (index 3)
        if quant_index == 3:
            # GGUF requires downloading a pre-quantized model, not local quantization
            # Trigger download flow instead
            provider = self.ui.model_service.currentText()
            current_index = self.ui.model_dropdown.currentIndex()
            self.logger.info(f"GGUF selected: provider={provider}, current_index={current_index}")
            
            if current_index < 0:
                QMessageBox.warning(
                    self,
                    "GGUF Download",
                    "Please select a model first.",
                )
                return
            
            model_id = self.ui.model_dropdown.itemData(current_index)
            self.logger.info(f"GGUF model_id={model_id}")
            if not model_id or model_id == "custom":
                QMessageBox.warning(
                    self,
                    "GGUF Download",
                    "GGUF format is only available for predefined models.\n"
                    "Custom models cannot be converted to GGUF locally.",
                )
                return
            
            # Check if GGUF is available for this model
            # Use "local" as provider since model_service shows display name like "Local"
            provider_key = "local"
            has_gguf = LLMProviderConfig.has_gguf_support(provider_key, model_id)
            self.logger.info(f"has_gguf_support({provider_key}, {model_id}) = {has_gguf}")
            if not has_gguf:
                QMessageBox.warning(
                    self,
                    "GGUF Not Available",
                    f"GGUF format is not available for this model.\n\n"
                    "Please select a different quantization option.",
                )
                return
            
            # Confirm GGUF download
            gguf_info = LLMProviderConfig.get_gguf_info(provider_key, model_id)
            model_info = LLMProviderConfig.get_model_info(provider_key, model_id)
            self.logger.info(f"GGUF info: {gguf_info}, model_info: {model_info.get('name', 'N/A')}")
            
            reply = QMessageBox.question(
                self,
                "Download GGUF Model",
                f"This will download the GGUF version of {model_info.get('name', model_id)}.\n\n"
                f"GGUF models are pre-quantized and smaller than BitsAndBytes quantization.\n"
                f"File: {gguf_info['filename']}\n\n"
                f"Continue with GGUF download?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("GGUF download cancelled by user")
                return
            
            # Trigger GGUF download
            model_name = model_info["name"]
            download_path = os.path.join(
                os.path.expanduser(self.path_settings.base_path),
                f"text/models/llm/causallm/{model_name}",
            )
            
            self.logger.info(f"Emitting LLM_MODEL_DOWNLOAD_REQUIRED for GGUF: {model_name} -> {download_path}")
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                {
                    "model_name": model_name,
                    "model_path": download_path,
                    "repo_id": gguf_info["repo_id"],
                    "model_type": "gguf",
                    "gguf_filename": gguf_info["filename"],
                    "quantization_bits": 0,
                },
            )
            return

        # Standard BitsAndBytes quantization flow
        if not model_path or not self._check_safetensors_exist(model_path):
            QMessageBox.warning(
                self,
                "Quantization Error",
                "Model files not found. Please download the model first.",
            )
            return

        index_to_bits = {0: "2bit", 1: "4bit", 2: "8bit"}
        bits = index_to_bits.get(quant_index, "4bit")

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Manual Quantization",
            f"This will create a {bits} quantized version of the model on disk.\n\n"
            f"Note: Automatic quantization during model loading is recommended instead, "
            f"as it uses less disk space.\n\nContinue with manual quantization?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Emit quantization signal
        self.logger.info(
            f"Starting manual {bits} quantization for model at: {model_path}"
        )
        self.emit_signal(
            SignalCode.LLM_START_QUANTIZATION,
            {
                "model_path": model_path,
                "bits": bits,
            },
        )

    @Slot(dict)
    def on_download_complete(self, data):
        """Handle download completion."""
        model_path = data.get("model_path", "")

        # Update model path - download button state handled by _update_quantize_button_state
        if model_path:
            self.ui.model_path.setText(model_path)
            self.logger.info(f"Model downloaded successfully: {model_path}")

            # Update quantize button state
            self._update_quantize_button_state()

    @Slot(dict)
    def on_download_failed(self, data):
        """Handle download failure."""
        error = data.get("error", "Unknown error")
        # Only log - the download dialog handles user-facing error display
        self.logger.error(f"Download failed: {error}")

    @Slot(bool)
    def toggle_use_cache(self, val: bool):
        self.update_chatbot("use_cache", val)

    @Slot(bool)
    def on_use_mode_routing_toggled(self, val: bool):
        """Handle mode-based routing toggle."""
        self.update_llm_generator_settings(use_mode_routing=val)

    @Slot(bool)
    def on_enable_trajectory_logging_toggled(self, val: bool):
        """Handle trajectory logging toggle."""
        self.update_llm_generator_settings(enable_trajectory_logging=val)

    @Slot(str)
    def on_mode_override_currentTextChanged(self, text: str):
        """Handle mode override selection."""
        # Map display text to internal mode value
        mode_map = {
            "Auto (Default)": None,
            "Author": "author",
            "Code": "code",
            "Research": "research",
            "QA": "qa",
            "General": "general",
        }
        mode_value = mode_map.get(text)
        self.update_llm_generator_settings(mode_override=mode_value)

    def _update_model_dropdown_visibility(self):
        """Update visibility of model selection widgets based on provider."""
        provider = self.ui.model_service.currentText()

        # Always show model selection group
        self.ui.model_selection_group.setVisible(True)

        # Populate model dropdown
        self._populate_model_dropdown(provider)

    def _populate_model_dropdown(self, provider: str):
        """Populate the model dropdown based on selected provider."""
        self.ui.model_dropdown.blockSignals(True)
        self.ui.model_dropdown.clear()

        models = LLMProviderConfig.get_models_for_provider(provider)

        for model_id in models:
            display_name = LLMProviderConfig.get_model_display_name(
                provider, model_id
            )
            self.ui.model_dropdown.addItem(display_name, model_id)

        # Set current model if available
        current_path = self.llm_generator_settings.model_path
        if provider == ModelService.LOCAL.value and current_path:
            # Try to match current path to a known model
            for model_id, model_info in LLMProviderConfig.LOCAL_MODELS.items():
                if model_info["name"] in current_path:
                    index = self.ui.model_dropdown.findData(model_id)
                    if index >= 0:
                        self.ui.model_dropdown.setCurrentIndex(index)
                    break

        self.ui.model_dropdown.blockSignals(False)

        # Update model path field behavior
        if provider == ModelService.LOCAL.value:
            self.ui.model_path.setEnabled(False)
            self.ui.download_model_button.setVisible(True)
        else:
            self.ui.model_path.setEnabled(True)
            self.ui.download_model_button.setVisible(False)

    def _toggle_model_path_visibility(self, val: bool):
        """Deprecated - kept for compatibility."""

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

        # Populate model dropdown for current provider
        provider = self.llm_generator_settings.model_service
        self._populate_model_dropdown(provider)

        # Set default model path if empty
        model_path = self.llm_generator_settings.model_path
        if not model_path:
            # Set a sensible default: Qwen3 8B (best overall for agent tasks)
            default_model_id = "qwen3-8b"
            model_info = LLMProviderConfig.get_model_info(
                provider, default_model_id
            )
            if model_info:
                model_name = model_info["name"]
                model_path = os.path.join(
                    os.path.expanduser(self.path_settings.base_path),
                    f"text/models/llm/causallm/{model_name}",
                )
                # Save to database
                self.update_llm_generator_settings(model_path=model_path)
                # Set dropdown to default model
                self.ui.model_dropdown.setCurrentText(default_model_id)

        # QLineEdit requires setText, not setCurrentText
        self.ui.model_path.setText(model_path or "")

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

    def _setup_quantization_dropdown(self):
        """Setup quantization dropdown - GGUF only mode.
        
        We hide quantization options and always use GGUF for simplicity.
        GGUF is the best choice for consumer hardware: efficient, single-file,
        supports CPU+GPU hybrid inference.
        """
        # Hide quantization UI - we're GGUF-only now
        if hasattr(self.ui, "quantization_label"):
            self.ui.quantization_label.setVisible(False)
        if hasattr(self.ui, "quantization_dropdown"):
            self.ui.quantization_dropdown.setVisible(False)
        if hasattr(self.ui, "start_quantize_button"):
            self.ui.start_quantize_button.setVisible(False)
        if hasattr(self.ui, "delete_safetensors_button"):
            self.ui.delete_safetensors_button.setVisible(False)
        if hasattr(self.ui, "delete_quantized_button"):
            self.ui.delete_quantized_button.setVisible(False)
        
        # Always use GGUF (quantization_bits=0)
        qs = get_qsettings()
        qs.setValue("llm_settings/quantization_bits", 0)
        qs.sync()
        self.update_llm_generator_settings(quantization_bits=0)

    @Slot(int)
    def on_quantization_changed(self, index: int):
        """Handle quantization selection change - always use GGUF."""
        # GGUF-only mode: ignore index, always use 0 (GGUF)
        quantization_bits = 0

        # Update settings
        self.update_llm_generator_settings(quantization_bits=quantization_bits)
        # Persist selection to QSettings
        try:
            qs = get_qsettings()
            qs.setValue("llm_settings/quantization_bits", quantization_bits)
            qs.sync()
        except Exception:
            pass

        # Update model info label
        self._update_model_info_label()

    def _update_model_info_label(self):
        """Update the model info label with VRAM, context, and capabilities."""
        provider = self.ui.model_service.currentText()
        current_index = self.ui.model_dropdown.currentIndex()

        if current_index < 0 or provider != ModelService.LOCAL.value:
            self.ui.model_info_label.setText(
                "Select a local model to see details"
            )
            return

        model_id = self.ui.model_dropdown.itemData(current_index)
        if not model_id or model_id == "custom":
            self.ui.model_info_label.setText(
                "Custom model - no info available"
            )
            return

        model_info = LLMProviderConfig.get_model_info(provider, model_id)
        if not model_info:
            self.ui.model_info_label.setText("Model info not available")
            return

        # GGUF mode: use 4-bit equivalent VRAM estimate (GGUF Q4_K_M is similar)
        vram = LLMProviderConfig.get_vram_for_quantization(
            provider, model_id, 4  # Q4_K_M is roughly equivalent to 4-bit
        )

        # Get context length
        context = model_info.get("context_length", 0)
        if context >= 1000000:
            context_str = f"{context // 1000000}M"
        elif context >= 1000:
            context_str = f"{context // 1000}K"
        else:
            context_str = str(context)

        # Get tool calling mode with appropriate icon
        tool_mode = model_info.get("tool_calling_mode", "react")
        tool_mode_icons = {
            "native": "⚡",  # Lightning bolt for native (fastest/best)
            "json": "📋",  # Clipboard for JSON (structured)
            "react": "📝",  # Memo for ReAct (text-based)
        }
        tool_icon = tool_mode_icons.get(tool_mode, "")

        # Capitalize mode name for display
        tool_mode_display = (
            tool_mode.upper()
            if tool_mode == "json"
            else tool_mode.capitalize()
        )

        # Get function calling status
        func_calling = model_info.get("function_calling", False)
        if func_calling:
            tool_info = f"{tool_mode_display} {tool_icon}"
        else:
            tool_info = "No"

        # Build info string (GGUF format)
        info = f"~{vram} GB VRAM | {context_str} context | Tools: {tool_info}"
        self.ui.model_info_label.setText(info)

    def update_chatbot(self, key, val):
        chatbot = self.chatbot
        try:
            setattr(chatbot, key, val)
        except TypeError:
            self.logger.error(f"Attribute {key} does not exist in Chatbot")
            return
        Chatbot.objects.update(pk=chatbot.id, **{key: val})

    def _setup_adapters_table(self):
        """Configure the adapters table columns and behavior."""
        self.ui.adapters_table.horizontalHeader().setStretchLastSection(True)
        self.ui.adapters_table.setColumnWidth(0, 80)
        self.ui.adapters_table.setColumnWidth(1, 200)

    @Slot()
    def on_refresh_adapters_button_clicked(self):
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

    def _check_safetensors_exist(self, model_path: str) -> bool:
        """Check if original .safetensors files exist at model path."""
        if not model_path:
            self.logger.debug("No model path provided")
            return False

        if not os.path.exists(model_path):
            self.logger.debug(f"Model path does not exist: {model_path}")
            return False

        import glob

        safetensors_files = glob.glob(
            os.path.join(model_path, "*.safetensors")
        )
        has_files = len(safetensors_files) > 0
        self.logger.debug(
            f"Checking safetensors in {model_path}: found {len(safetensors_files)} files, result={has_files}"
        )
        return has_files

    def _is_model_loaded(self, model_path: str) -> bool:
        """Check if a model is currently loaded."""
        try:
            current_loaded = self.llm_generator_settings.model_path
            return current_loaded == model_path
        except Exception:
            return False

    def _check_quantized_models_exist(self, model_path: str) -> bool:
        """Check if quantized model directories exist (e.g., model-2bit, model-4bit, model-8bit)."""
        if not model_path or not os.path.exists(model_path):
            return False

        base_dir = os.path.dirname(model_path)
        model_name = os.path.basename(model_path)

        # Check for quantized directories
        for suffix in ["2bit", "4bit", "8bit"]:
            quant_path = os.path.join(base_dir, f"{model_name}-{suffix}")
            if os.path.exists(quant_path) and os.path.isdir(quant_path):
                return True

        return False

    def _update_quantize_button_state(self):
        """Enable/disable quantize button, download button, delete buttons, and combobox based on file existence."""
        current_path = self.ui.model_path.text()
        has_safetensors = self._check_safetensors_exist(current_path)
        has_quantized = self._check_quantized_models_exist(current_path)

        # Download button only enabled when model files DON'T exist
        self.ui.download_model_button.setEnabled(not has_safetensors)

        # Manual quantize button enabled when original safetensors exist
        self.ui.start_quantize_button.setEnabled(has_safetensors)

        # Delete safetensors button only enabled when safetensors exist
        self.ui.delete_safetensors_button.setEnabled(has_safetensors)

        # Delete quantized button only enabled when quantized models exist
        self.ui.delete_quantized_button.setEnabled(has_quantized)

        # Quantization dropdown is always enabled - used during model loading
        self.ui.quantization_dropdown.setEnabled(True)
        self.ui.quantization_dropdown.setToolTip(
            "Select quantization level - applied automatically when loading the model (uses bitsandbytes)"
        )

        if has_safetensors:
            self.ui.download_model_button.setToolTip(
                "Model already downloaded"
            )
            self.ui.start_quantize_button.setToolTip(
                "Manually quantize model to disk (creates separate files). Automatic quantization during loading is recommended instead."
            )
            self.ui.delete_safetensors_button.setToolTip(
                "Delete original .safetensors files to save disk space"
            )
        else:
            self.ui.download_model_button.setToolTip(
                "Download model from HuggingFace"
            )
            self.ui.start_quantize_button.setToolTip(
                "Download the model first before quantizing"
            )
            self.ui.delete_safetensors_button.setToolTip(
                "No original safetensors files to delete"
            )

        if has_quantized:
            self.ui.delete_quantized_button.setToolTip(
                "Delete quantized model versions (2bit, 4bit, 8bit)"
            )
        else:
            self.ui.delete_quantized_button.setToolTip(
                "No quantized models found"
            )

    @Slot(dict)
    def on_quantization_progress(self, data):
        """Handle quantization progress updates."""
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt

        stage = data.get("stage", "")
        progress = data.get("progress", 0.0)
        bits = data.get("bits", "")
        data.get("current", 0)
        data.get("total", 1)

        self.logger.info(
            f"Quantization {bits}-bit: {stage} - {int(progress)}%"
        )

        # Create progress dialog on first progress update
        if self.quantization_dialog is None:
            self.quantization_dialog = QProgressDialog(
                "Quantizing model...", None, 0, 100, self
            )
            self.quantization_dialog.setWindowTitle("Model Quantization")
            self.quantization_dialog.setWindowModality(
                Qt.WindowModality.WindowModal
            )
            self.quantization_dialog.setAutoClose(False)
            self.quantization_dialog.setAutoReset(False)
            self.quantization_dialog.setMinimumDuration(0)
            self.quantization_dialog.show()

        # Update progress
        self.quantization_dialog.setLabelText(f"{stage}")
        self.quantization_dialog.setValue(int(progress))

    @Slot(dict)
    def on_quantization_complete(self, data):
        """Handle quantization completion."""
        bits = data.get("bits", "")
        output_path = data.get("output_path", "")

        self.logger.info(f"{bits}-bit quantization complete: {output_path}")

        # Close progress dialog
        if self.quantization_dialog is not None:
            self.quantization_dialog.close()
            self.quantization_dialog = None

        # Update button state
        self._update_quantize_button_state()

    @Slot(dict)
    def on_quantization_failed(self, data):
        """Handle quantization failure."""
        error = data.get("error", "Unknown error")
        bits = data.get("bits", "")

        # Just log - the manager will try other quantizations
        self.logger.warning(
            f"{bits} quantization failed (will try others): {error}"
        )

    @Slot()
    def on_delete_safetensors_button_clicked(self):
        """Handle delete safetensors button click - delete original model files after confirmation."""
        from PySide6.QtWidgets import QMessageBox

        model_path = self.ui.model_path.text()

        if not model_path or not self._check_safetensors_exist(model_path):
            return

        # Check if model is currently loaded
        if self._is_model_loaded(model_path):
            QMessageBox.warning(
                self,
                "Model In Use",
                "Cannot delete files while the model is loaded.\n\n"
                "Please unload the model first, then try again.",
            )
            return

        # Count files to be deleted
        import glob

        safetensors_files = glob.glob(
            os.path.join(model_path, "*.safetensors")
        )
        file_count = len(safetensors_files)

        # Calculate total size
        total_size = sum(
            os.path.getsize(f) for f in safetensors_files if os.path.exists(f)
        )
        size_gb = total_size / (1024**3)

        # Show confirmation dialog
        reply = QMessageBox.warning(
            self,
            "Delete Original Safetensors",
            f"This will permanently delete {file_count} original .safetensors files ({size_gb:.2f} GB).\n\n"
            f"Location: {model_path}\n\n"
            f"WARNING: This action cannot be undone!\n\n"
            f"Only delete these files if you have already created quantized versions.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete the files
        deleted_count = 0
        failed_files = []

        for file_path in safetensors_files:
            try:
                os.remove(file_path)
                deleted_count += 1
                self.logger.info(f"Deleted: {file_path}")
            except Exception as e:
                failed_files.append((file_path, str(e)))
                self.logger.error(f"Failed to delete {file_path}: {e}")

        # Show result
        if failed_files:
            error_msg = "\n".join(
                [f"{os.path.basename(f)}: {err}" for f, err in failed_files]
            )
            QMessageBox.warning(
                self,
                "Deletion Incomplete",
                f"Deleted {deleted_count} of {file_count} files.\n\n"
                f"Failed to delete:\n{error_msg}",
            )
        else:
            QMessageBox.information(
                self,
                "Deletion Complete",
                f"Successfully deleted {deleted_count} original .safetensors files ({size_gb:.2f} GB freed).",
            )

        # Update button state
        self._update_quantize_button_state()

    @Slot()
    def on_delete_quantized_button_clicked(self):
        """Handle delete quantized button click - delete quantized model directories."""
        from PySide6.QtWidgets import QMessageBox
        import shutil

        model_path = self.ui.model_path.text()

        if not model_path:
            return

        # Check if any quantized models are currently loaded
        base_dir = os.path.dirname(model_path)
        model_name = os.path.basename(model_path)

        # Find all quantized directories
        quantized_dirs = []
        total_size = 0

        for suffix in ["2bit", "4bit", "8bit"]:
            quant_path = os.path.join(base_dir, f"{model_name}-{suffix}")
            if os.path.exists(quant_path) and os.path.isdir(quant_path):
                # Check if this specific quantized model is loaded
                if self._is_model_loaded(quant_path):
                    QMessageBox.warning(
                        self,
                        "Model In Use",
                        f"Cannot delete {suffix} quantized model while it is loaded.\n\n"
                        "Please unload the model first, then try again.",
                    )
                    return

                # Calculate directory size
                dir_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(quant_path)
                    for filename in filenames
                )
                total_size += dir_size
                quantized_dirs.append((quant_path, suffix, dir_size))

        if not quantized_dirs:
            QMessageBox.information(
                self,
                "No Quantized Models",
                "No quantized model directories found.",
            )
            return

        size_gb = total_size / (1024**3)

        # Show confirmation dialog
        dir_list = "\n".join(
            [f"  • {suffix}" for _, suffix, _ in quantized_dirs]
        )
        reply = QMessageBox.warning(
            self,
            "Delete Quantized Models",
            f"This will permanently delete {len(quantized_dirs)} quantized model version(s):\n\n"
            f"{dir_list}\n\n"
            f"Total size: {size_gb:.2f} GB\n\n"
            f"Location: {base_dir}\n\n"
            f"WARNING: This action cannot be undone!\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete the directories
        deleted_count = 0
        failed_dirs = []

        for quant_path, suffix, _ in quantized_dirs:
            try:
                shutil.rmtree(quant_path)
                deleted_count += 1
                self.logger.info(f"Deleted quantized model: {quant_path}")
            except Exception as e:
                failed_dirs.append((suffix, str(e)))
                self.logger.error(f"Failed to delete {quant_path}: {e}")

        # Show result
        if failed_dirs:
            error_msg = "\n".join(
                [f"{suffix}: {err}" for suffix, err in failed_dirs]
            )
            QMessageBox.warning(
                self,
                "Deletion Incomplete",
                f"Deleted {deleted_count} of {len(quantized_dirs)} quantized models.\n\n"
                f"Failed to delete:\n{error_msg}",
            )
        else:
            QMessageBox.information(
                self,
                "Deletion Complete",
                f"Successfully deleted {deleted_count} quantized model(s) ({size_gb:.2f} GB freed).",
            )

        # Update button state
        self._update_quantize_button_state()

    @Slot(dict)
    def on_quantization_failed(self, data):
        """Handle quantization failure."""
        error = data.get("error", "Unknown error")
        bits = data.get("bits", "")
        self.logger.error(f"{bits}-bit quantization failed: {error}")
