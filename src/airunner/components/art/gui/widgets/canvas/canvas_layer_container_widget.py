from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QSpacerItem, QSizePolicy
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.outpaint_settings import OutpaintSettings
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
            SignalCode.LAYER_SELECTED: self.on_layer_selected,
            SignalCode.LAYERS_SHOW_SIGNAL: self.on_layers_show_signal,
        }
        self.selected_layers = set()  # Track selected layer IDs
        self.layer_widgets = {}  # Map layer_id to widget
        super().__init__(*args, **kwargs)
        self.layers = CanvasLayer.objects.order_by("order").all()
        if not self.layers or len(self.layers) == 0:
            layer = self.create_layer(order=0, name="Layer 1")
            # Initialize default settings for the first layer
            self._initialize_layer_default_settings(layer.id)
            self.layers = [layer]

        # Add layers to the grid layout
        for i, layer in enumerate(self.layers):
            item = LayerItemWidget(layer_id=layer.id)
            self.layer_widgets[layer.id] = item
            self.ui.layer_list_layout.layout().addWidget(
                item, i, 0
            )  # Add to row i, column 0

        # Select the first layer by default
        if self.layers:
            self.selected_layers.add(self.layers[0].id)
            self.layer_widgets[self.layers[0].id].set_selected(True)
            # Emit selection changed signal to notify settings system
            self.emit_signal(
                SignalCode.LAYER_SELECTION_CHANGED,
                {"selected_layer_ids": list(self.selected_layers)},
            )

        # add a vertical spacer
        self.spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.ui.layer_list_layout.layout().addItem(
            self.spacer, len(self.layers), 0
        )

        # Enable drag and drop for the container
        self.setAcceptDrops(True)

    def create_layer(self, **kwargs) -> CanvasLayer:
        if "name" not in kwargs:
            kwargs["name"] = f"Layer {len(self.layers) + 1}"

        if "order" not in kwargs:
            kwargs["order"] = len(self.layers)
        layer = CanvasLayer.objects.create(**kwargs)
        DrawingPadSettings.objects.create(layer_id=layer.id)
        ControlnetSettings.objects.create(layer_id=layer.id)
        ImageToImageSettings.objects.create(layer_id=layer.id)
        OutpaintSettings.objects.create(layer_id=layer.id)
        BrushSettings.objects.create(layer_id=layer.id)
        MetadataSettings.objects.create(layer_id=layer.id)
        return CanvasLayer.objects.get(layer.id)

    @Slot()
    def on_merge_visible_layers_clicked(self):
        pass

    @Slot()
    def on_add_layer_clicked(self):
        self.api.art.canvas.begin_layer_operation("create")
        try:
            layer = self.create_layer()
            if not layer:
                self.api.art.canvas.cancel_layer_operation("create")
                return

            # Initialize default settings for the new layer
            self._initialize_layer_default_settings(layer.id)

            self.layers.append(layer)
            item = LayerItemWidget(layer_id=layer.id)
            self.layer_widgets[layer.id] = item

            # Remove spacer, add new widget, then add spacer back
            self.ui.layer_list_layout.layout().removeItem(self.spacer)
            self.ui.layer_list_layout.layout().addWidget(
                item, len(self.layers) - 1, 0
            )
            self.ui.layer_list_layout.layout().addItem(
                self.spacer, len(self.layers), 0
            )

            # Select the newly created layer
            # Clear previous selections
            for lid in self.selected_layers:
                self.layer_widgets[lid].set_selected(False)

            self.selected_layers.clear()
            self.selected_layers.add(layer.id)
            item.set_selected(True)

            # Emit selection changed signal to notify settings system
            self.emit_signal(
                SignalCode.LAYER_SELECTION_CHANGED,
                {"selected_layer_ids": list(self.selected_layers)},
            )

            self.api.art.canvas.commit_layer_operation("create", [layer.id])
            self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)
        except Exception:
            self.api.art.canvas.cancel_layer_operation("create")
            raise

    @Slot()
    def on_move_layer_up_clicked(self):
        if not self.selected_layers:
            return

        selected_layer_ids = sorted(self.selected_layers)
        selected_layers = [
            l for l in self.layers if l.id in selected_layer_ids
        ]

        # Find the minimum order among selected layers
        min_order = min(layer.order for layer in selected_layers)

        # Can't move up if already at the top
        if min_order == 0:
            return

        self.api.art.canvas.begin_layer_operation(
            "reorder", selected_layer_ids
        )
        changed = False

        try:
            # Move each selected layer up by one position
            for layer in selected_layers:
                # Find the layer above this one
                layer_above = next(
                    (l for l in self.layers if l.order == layer.order - 1),
                    None,
                )
                if layer_above and layer_above.id not in selected_layer_ids:
                    # Swap orders
                    layer_above.order, layer.order = (
                        layer.order,
                        layer_above.order,
                    )
                    CanvasLayer.objects.update(layer.id, order=layer.order)
                    CanvasLayer.objects.update(
                        layer_above.id, order=layer_above.order
                    )
                    changed = True
        except Exception:
            self.api.art.canvas.cancel_layer_operation("reorder")
            raise

        if changed:
            self._refresh_layer_display()
            self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)
            self.api.art.canvas.commit_layer_operation(
                "reorder", selected_layer_ids
            )
        else:
            self.api.art.canvas.cancel_layer_operation("reorder")

    @Slot()
    def on_move_layer_down_clicked(self):
        if not self.selected_layers:
            return

        selected_layer_ids = sorted(self.selected_layers, reverse=True)
        selected_layers = [
            l for l in self.layers if l.id in selected_layer_ids
        ]

        # Find the maximum order among selected layers
        max_order = max(layer.order for layer in selected_layers)

        # Can't move down if already at the bottom
        if max_order >= len(self.layers) - 1:
            return

        self.api.art.canvas.begin_layer_operation(
            "reorder", selected_layer_ids
        )
        changed = False

        try:
            # Move each selected layer down by one position
            for layer in selected_layers:
                # Find the layer below this one
                layer_below = next(
                    (l for l in self.layers if l.order == layer.order + 1),
                    None,
                )
                if layer_below and layer_below.id not in selected_layer_ids:
                    # Swap orders
                    layer_below.order, layer.order = (
                        layer.order,
                        layer_below.order,
                    )
                    CanvasLayer.objects.update(layer.id, order=layer.order)
                    CanvasLayer.objects.update(
                        layer_below.id, order=layer_below.order
                    )
                    changed = True
        except Exception:
            self.api.art.canvas.cancel_layer_operation("reorder")
            raise

        if changed:
            self._refresh_layer_display()
            self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)
            self.api.art.canvas.commit_layer_operation(
                "reorder", selected_layer_ids
            )
        else:
            self.api.art.canvas.cancel_layer_operation("reorder")

    @Slot()
    def on_delete_layer_clicked(self):
        if not self.selected_layers:
            return

        # Can't delete all layers - must have at least one
        if len(self.selected_layers) >= len(self.layers):
            return

        layers_to_delete = [
            l for l in self.layers if l.id in self.selected_layers
        ]

        if not layers_to_delete:
            return

        layer_ids = [layer.id for layer in layers_to_delete]
        self.api.art.canvas.begin_layer_operation("delete", layer_ids)
        deleted_any = False

        try:
            # Delete selected layers
            for layer in layers_to_delete:
                self.layers.remove(layer)
                widget = self.layer_widgets.pop(layer.id, None)
                if widget:
                    self.ui.layer_list_layout.layout().removeWidget(widget)
                    widget.deleteLater()

                # Emit layer deleted signal for canvas to handle
                self.emit_signal(
                    SignalCode.LAYER_DELETED,
                    {"layer_id": layer.id},
                )
                CanvasLayer.objects.delete(layer.id)
                deleted_any = True

            # Clear selection
            self.selected_layers.clear()

            # Reorder remaining layers
            for i, layer in enumerate(self.layers):
                layer.order = i
                CanvasLayer.objects.update(layer.id, order=i)

            # Select the first remaining layer
            if self.layers:
                self.selected_layers.add(self.layers[0].id)
                self.layer_widgets[self.layers[0].id].set_selected(True)
                # Emit selection changed signal to notify settings system
                self.emit_signal(
                    SignalCode.LAYER_SELECTION_CHANGED,
                    {"selected_layer_ids": list(self.selected_layers)},
                )

            self._refresh_layer_display()
        except Exception:
            self.api.art.canvas.cancel_layer_operation("delete")
            raise

        if deleted_any:
            self.api.art.canvas.commit_layer_operation("delete", layer_ids)
            self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)
        else:
            self.api.art.canvas.cancel_layer_operation("delete")

    def on_layer_deleted(self, data: dict):
        layer_id = data.get("layer_id")
        layer_item = data.get("layer_item")
        if layer_id:
            layer = next((l for l in self.layers if l.id == layer_id), None)
            if layer:
                self.layers.remove(layer)
                widget = layer_item or self.layer_widgets.get(layer_id)
                if widget:
                    self.ui.layer_list_layout.layout().removeWidget(widget)
                    widget.deleteLater()
                # Remove from tracking
                self.layer_widgets.pop(layer_id, None)
                self.selected_layers.discard(layer_id)
            CanvasLayer.objects.delete(layer_id)
            DrawingPadSettings.objects.delete_by(layer_id=layer_id)
            ControlnetSettings.objects.delete_by(layer_id=layer_id)
            ImageToImageSettings.objects.delete_by(layer_id=layer_id)
            OutpaintSettings.objects.delete_by(layer_id=layer_id)
            BrushSettings.objects.delete_by(layer_id=layer_id)
            MetadataSettings.objects.delete_by(layer_id=layer_id)

    def on_layer_selected(self, data: dict):
        layer_id = data.get("layer_id")
        modifiers = data.get("modifiers", Qt.KeyboardModifier.NoModifier)

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Click: Toggle individual selection
            if layer_id in self.selected_layers:
                # Don't allow deselecting if it's the only selected layer
                if len(self.selected_layers) > 1:
                    self.selected_layers.remove(layer_id)
                    self.layer_widgets[layer_id].set_selected(False)
            else:
                self.selected_layers.add(layer_id)
                self.layer_widgets[layer_id].set_selected(True)

        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Shift+Click: Select range
            if self.selected_layers:
                # Find the current selection range
                selected_orders = [
                    l.order
                    for l in self.layers
                    if l.id in self.selected_layers
                ]
                clicked_layer = next(
                    (l for l in self.layers if l.id == layer_id), None
                )

                if clicked_layer:
                    min_order = min(selected_orders + [clicked_layer.order])
                    max_order = max(selected_orders + [clicked_layer.order])

                    # Clear current selection visual
                    for lid in self.selected_layers:
                        self.layer_widgets[lid].set_selected(False)

                    # Select range
                    self.selected_layers.clear()
                    for layer in self.layers:
                        if min_order <= layer.order <= max_order:
                            self.selected_layers.add(layer.id)
                            self.layer_widgets[layer.id].set_selected(True)
            else:
                # No previous selection, just select this layer
                self.selected_layers.add(layer_id)
                self.layer_widgets[layer_id].set_selected(True)
        else:
            # Normal click: Select only this layer
            # Clear previous selections
            for lid in self.selected_layers:
                self.layer_widgets[lid].set_selected(False)

            self.selected_layers.clear()
            self.selected_layers.add(layer_id)
            self.layer_widgets[layer_id].set_selected(True)

        # Emit selection changed signal
        self.emit_signal(
            SignalCode.LAYER_SELECTION_CHANGED,
            {"selected_layer_ids": list(self.selected_layers)},
        )

    def _refresh_layer_display(self):
        """Refresh the layer display order after reordering."""
        # Sort layers by order
        self.layers.sort(key=lambda l: l.order)

        # Clear layout (except spacer)
        widgets = list(self.layer_widgets.values())
        for widget in widgets:
            self.ui.layer_list_layout.layout().removeWidget(widget)

        # Remove spacer
        if self.spacer:
            self.ui.layer_list_layout.layout().removeItem(self.spacer)

        # Re-add widgets in new order
        for i, layer in enumerate(self.layers):
            widget = self.layer_widgets.get(layer.id)
            if widget:
                self.ui.layer_list_layout.layout().addWidget(widget, i, 0)

        # Add spacer back
        self.ui.layer_list_layout.layout().addItem(
            self.spacer, len(self.layers), 0
        )

    def _sync_layers_from_database(self) -> None:
        db_layers = CanvasLayer.objects.all() or []
        db_layers.sort(key=lambda layer: getattr(layer, "order", 0))
        db_layer_ids = {layer.id for layer in db_layers}

        # Remove widgets for layers that no longer exist
        for layer_id in list(self.layer_widgets.keys()):
            if layer_id not in db_layer_ids:
                widget = self.layer_widgets.pop(layer_id)
                self.ui.layer_list_layout.layout().removeWidget(widget)
                widget.deleteLater()
                self.selected_layers.discard(layer_id)

        # Create widgets for new layers
        for layer in db_layers:
            if layer.id not in self.layer_widgets:
                widget = LayerItemWidget(layer_id=layer.id)
                self.layer_widgets[layer.id] = widget

        self.layers = db_layers
        self._refresh_layer_display()

        # Ensure selection remains valid
        self.selected_layers = {
            layer_id
            for layer_id in self.selected_layers
            if layer_id in db_layer_ids
        }
        if not self.selected_layers and self.layers:
            self.selected_layers.add(self.layers[0].id)

        for layer_id, widget in self.layer_widgets.items():
            widget.set_selected(layer_id in self.selected_layers)

    def on_layers_show_signal(self, _data: dict | None = None) -> None:
        self._sync_layers_from_database()

    def on_visibility_toggled(self, data: dict):
        layer_id = data.get("layer_id")
        visible = data.get("visible")
        layer = CanvasLayer.objects.get(layer_id)
        if layer:
            CanvasLayer.objects.update(layer.id, visible=visible)
            # Emit signal to update canvas display
            self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

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

        self.api.art.canvas.begin_layer_operation(
            "reorder", [source_layer_id, target_layer_id]
        )
        changed = False
        try:
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
                changed = True

                # Re-add widgets in new order
                for i, layer in enumerate(self.layers):
                    widget = next(
                        (w for w in widgets if w.layer.id == layer.id), None
                    )
                    if widget:
                        layout.addWidget(widget, i, 0)

                # Add spacer back at the end
                layout.addItem(self.spacer, len(self.layers), 0)

                # Update order values in database
                for i, layer in enumerate(self.layers):
                    CanvasLayer.objects.update(layer.id, order=i)
                    layer.order = i

                # Emit signal to update canvas display
                self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)
        except Exception:
            self.api.art.canvas.cancel_layer_operation("reorder")
            raise

        if changed:
            self.api.art.canvas.commit_layer_operation(
                "reorder", [source_layer_id, target_layer_id]
            )
        else:
            self.api.art.canvas.cancel_layer_operation("reorder")

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

    def _initialize_layer_default_settings(self, layer_id: int):
        """Initialize default settings for a new layer.

        Args:
            layer_id: The ID of the layer to initialize settings for.
        """
        try:
            # Create default DrawingPadSettings
            if not DrawingPadSettings.objects.filter_by(layer_id=layer_id):
                DrawingPadSettings.objects.create(layer_id=layer_id)

            # Create default ControlnetSettings
            if not ControlnetSettings.objects.filter_by(layer_id=layer_id):
                ControlnetSettings.objects.create(layer_id=layer_id)

            # Create default ImageToImageSettings
            if not ImageToImageSettings.objects.filter_by(layer_id=layer_id):
                ImageToImageSettings.objects.create(layer_id=layer_id)

            # Create default OutpaintSettings
            if not OutpaintSettings.objects.filter_by(layer_id=layer_id):
                OutpaintSettings.objects.create(layer_id=layer_id)

            # Create default BrushSettings
            if not BrushSettings.objects.filter_by(layer_id=layer_id):
                BrushSettings.objects.create(layer_id=layer_id)

            # Create default MetadataSettings
            if not MetadataSettings.objects.filter_by(layer_id=layer_id):
                MetadataSettings.objects.create(layer_id=layer_id)

        except Exception as e:
            print(
                f"Error initializing default settings for layer {layer_id}: {e}"
            )
