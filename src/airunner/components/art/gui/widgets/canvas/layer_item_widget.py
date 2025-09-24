from PySide6.QtCore import Slot, Qt, QMimeData
from PySide6.QtGui import QDrag, QPainter
from PySide6.QtWidgets import QApplication
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.gui.widgets.canvas.templates.layer_item_ui import (
    Ui_layer_item,
)
from airunner.enums import SignalCode


class LayerItemWidget(BaseWidget, PipelineMixin):
    widget_class_ = Ui_layer_item
    icons = [
        ("eye", "visibility"),
        ("trash-2", "delete_layer"),
    ]

    def __init__(self, layer_id: int, *args, **kwargs):
        self.layer = CanvasLayer.objects.get(layer_id)
        self.drag_start_position = None
        self.is_selected = False

        super().__init__(*args, **kwargs)
        self.ui.label.setText(self.layer.name)
        self.ui.visibility.blockSignals(True)
        self.ui.visibility.setChecked(self.layer.visible)
        self.ui.visibility.blockSignals(False)

        # Enable drag functionality
        self.setAcceptDrops(True)

        # Set initial style
        self._update_selection_style()

    @Slot(bool)
    def on_visibility_toggled(self, checked: bool):
        self.layer.visible = checked
        self.emit_signal(
            SignalCode.LAYER_VISIBILITY_TOGGLED,
            {"layer_id": self.layer.id, "visible": checked},
        )

    @Slot()
    def on_delete_layer_clicked(self):
        self.emit_signal(
            SignalCode.LAYER_DELETED,
            {"layer_id": self.layer.id, "layer_item": self},
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()

            # Handle layer selection
            self.emit_signal(
                SignalCode.LAYER_SELECTED,
                {"layer_id": self.layer.id, "modifiers": event.modifiers()},
            )

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if not self.drag_start_position:
            return

        if (
            event.position().toPoint() - self.drag_start_position
        ).manhattanLength() < QApplication.startDragDistance():
            return

        self.start_drag()

    def start_drag(self):
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.layer.id))
        mime_data.setData(
            "application/x-layer-item", str(self.layer.id).encode()
        )
        drag.setMimeData(mime_data)

        # Create a simple pixmap for the drag operation
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_position)

        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-layer-item"):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-layer-item"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-layer-item"):
            source_layer_id = int(
                event.mimeData()
                .data("application/x-layer-item")
                .data()
                .decode()
            )
            target_layer_id = self.layer.id

            if source_layer_id != target_layer_id:
                self.emit_signal(
                    SignalCode.LAYER_REORDERED,
                    {
                        "source_layer_id": source_layer_id,
                        "target_layer_id": target_layer_id,
                        "drop_position": event.position().toPoint(),
                    },
                )
            event.accept()
        else:
            event.ignore()

    def set_selected(self, selected: bool):
        """Set the selection state and update visual appearance."""
        self.is_selected = selected
        self._update_selection_style()

    def _update_selection_style(self):
        """Update the widget's appearance based on selection state."""
        if self.is_selected:
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #4a90e2;
                    border: 2px solid #357abd;
                    border-radius: 4px;
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                QWidget {
                    background-color: transparent;
                    border: none;
                }
            """
            )
