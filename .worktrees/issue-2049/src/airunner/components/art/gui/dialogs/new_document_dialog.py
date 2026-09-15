"""Dialog for creating a new fixed-size canvas document."""

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


@dataclass(frozen=True)
class NewDocumentConfig:
    """Configuration returned from the new document dialog."""

    width: int
    height: int


class NewDocumentDialog(QDialog):
    """Dialog that collects document size for a new canvas document."""

    _PRESETS = (
        ("Custom", None),
        ("Square 512 x 512", (512, 512)),
        ("Square 1024 x 1024", (1024, 1024)),
        ("HD 1280 x 720", (1280, 720)),
        ("Full HD 1920 x 1080", (1920, 1080)),
        ("Portrait 1080 x 1920", (1080, 1920)),
        ("Print 2480 x 3508", (2480, 3508)),
    )

    def __init__(
        self,
        parent=None,
        width: int = 1024,
        height: int = 1024,
    ) -> None:
        super().__init__(parent)
        self._custom_size = NewDocumentConfig(width=width, height=height)
        self._preset_combo: Optional[QComboBox] = None
        self._width_spin: Optional[QSpinBox] = None
        self._height_spin: Optional[QSpinBox] = None
        self._build_ui()
        self._apply_initial_size(width, height)

    def _build_ui(self) -> None:
        """Create the dialog widgets and signal bindings."""
        self.setWindowTitle("Create a New Image")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Create a transparent document with a fixed canvas size.")
        )

        form = QFormLayout()
        layout.addLayout(form)

        self._preset_combo = QComboBox(self)
        for label, size in self._PRESETS:
            self._preset_combo.addItem(label, size)
        self._preset_combo.currentIndexChanged.connect(
            self._on_preset_changed
        )
        form.addRow("Template:", self._preset_combo)

        self._width_spin = self._create_dimension_spinbox()
        self._height_spin = self._create_dimension_spinbox()
        self._width_spin.valueChanged.connect(self._on_dimension_changed)
        self._height_spin.valueChanged.connect(self._on_dimension_changed)
        form.addRow("Width:", self._width_spin)
        form.addRow("Height:", self._height_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_dimension_spinbox(self) -> QSpinBox:
        """Return one dimension spinbox with document-size constraints."""
        spinbox = QSpinBox(self)
        spinbox.setRange(64, 16384)
        spinbox.setSingleStep(64)
        spinbox.setSuffix(" px")
        return spinbox

    def _apply_initial_size(self, width: int, height: int) -> None:
        """Seed the dialog with the current document size."""
        self._width_spin.setValue(width)
        self._height_spin.setValue(height)
        self._set_preset_index(self._find_preset_index(width, height))

    def _find_preset_index(self, width: int, height: int) -> int:
        """Return the preset index matching one size, or custom."""
        for index, (_label, size) in enumerate(self._PRESETS):
            if size == (width, height):
                return index
        return 0

    def _set_preset_index(self, index: int) -> None:
        """Update the preset combo without re-entering handlers."""
        with QSignalBlocker(self._preset_combo):
            self._preset_combo.setCurrentIndex(index)

    def _on_preset_changed(self, index: int) -> None:
        """Apply one preset size to the width and height controls."""
        size = self._preset_combo.itemData(index)
        if size is None:
            return
        self._set_dimensions(*size)

    def _set_dimensions(self, width: int, height: int) -> None:
        """Update both dimension controls and store the current size."""
        with QSignalBlocker(self._width_spin):
            self._width_spin.setValue(width)
        with QSignalBlocker(self._height_spin):
            self._height_spin.setValue(height)
        self._custom_size = NewDocumentConfig(width=width, height=height)

    def _on_dimension_changed(self, _value: int) -> None:
        """Track manual size edits and switch to custom when needed."""
        config = self.document_config()
        self._custom_size = config
        self._set_preset_index(self._find_preset_index(config.width, config.height))

    def document_config(self) -> NewDocumentConfig:
        """Return the current dialog values as document configuration."""
        return NewDocumentConfig(
            width=self._width_spin.value(),
            height=self._height_spin.value(),
        )
