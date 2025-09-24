from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.gui.widgets.canvas.layer_item_widget import (
    LayerItemWidget,
)
from airunner.components.art.gui.widgets.canvas.templates.canvas_layer_container_ui import (
    Ui_canvas_layer_container,
)
from airunner.enums import SignalCode


class CanvasLayerContainerWidget(BaseWidget, PipelineMixin):
    widget_class_ = Ui_canvas_layer_container
    icons = [
        ("plus", "add_layer"),
        ("chevron-up", "move_layer_up"),
        ("chevron-down", "move_layer_down"),
        ("trash-2", "delete_layer"),
    ]

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LAYER_DELETED: self.on_layer_deleted,
            SignalCode.LAYER_VISIBILITY_TOGGLED: self.on_visibility_toggled,
            SignalCode.LAYER_REORDERED: self.on_layer_reordered,
        }
        super().__init__(*args, **kwargs)
        self.layers = CanvasLayer.objects.order_by("order").all()
        if not self.layers or len(self.layers) == 0:
            layer = CanvasLayer.objects.create(order=0, name="Layer 1")
            layer = CanvasLayer.objects.get(layer.id)
            self.layers = [layer]

        # Add layers to the grid layout
        for i, layer in enumerate(self.layers):
            item = LayerItemWidget(layer_id=layer.id)
            self.ui.layer_list_layout.layout().addWidget(
                item, i, 0
            )  # Add to row i, column 0

        # add a vertical spacer
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.ui.layer_list_layout.layout().addItem(
            self.spacer, len(self.layers), 0
        )

        # Enable drag and drop for the container
        self.setAcceptDrops(True)

    @Slot()
    def on_add_layer_clicked(self):
        layer = CanvasLayer.objects.create(
            order=len(self.layers), name=f"Layer {len(self.layers) + 1}"
        )
        layer = CanvasLayer.objects.get(layer.id)
        self.layers.append(layer)
        item = LayerItemWidget(layer_id=layer.id)

        # Remove spacer, add new widget, then add spacer back
        self.ui.layer_list_layout.layout().removeItem(self.spacer)
        self.ui.layer_list_layout.layout().addWidget(
            item, len(self.layers) - 1, 0
        )
        self.ui.layer_list_layout.layout().addItem(
            self.spacer, len(self.layers), 0
        )

    def on_layer_deleted(self, data: dict):
        layer_id = data.get("layer_id")
        layer_item = data.get("layer_item")
        if layer_id:
            layer = next((l for l in self.layers if l.id == layer_id), None)
            if layer:
                self.layers.remove(layer)
                self.ui.layer_list_layout.layout().removeWidget(layer_item)
                layer_item.deleteLater()
            CanvasLayer.objects.delete(layer_id)

    def on_visibility_toggled(self, data: dict):
        layer_id = data.get("layer_id")
        visible = data.get("visible")
        layer = CanvasLayer.objects.get(layer_id)
        if layer:
            CanvasLayer.objects.update(layer.id, visible=visible)

    def on_layer_reordered(self, data: dict):
        source_layer_id = data.get("source_layer_id")
        target_layer_id = data.get("target_layer_id")

        # Find the source and target layers
        source_layer = next(
            (l for l in self.layers if l.id == source_layer_id), None
        )
        target_layer = next(
            (l for l in self.layers if l.id == target_layer_id), None
        )

        if not source_layer or not target_layer:
            return

        # Get the layout
        layout = self.ui.layer_list_layout.layout()

        # Collect all widgets first
        widgets = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), "layer"):
                widgets.append(item.widget())

        # Clear the layout (except spacer)
        for widget in widgets:
            layout.removeWidget(widget)

        # Remove spacer temporarily
        if self.spacer:
            layout.removeItem(self.spacer)

        # Find source and target widgets
        source_widget = next(
            (w for w in widgets if w.layer.id == source_layer_id), None
        )
        target_widget = next(
            (w for w in widgets if w.layer.id == target_layer_id), None
        )

        if source_widget and target_widget:
            # Update the layers list order
            self.layers.remove(source_layer)
            target_index = self.layers.index(target_layer)
            self.layers.insert(target_index, source_layer)

            # Re-add widgets in new order
            for i, layer in enumerate(self.layers):
                widget = next(
                    (w for w in widgets if w.layer.id == layer.id), None
                )
                if widget:
                    layout.addWidget(widget, i, 0)  # Add to row i, column 0

            # Add spacer back at the end
            layout.addItem(self.spacer, len(self.layers), 0)

            # Update order values in database
            for i, layer in enumerate(self.layers):
                CanvasLayer.objects.update(layer.id, order=i)
                layer.order = i

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

            # Find the drop position and determine the target
            drop_position = event.position().toPoint()
            layout = self.ui.layer_list_layout.layout()

            # Find the closest widget to the drop position
            closest_widget = None
            min_distance = float("inf")

            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "layer"):
                    widget = item.widget()
                    widget_center = widget.geometry().center()
                    distance = (
                        drop_position - widget_center
                    ).manhattanLength()
                    if distance < min_distance:
                        min_distance = distance
                        closest_widget = widget

            # If we found a target widget, use it for reordering
            if closest_widget:
                target_layer_id = closest_widget.layer.id
                if source_layer_id != target_layer_id:
                    self.on_layer_reordered(
                        {
                            "source_layer_id": source_layer_id,
                            "target_layer_id": target_layer_id,
                        }
                    )

            event.accept()
        else:
            event.ignore()
