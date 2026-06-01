"""Widget displaying real-time model loading status and VRAM usage."""

from __future__ import annotations

import os

import airunner.feather_rc  # noqa: F401

from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QPushButton,
)
from airunner.components.icons.managers.icon_manager import IconManager
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.enums import SignalCode
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.components.llm.config.provider_config import (
    LLMProviderConfig,
)
from airunner.daemon_client.resource_store import get_resource_store


_UNLOAD_SIGNALS = {
    "art": SignalCode.SD_UNLOAD_SIGNAL,
    "controlnet": SignalCode.CONTROLNET_UNLOAD_SIGNAL,
    "llm": SignalCode.LLM_UNLOAD_SIGNAL,
    "llmmodel": SignalCode.LLM_UNLOAD_SIGNAL,
    "ragembedding": SignalCode.RAG_UNLOAD_SIGNAL,
    "rmbg": SignalCode.RMBG_UNLOAD_SIGNAL,
    "rmbgmodel": SignalCode.RMBG_UNLOAD_SIGNAL,
    "safetychecker": SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL,
    "sd": SignalCode.SD_UNLOAD_SIGNAL,
    "sdcontrolnet": SignalCode.CONTROLNET_UNLOAD_SIGNAL,
    "sdmodel": SignalCode.SD_UNLOAD_SIGNAL,
    "speechtotext": SignalCode.STT_UNLOAD_SIGNAL,
    "stt": SignalCode.STT_UNLOAD_SIGNAL,
    "sttmodel": SignalCode.STT_UNLOAD_SIGNAL,
    "texttoimage": SignalCode.SD_UNLOAD_SIGNAL,
    "texttospeech": SignalCode.TTS_DISABLE_SIGNAL,
    "tts": SignalCode.TTS_DISABLE_SIGNAL,
    "ttsmodel": SignalCode.TTS_DISABLE_SIGNAL,
}


