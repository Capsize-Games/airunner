"""Widget displaying real-time model loading status and VRAM usage."""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
)
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)


class ModelStatusWidget(QWidget):
    """Displays active models and memory usage in real-time."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = ModelResourceManager()
        self._setup_ui()
        self._start_refresh_timer()

    def _setup_ui(self):
        """Create the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.title_label = QLabel("<b>Model Resource Status</b>")
        layout.addWidget(self.title_label)

        self.vram_bar = self._create_memory_bar("VRAM")
        layout.addWidget(self.vram_bar)

        self.ram_bar = self._create_memory_bar("RAM")
        layout.addWidget(self.ram_bar)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        self.models_label = QLabel("<b>Active Models:</b>")
        layout.addWidget(self.models_label)

        self.models_container = QWidget()
        self.models_layout = QVBoxLayout(self.models_container)
        self.models_layout.setContentsMargins(0, 0, 0, 0)
        self.models_layout.setSpacing(5)
        layout.addWidget(self.models_container)

        layout.addStretch()

    def _create_memory_bar(self, name: str) -> QWidget:
        """Create a labeled progress bar for memory display."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(f"{name}: 0.0 GB / 0.0 GB")
        label.setObjectName(f"{name.lower()}_label")
        layout.addWidget(label)

        bar = QProgressBar()
        bar.setObjectName(f"{name.lower()}_bar")
        bar.setMaximum(100)
        bar.setValue(0)
        layout.addWidget(bar)

        return container

    def _start_refresh_timer(self):
        """Start 1-second refresh timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_status)
        self.timer.start(1000)

    def _update_status(self):
        """Refresh all status displays."""
        self._update_memory_bars()
        self._update_active_models()

    def _update_memory_bars(self):
        """Update VRAM and RAM usage bars."""
        profile = self.manager.hardware_profiler.get_profile()

        vram_used = profile.total_vram_gb - profile.available_vram_gb
        ram_used = profile.total_ram_gb - profile.available_ram_gb

        self._update_memory_bar("vram", vram_used, profile.total_vram_gb)
        self._update_memory_bar("ram", ram_used, profile.total_ram_gb)

    def _update_memory_bar(self, name: str, used: float, total: float):
        """Update a single memory bar."""
        label = self.findChild(QLabel, f"{name}_label")
        bar = self.findChild(QProgressBar, f"{name}_bar")

        if label and bar and total > 0:
            percentage = int((used / total) * 100)
            label.setText(f"{name.upper()}: {used:.1f} GB / {total:.1f} GB")
            bar.setValue(percentage)

            if percentage > 90:
                bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #d32f2f; }"
                )
            elif percentage > 75:
                bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #f57c00; }"
                )
            else:
                bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #388e3c; }"
                )

    def _update_active_models(self):
        """Update list of active models."""
        while self.models_layout.count():
            child = self.models_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        active_models = self.manager.get_active_models()

        if not active_models:
            no_models_label = QLabel("<i>No models loaded</i>")
            self.models_layout.addWidget(no_models_label)
            return

        for model_info in active_models:
            model_widget = self._create_model_entry(model_info)
            self.models_layout.addWidget(model_widget)

    def _create_model_entry(self, model_info) -> QWidget:
        """Create a single model status entry."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)

        model_name = model_info.model_id.split("/")[-1][:30]
        name_label = QLabel(model_name)
        layout.addWidget(name_label, 1)

        state_text = model_info.state.value.upper()
        state_label = QLabel(state_text)
        state_label.setStyleSheet(self._get_state_style(state_text))
        layout.addWidget(state_label)

        return container

    def _get_state_style(self, state: str) -> str:
        """Get stylesheet for model state."""
        state_colors = {
            "LOADED": "color: #388e3c; font-weight: bold;",
            "LOADING": "color: #f57c00; font-weight: bold;",
            "UNLOADING": "color: #f57c00; font-weight: bold;",
            "BUSY": "color: #1976d2; font-weight: bold;",
            "UNLOADED": "color: #757575;",
        }
        return state_colors.get(state, "")
