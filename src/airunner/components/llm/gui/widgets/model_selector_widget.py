from typing import Optional
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QGroupBox,
    QProgressBar,
)

from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.components.model_management.model_registry import (
    ModelProvider,
    ModelType,
)


class ModelSelectorWidget(QWidget):
    """Widget for selecting AI models with hardware requirements display."""

    model_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.resource_manager = ModelResourceManager()
        self._init_ui()
        self._update_hardware_info()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        self._create_hardware_group(layout)
        self._create_model_selection_group(layout)
        self._create_model_info_group(layout)

        layout.addStretch()

    def _create_hardware_group(self, parent_layout: QVBoxLayout) -> None:
        """Create hardware information group."""
        group = QGroupBox("System Hardware")
        layout = QVBoxLayout(group)

        self.vram_label = QLabel()
        self.ram_label = QLabel()
        self.gpu_label = QLabel()

        layout.addWidget(self.vram_label)
        layout.addWidget(self.ram_label)
        layout.addWidget(self.gpu_label)

        parent_layout.addWidget(group)

    def _create_model_selection_group(
        self, parent_layout: QVBoxLayout
    ) -> None:
        """Create model selection controls."""
        group = QGroupBox("Model Selection")
        layout = QVBoxLayout(group)

        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([p.value for p in ModelProvider])
        self.provider_combo.currentTextChanged.connect(
            self._on_provider_changed
        )
        provider_layout.addWidget(self.provider_combo)
        layout.addLayout(provider_layout)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)

        self.auto_select_btn = QPushButton("Auto-Select Best Model")
        self.auto_select_btn.clicked.connect(self._auto_select_model)
        layout.addWidget(self.auto_select_btn)

        parent_layout.addWidget(group)

    def _create_model_info_group(self, parent_layout: QVBoxLayout) -> None:
        """Create model information display."""
        group = QGroupBox("Model Information")
        layout = QVBoxLayout(group)

        self.model_size_label = QLabel()
        self.min_vram_label = QLabel()
        self.rec_vram_label = QLabel()
        self.quantization_label = QLabel()
        self.compatibility_bar = QProgressBar()

        layout.addWidget(self.model_size_label)
        layout.addWidget(self.min_vram_label)
        layout.addWidget(self.rec_vram_label)
        layout.addWidget(self.quantization_label)
        layout.addWidget(QLabel("Compatibility:"))
        layout.addWidget(self.compatibility_bar)

        parent_layout.addWidget(group)

    def _update_hardware_info(self) -> None:
        """Update hardware information display."""
        profile = self.resource_manager.hardware_profiler.get_profile()

        self.vram_label.setText(
            f"VRAM: {profile.available_vram_gb:.1f}GB / {profile.total_vram_gb:.1f}GB"
        )
        self.ram_label.setText(
            f"RAM: {profile.available_ram_gb:.1f}GB / {profile.total_ram_gb:.1f}GB"
        )
        self.gpu_label.setText(f"GPU: {profile.device_name or 'None'}")

    @Slot(str)
    def _on_provider_changed(self, provider_name: str) -> None:
        """Handle provider selection change."""
        try:
            provider = ModelProvider(provider_name)
            self._update_model_list(provider)
        except ValueError:
            pass

    def _update_model_list(self, provider: ModelProvider) -> None:
        """Update available models for selected provider."""
        self.model_combo.clear()
        models = self.resource_manager.model_registry.list_models(
            provider=provider, model_type=ModelType.LLM
        )

        for model in models:
            self.model_combo.addItem(model.name, model.huggingface_id)

    @Slot(str)
    def _on_model_changed(self, model_name: str) -> None:
        """Handle model selection change."""
        model_id = self.model_combo.currentData()
        if model_id:
            self._update_model_info(model_id)
            self.model_selected.emit(model_id)

    def _update_model_info(self, model_id: str) -> None:
        """Update model information display."""
        metadata, quantization, allocation = (
            self.resource_manager.prepare_model_loading(model_id)
        )

        if not metadata:
            return

        self.model_size_label.setText(f"Model Size: {metadata.size_gb:.1f}GB")
        self.min_vram_label.setText(f"Min VRAM: {metadata.min_vram_gb:.1f}GB")
        self.rec_vram_label.setText(
            f"Recommended VRAM: {metadata.recommended_vram_gb:.1f}GB"
        )

        if quantization:
            self.quantization_label.setText(
                f"Auto Quantization: {quantization.description}"
            )

        profile = self.resource_manager.hardware_profiler.get_profile()
        compatibility = self._calculate_compatibility(metadata, profile)
        self.compatibility_bar.setValue(int(compatibility * 100))

    def _calculate_compatibility(self, metadata, profile) -> float:
        """Calculate compatibility score (0.0 to 1.0)."""
        vram_ratio = profile.available_vram_gb / metadata.min_vram_gb
        ram_ratio = profile.available_ram_gb / metadata.min_ram_gb
        return min(1.0, min(vram_ratio, ram_ratio))

    @Slot()
    def _auto_select_model(self) -> None:
        """Auto-select best model for current hardware."""
        try:
            provider = ModelProvider(self.provider_combo.currentText())
            model = self.resource_manager.select_best_model(
                provider=provider, model_type=ModelType.LLM
            )

            if model:
                index = self.model_combo.findData(model.huggingface_id)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
        except ValueError:
            pass
