"""Model Selector Widget with VSCode-style search for provider and model selection.

Provides an improved UI for selecting LLM providers and models with:
- Searchable provider dropdown
- Searchable model dropdown with details
- Model information display (VRAM, context length, capabilities)
- Quick access to Manage Models dialog
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Signal, Slot

from airunner.components.application.gui.widgets.searchable_combo_box import (
    SearchableComboBox,
)
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.enums import ModelService


class ModelSelectorWidget(QWidget):
    """Widget for selecting LLM provider and model with enhanced UI.

    Features:
    - Searchable provider dropdown
    - Searchable model dropdown with filtering
    - Model information display (VRAM, context, capabilities)
    - Manage Models button for advanced operations
    """

    # Signals
    provider_changed = Signal(str)  # Emits provider name
    model_changed = Signal(str, str)  # Emits (provider, model_id)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize model selector widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._current_provider: Optional[str] = None
        self._current_model_id: Optional[str] = None
        self._setup_ui()
        self._populate_providers()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Provider selection
        provider_group = QGroupBox("Provider")
        provider_layout = QVBoxLayout(provider_group)

        self.provider_combo = SearchableComboBox()
        self.provider_combo.setPlaceholderText("Search providers...")
        self.provider_combo.itemSelected.connect(self._on_provider_selected)
        provider_layout.addWidget(self.provider_combo)

        layout.addWidget(provider_group)

        # Model selection
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout(model_group)

        self.model_combo = SearchableComboBox()
        self.model_combo.setPlaceholderText("Search models...")
        self.model_combo.itemSelected.connect(self._on_model_selected)
        model_layout.addWidget(self.model_combo)

        # Model info display
        info_layout = QFormLayout()

        self.vram_label = QLabel("-")
        self.vram_label.setStyleSheet("color: #666;")
        info_layout.addRow("VRAM (4-bit):", self.vram_label)

        self.context_label = QLabel("-")
        self.context_label.setStyleSheet("color: #666;")
        info_layout.addRow("Context:", self.context_label)

        self.tools_label = QLabel("-")
        self.tools_label.setStyleSheet("color: #666;")
        info_layout.addRow("Tool Calling:", self.tools_label)

        model_layout.addLayout(info_layout)

        # Manage Models button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.manage_button = QPushButton("Manage Models...")
        self.manage_button.clicked.connect(self._on_manage_clicked)
        button_layout.addWidget(self.manage_button)

        model_layout.addLayout(button_layout)

        layout.addWidget(model_group)
        layout.addStretch()

    def _populate_providers(self):
        """Populate provider dropdown with available providers."""
        self.provider_combo.clear()

        providers = [
            (
                "Local Models",
                ModelService.LOCAL.value,
                "Run models locally on your hardware",
            ),
            (
                "OpenRouter",
                ModelService.OPENROUTER.value,
                "Access multiple providers through OpenRouter",
            ),
            (
                "Ollama",
                ModelService.OLLAMA.value,
                "Use Ollama for local model serving",
            ),
        ]

        self.provider_combo.addItemsWithData(providers)

    def _populate_models(self, provider: str):
        """Populate model dropdown based on selected provider.

        Args:
            provider: Provider name
        """
        self.model_combo.clear()

        models = LLMProviderConfig.get_models_for_provider(provider)

        for model_id in models:
            display_name = LLMProviderConfig.get_model_display_name(
                provider, model_id
            )

            # Get model info for tooltip
            model_info = LLMProviderConfig.get_model_info(provider, model_id)
            tooltip = None
            if model_info and model_info.get("description"):
                tooltip = model_info["description"]

            if tooltip:
                self.model_combo.addItemWithData(
                    display_name, model_id, tooltip
                )
            else:
                self.model_combo.addItemWithData(display_name, model_id)

    def _update_model_info(self, provider: str, model_id: str):
        """Update model information display.

        Args:
            provider: Provider name
            model_id: Model identifier
        """
        if provider != ModelService.LOCAL.value:
            # For remote providers, show generic info
            self.vram_label.setText("N/A (remote)")
            self.context_label.setText("Varies by model")
            self.tools_label.setText("Check provider docs")
            return

        model_info = LLMProviderConfig.get_model_info(provider, model_id)
        if not model_info or model_id == "custom":
            self.vram_label.setText("-")
            self.context_label.setText("-")
            self.tools_label.setText("-")
            return

        # VRAM info
        vram_4bit = model_info.get("vram_4bit_gb", 0)
        if vram_4bit > 0:
            self.vram_label.setText(f"~{vram_4bit} GB")
        else:
            self.vram_label.setText("Unknown")

        # Context length
        context = model_info.get("context_length", 0)
        if context > 0:
            if context >= 1000000:
                self.context_label.setText(f"{context // 1000000}M tokens")
            elif context >= 1000:
                self.context_label.setText(f"{context // 1000}K tokens")
            else:
                self.context_label.setText(f"{context} tokens")
        else:
            self.context_label.setText("Unknown")

        # Tool calling support
        has_tools = model_info.get("function_calling", False)
        tool_mode = model_info.get("tool_calling_mode", "none")
        if has_tools:
            self.tools_label.setText(f"Yes ({tool_mode})")
        else:
            self.tools_label.setText("No (chat only)")

    @Slot(object)
    def _on_provider_selected(self, provider_data: str):
        """Handle provider selection.

        Args:
            provider_data: Selected provider name
        """
        self._current_provider = provider_data
        self._populate_models(provider_data)
        self.provider_changed.emit(provider_data)

        # Clear model info
        self._update_model_info("", "")

    @Slot(object)
    def _on_model_selected(self, model_data: str):
        """Handle model selection.

        Args:
            model_data: Selected model ID
        """
        if not self._current_provider:
            return

        self._current_model_id = model_data
        self._update_model_info(self._current_provider, model_data)
        self.model_changed.emit(self._current_provider, model_data)

    @Slot()
    def _on_manage_clicked(self):
        """Handle Manage Models button click."""
        from airunner.components.settings.gui.widgets.model_manager_dialog import (
            ManageModelsDialog,
        )

        dialog = ManageModelsDialog(self)

        # Connect signals if needed (download/delete)
        # These would typically be connected to actual download/delete handlers

        dialog.exec()

    def set_provider(self, provider: str):
        """Set current provider.

        Args:
            provider: Provider name
        """
        self.provider_combo.setCurrentData(provider)
        self._current_provider = provider
        self._populate_models(provider)

    def set_model(self, model_id: str):
        """Set current model.

        Args:
            model_id: Model identifier
        """
        self.model_combo.setCurrentData(model_id)
        self._current_model_id = model_id

        if self._current_provider:
            self._update_model_info(self._current_provider, model_id)

    def get_provider(self) -> Optional[str]:
        """Get currently selected provider.

        Returns:
            Provider name or None
        """
        return self._current_provider

    def get_model_id(self) -> Optional[str]:
        """Get currently selected model ID.

        Returns:
            Model ID or None
        """
        return self._current_model_id