class ModelStatusWidget(QWidget):
    """Displays active models and memory usage in real-time."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager: ModelResourceManager | None = None
        self.icon_manager = IconManager([], self)
        self.signal_mediator = SignalMediator()
        self._setup_ui()
        self._start_refresh_timer()

    def _get_manager(self) -> ModelResourceManager:
        """Create the shared resource manager on first refresh."""
        if self.manager is None:
            self.manager = ModelResourceManager()
        return self.manager

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
        self.timer.start(10)

    def _update_status(self):
        """Refresh all status displays."""
        self._update_memory_bars()
        self._update_active_models()

    def _update_memory_bars(self):
        """Update VRAM and RAM usage bars."""
        profile = self._get_manager().hardware_profiler.get_profile()

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

        active_models = self._get_manager().get_active_models()

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
        layout.setSpacing(8)

        model_name = self._display_model_name(model_info)
        name_label = QLabel(model_name)
        layout.addWidget(name_label, 1)

        state_text = model_info.state.value.upper()
        state_label = QLabel(state_text)
        state_label.setStyleSheet(self._get_state_style(state_text))
        layout.addWidget(state_label)

        unload_button = self._create_unload_button(model_info)
        layout.addWidget(unload_button)

        return container

    def _create_unload_button(self, model_info) -> QPushButton:
        """Return one unload button for an active-model row."""
        button = QPushButton()
        button.setToolTip("Unload")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(24, 24)
        button.setIconSize(QSize(16, 16))
        button.setFlat(True)
        button.setIcon(self._unload_icon())

        unload_request = self._resolve_unload_request(model_info)
        if unload_request is None:
            button.setEnabled(False)
            button.setToolTip("Unload unavailable for this model")
            return button

        if not self._can_unload_model(model_info):
            button.setEnabled(False)
            button.setToolTip(
                "Unload is available once the model is loaded"
            )
            return button

        button.clicked.connect(
            lambda _checked=False, info=model_info: self._unload_model(info)
        )
        return button

    @classmethod
    def _display_model_name(cls, model_info) -> str:
        """Return the user-facing label for one active-model row."""
        raw_model_id = str(getattr(model_info, "model_id", "") or "")
        normalized_type = cls._normalize_model_type(
            getattr(model_info, "model_type", "")
        )
        if normalized_type == "ragembedding":
            short_name = cls._short_model_name(raw_model_id) or "e5-large"
            return f"RAG Embeddings ({short_name})"[:30]
        if normalized_type in {"llm", "llmmodel"}:
            display_name = cls._resolve_llm_display_name(raw_model_id)
            if display_name:
                return display_name[:30]
        return cls._short_model_name(raw_model_id)

    @staticmethod
    def _short_model_name(model_id: str) -> str:
        """Collapse one raw model identifier into a short label."""
        trimmed = str(model_id or "").rstrip("/\\")
        if not trimmed:
            return ""
        return os.path.basename(trimmed)[:30]

    @staticmethod
    def _resolve_llm_display_name(model_id: str) -> str:
        """Resolve one configured LLM display name for the status row."""
        settings = None
        try:
            settings = get_resource_store().get_singleton(
                "LLMGeneratorSettings",
                create_if_missing=True,
            )
        except Exception:
            settings = None

        candidate_ids = []
        basename = os.path.basename(str(model_id or "").rstrip("/\\"))
        for value in (
            model_id,
            basename,
            getattr(settings, "model_id", ""),
            getattr(settings, "model_version", ""),
            getattr(settings, "model_path", ""),
        ):
            candidate = str(value or "").strip()
            if not candidate:
                continue
            resolved = LLMProviderConfig.resolve_model_id("local", candidate)
            if resolved and resolved not in candidate_ids:
                candidate_ids.append(resolved)

        for candidate_id in candidate_ids:
            model_info = LLMProviderConfig.get_model_info(
                "local",
                candidate_id,
            )
            display_name = str(model_info.get("name", "") or "").strip()
            if display_name:
                return display_name

        model_version = str(
            getattr(settings, "model_version", "") or ""
        ).strip()
        return model_version

    @staticmethod
    def _can_unload_model(model_info) -> bool:
        """Return whether one active-model row can be unloaded now."""
        state = getattr(model_info, "state", None)
        state_value = getattr(state, "value", "").strip().lower()
        if state_value:
            return state_value == "loaded"
        return bool(getattr(model_info, "can_unload", False))

    @staticmethod
    def _normalize_model_type(model_type) -> str:
        """Normalize one model type string for signal lookup."""
        value = getattr(model_type, "name", model_type)
        return "".join(
            character
            for character in str(value or "").lower()
            if character.isalnum()
        )

    @classmethod
    def _resolve_unload_request(cls, model_info):
        """Resolve one active model into its unload signal and payload."""
        normalized_type = cls._normalize_model_type(
            getattr(model_info, "model_type", "")
        )
        signal_code = _UNLOAD_SIGNALS.get(normalized_type)
        if signal_code is None:
            return None

        payload = {}
        if signal_code is SignalCode.RMBG_UNLOAD_SIGNAL:
            payload["model_id"] = getattr(model_info, "model_id", "")
        return signal_code, payload

    def _unload_model(self, model_info) -> bool:
        """Emit one unload request for the selected active model."""
        unload_request = ModelStatusWidget._resolve_unload_request(
            model_info
        )
        if unload_request is None:
            return False

        signal_code, payload = unload_request
        if signal_code is SignalCode.LLM_UNLOAD_SIGNAL:
            if ModelStatusWidget._unload_llm_via_api(self, payload):
                return True
        if signal_code is SignalCode.RAG_UNLOAD_SIGNAL:
            if ModelStatusWidget._unload_rag_via_api(self):
                return True
        self.signal_mediator.emit_signal(signal_code, payload)
        return True

    @staticmethod
    def _main_window_api(widget) -> object:
        """Return one API reference from the enclosing main window."""
        current = widget
        visited = set()
        while current is not None and id(current) not in visited:
            visited.add(id(current))
            api = getattr(current, "api", None)
            if api is not None:
                return api
            parent_getter = getattr(current, "parentWidget", None)
            if callable(parent_getter):
                current = parent_getter()
                continue
            current = None

        window_getter = getattr(widget, "window", None)
        if callable(window_getter):
            window = window_getter()
            api = getattr(window, "api", None)
            if api is not None:
                return api
        return None

    @staticmethod
    def _current_gui_api(widget=None):
        """Return the live GUI API instance when available."""
        if widget is not None:
            api = ModelStatusWidget._main_window_api(widget)
            if api is not None:
                return api

        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                main_window = getattr(app, "main_window", None)
                api = getattr(main_window, "api", None)
                if api is not None:
                    return api
                api = getattr(app, "api", None)
                if api is not None:
                    return api
        except Exception:
            pass

        return None

    @staticmethod
    def _unload_llm_via_api(widget, payload: dict) -> bool:
        """Send one LLM unload through the same service boundary as stop."""
        api = ModelStatusWidget._current_gui_api(widget)
        if api is None:
            return False
        llm_service = getattr(api, "llm", None)
        unload = getattr(llm_service, "unload", None)
        if not callable(unload):
            return False
        unload(dict(payload))
        return True

    @staticmethod
    def _unload_rag_via_api(widget) -> bool:
        """Send one RAG embedding unload through the LLM service boundary."""
        api = ModelStatusWidget._current_gui_api(widget)
        if api is None:
            return False
        llm_service = getattr(api, "llm", None)
        unload_rag = getattr(llm_service, "unload_rag", None)
        if not callable(unload_rag):
            return False
        unload_rag()
        return True

    def _unload_icon(self):
        """Return the themed Lucide unload icon."""
        palette_color = self.palette().color(self.backgroundRole())
        theme = "dark" if palette_color.lightness() < 128 else "light"
        return self.icon_manager.get_icon("circle-x", theme)

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
