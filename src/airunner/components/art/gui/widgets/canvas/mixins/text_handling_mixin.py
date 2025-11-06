"""Text handling mixin for CustomGraphicsView.

This mixin handles text item management including creation, editing,
persistence, and deletion for the canvas view.
"""

import json
from typing import Dict, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication, QGraphicsTextItem

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.gui.widgets.canvas.draggables.draggable_text_item import (
    DraggableTextItem,
)
from airunner.components.art.gui.widgets.canvas.resizable_text_item import (
    ResizableTextItem,
)
from airunner.enums import CanvasToolName


class TextHandlingMixin:
    """Mixin for text item management in CustomGraphicsView.

    This mixin handles:
    - Finding text items at specific positions
    - Creating new inline text items
    - Editing existing text items
    - Text item event handlers (focus, key press, position change)
    - Removing text items
    - Persisting text items to database
    - Restoring text items from database
    - Clearing all text items
    - Setting text item interaction modes

    Attributes:
        _text_items: List of text items on canvas
        _text_item_layer_map: Mapping of text items to layer IDs
        _editing_text_item: Currently edited text item
        _text_inspector: Text property inspector widget
    """

    def _find_text_item_at(self, pos: QPointF) -> Optional[QGraphicsTextItem]:
        """Find text item at the given position.

        Args:
            pos: Position to check for text items.

        Returns:
            Text item at position or None if not found.
        """
        if not self.scene:
            return None
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, QGraphicsTextItem):
                return item
        return None

    def _add_text_item_inline(self, pos: QPointF) -> None:
        """Create a new text item at scene position and start editing inline.

        Args:
            pos: Scene position for new text item.
        """
        if not self.scene:
            return

        text_item = DraggableTextItem(self)
        text_item.setPlainText("")
        text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        text_item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        text_item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        text_item.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
        text_item.setPos(pos)
        text_item.setZValue(2000)  # Above images (which use ~1000)
        text_item.setDefaultTextColor(QColor("white"))
        text_item.setFont(self._get_default_text_font())
        text_item.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges, True)
        text_item.itemChange = self._make_text_item_change_handler(text_item)
        text_item.focusOutEvent = self._make_text_focus_out_handler(text_item)
        text_item.keyPressEvent = self._make_text_key_press_handler(text_item)

        self.scene.addItem(text_item)
        self._text_items.append(text_item)
        # Associate with currently selected layer
        layer_id = self._get_current_selected_layer_id()
        self._text_item_layer_map[text_item] = layer_id

        text_item.setFocus()
        self._editing_text_item = text_item
        # Bind inspector
        if self._text_inspector:
            self._text_inspector.bind_to(text_item)

        self._save_text_items_to_db()

    def _edit_text_item(self, item: QGraphicsTextItem) -> None:
        """Enable editing mode for an existing text item.

        Args:
            item: Text item to edit.
        """
        # Only allow editing if text tool is active
        if self.current_tool is CanvasToolName.TEXT:
            item.setTextInteractionFlags(Qt.TextEditorInteraction)
            item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
            item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            item.setFocus()
            self._editing_text_item = item
            # Bind inspector to this item
            if self._text_inspector:
                self._text_inspector.bind_to(item)

    def _make_text_focus_out_handler(self, item: QGraphicsTextItem):
        """Create focus out handler for text item.

        Handles saving text and unbinding inspector when focus is lost,
        unless focus moved to the inspector itself.

        Args:
            item: Text item to create handler for.

        Returns:
            Focus out event handler function.
        """

        def handler(event):
            # If focus moved into the inspector widget (or its children), keep
            # the inspector bound so clicking controls doesn't cause the
            # inspector to disappear.
            try:
                fw = QApplication.focusWidget()
                if self._text_inspector is not None and fw is not None:
                    try:
                        if (
                            self._text_inspector.isAncestorOf(fw)
                            or fw is self._text_inspector
                        ):
                            # Don't unbind; leave the text interaction flags alone
                            QGraphicsTextItem.focusOutEvent(item, event)
                            return
                    except Exception:
                        # If any failure occurs checking ancestry, fall back to
                        # default behavior below
                        pass

            except Exception:
                pass

            item.setTextInteractionFlags(Qt.NoTextInteraction)
            self._editing_text_item = None
            self._save_text_items_to_db()
            # Unbind inspector when editing finishes
            if self._text_inspector:
                self._text_inspector.bind_to(None)
            QGraphicsTextItem.focusOutEvent(item, event)

        return handler

    def _make_text_key_press_handler(self, item: QGraphicsTextItem):
        """Create key press handler for text item.

        Handles Delete key to remove text item.

        Args:
            item: Text item to create handler for.

        Returns:
            Key press event handler function.
        """

        def handler(event):
            if event.key() == Qt.Key.Key_Delete:
                self._remove_text_item(item)
            else:
                QGraphicsTextItem.keyPressEvent(item, event)

        return handler

    def _make_text_item_change_handler(self, item: QGraphicsTextItem):
        """Create item change handler for text item.

        Saves text items when position changes.

        Args:
            item: Text item to create handler for.

        Returns:
            Item change event handler function.
        """

        def handler(change, value):
            if change == QGraphicsTextItem.ItemPositionChange:
                self._save_text_items_to_db()
            return QGraphicsTextItem.itemChange(item, change, value)

        return handler

    def _remove_text_item(
        self, item: QGraphicsTextItem, *, manage_transaction: bool = True
    ) -> None:
        """Remove a text item from the canvas.

        Args:
            item: Text item to remove.
            manage_transaction: Whether to manage layer history transaction.
        """
        layer_id = self._text_item_layer_map.get(item)
        if manage_transaction:
            try:
                if self.scene and layer_id is not None:
                    if layer_id not in self.scene._history_transactions:
                        self.scene._begin_layer_history_transaction(
                            layer_id, "text"
                        )
            except Exception:
                pass

        try:
            if hasattr(item, "scene") and item.scene():
                item.scene().removeItem(item)
        except Exception:
            pass

        if item in self._text_items:
            self._text_items.remove(item)
        if item in self._text_item_layer_map:
            del self._text_item_layer_map[item]

        editing = getattr(self, "_editing_text_item", None)
        if editing is item or getattr(item, "text_item", None) is editing:
            self._editing_text_item = None
        if self._text_inspector:
            try:
                self._text_inspector.bind_to(None)
            except Exception:
                pass

        self._save_text_items_to_db()

        if manage_transaction:
            try:
                if self.scene and layer_id is not None:
                    self.scene._commit_layer_history_transaction(
                        layer_id, "text"
                    )
            except Exception:
                pass

    def _get_default_text_font(self) -> QFont:
        """Get default font for new text items.

        Returns:
            Default QFont with 18pt Arial.
        """
        font = QFont()
        font.setPointSize(18)
        font.setFamily("Arial")
        return font

    def _save_text_items_to_db(self) -> None:
        """Save all text items to database grouped by layer."""
        # Group text items by associated layer and save per-layer
        layer_buckets: Dict[Optional[int], list] = {}
        for item in self._text_items:
            layer_id = self._text_item_layer_map.get(item)
            if layer_id not in layer_buckets:
                layer_buckets[layer_id] = []
            # Two kinds of items: inline QGraphicsTextItem or ResizableTextItem
            try:
                if isinstance(item, ResizableTextItem):
                    d = item.to_persist_dict()
                    layer_buckets[layer_id].append(d)
                elif isinstance(item, QGraphicsTextItem):
                    abs_x = int(item.pos().x() + self.canvas_offset_x)
                    abs_y = int(item.pos().y() + self.canvas_offset_y)
                    layer_buckets[layer_id].append(
                        {
                            "type": "inline",
                            "text": item.toPlainText(),
                            "x": abs_x,
                            "y": abs_y,
                            "color": item.defaultTextColor().name(),
                            "font": item.font().toString(),
                        }
                    )
                else:
                    # Unknown item type: try best-effort extraction
                    abs_x = int(item.pos().x() + self.canvas_offset_x)
                    abs_y = int(item.pos().y() + self.canvas_offset_y)
                    text = getattr(item, "toPlainText", lambda: "")()
                    color = "white"
                    try:
                        color = item.defaultTextColor().name()
                    except Exception:
                        pass
                    font = ""
                    try:
                        font = item.font().toString()
                    except Exception:
                        pass
                    layer_buckets[layer_id].append(
                        {
                            "type": "inline",
                            "text": text,
                            "x": abs_x,
                            "y": abs_y,
                            "color": color,
                            "font": font,
                        }
                    )
            except Exception:
                self.logger.exception("Failed serializing text item for DB")

        # Persist each layer's text items JSON into DrawingPadSettings.text_items
        for layer_id, items in layer_buckets.items():
            try:
                json_text = json.dumps(items)
                # Use update_drawing_pad_settings with explicit layer_id
                self.update_drawing_pad_settings(
                    layer_id=layer_id, text_items=json_text
                )
            except Exception:
                self.logger.exception(
                    "Failed to save text items for layer %s", layer_id
                )

    def update_drawing_pad_settings(self, **kwargs) -> None:
        """Update drawing pad settings for layers.

        Args:
            **kwargs: Settings to update, may include layer_id for specific layer.
        """
        # Extract layer_id if provided in kwargs
        specific_layer_id = kwargs.pop("layer_id", None)

        if specific_layer_id is not None:
            # Update only the specific layer
            super().update_drawing_pad_settings(
                layer_id=specific_layer_id, **kwargs
            )
        else:
            # Update all layers if no specific layer_id provided
            for layer_item in self.layers:
                super().update_drawing_pad_settings(
                    layer_id=layer_item.id, **kwargs
                )

    def _restore_text_items_from_db(self) -> None:
        """Restore text items from per-layer database settings."""
        self._clear_text_items()
        try:
            # Iterate through layers and load their text_items JSON
            for layer in CanvasLayer.objects.order_by("order").all():
                settings = DrawingPadSettings.objects.filter_by_first(
                    layer_id=layer.id
                )
                if not settings:
                    continue
                raw = getattr(settings, "text_items", None)
                if not raw:
                    continue
                try:
                    data_list = json.loads(raw)
                except Exception:
                    data_list = []

                for data in data_list:
                    text = data.get("text", "")
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    color = QColor(data.get("color", "white"))
                    font = QFont()
                    try:
                        font.fromString(data.get("font", ""))
                    except Exception:
                        font = self._get_default_text_font()
                    # Distinguish between inline and area types
                    item_type = data.get("type", "inline")
                    if item_type == "area":
                        # Restore a ResizableTextItem with provided w/h
                        w = data.get("w", 100)
                        h = data.get("h", 40)
                        display_x = x - int(self.canvas_offset_x)
                        display_y = y - int(self.canvas_offset_y)
                        rect = QRectF(display_x, display_y, w, h)
                        area = ResizableTextItem(self, rect)
                        area.text_item.setPlainText(text)
                        area.text_item.setDefaultTextColor(color)
                        area.text_item.setFont(font)
                        area.setZValue(2000)
                        # Bind handlers to the text child so focus/keys persist
                        area.text_item.focusOutEvent = (
                            self._make_text_focus_out_handler(area.text_item)
                        )
                        area.text_item.keyPressEvent = (
                            self._make_text_key_press_handler(area.text_item)
                        )
                        area.text_item.itemChange = (
                            self._make_text_item_change_handler(area.text_item)
                        )
                        self.scene.addItem(area)
                        self._text_items.append(area)
                        self._text_item_layer_map[area] = layer.id
                    else:
                        text_item = DraggableTextItem(self)
                        text_item.setPlainText(text)
                        # Stored x/y are absolute coordinates; convert to display
                        # position by subtracting the current canvas offset.
                        display_x = x - int(self.canvas_offset_x)
                        display_y = y - int(self.canvas_offset_y)
                        text_item.setPos(QPointF(display_x, display_y))
                        text_item.setDefaultTextColor(color)
                        text_item.setFont(font)
                        text_item.setFlag(
                            QGraphicsTextItem.ItemIsMovable, True
                        )
                        text_item.setFlag(
                            QGraphicsTextItem.ItemIsSelectable, True
                        )
                        text_item.setFlag(
                            QGraphicsTextItem.ItemIsFocusable, True
                        )
                        text_item.setFlag(
                            QGraphicsTextItem.ItemSendsGeometryChanges, True
                        )
                        text_item.setZValue(2000)
                        text_item.focusOutEvent = (
                            self._make_text_focus_out_handler(text_item)
                        )
                        text_item.keyPressEvent = (
                            self._make_text_key_press_handler(text_item)
                        )
                        text_item.itemChange = (
                            self._make_text_item_change_handler(text_item)
                        )
                        self.scene.addItem(text_item)
                        self._text_items.append(text_item)
                        self._text_item_layer_map[text_item] = layer.id
        except Exception:
            self.logger.exception("Failed to restore text items from DB")

    def _clear_text_items(self) -> None:
        """Clear all text items from canvas."""
        for item in self._text_items:
            self.scene.removeItem(item)
        self._text_items.clear()
        self._text_item_layer_map.clear()

    def _set_text_items_interaction(self, enable: bool) -> None:
        """Enable or disable interaction for all text items.

        Args:
            enable: True to enable interaction, False to disable.
        """
        # Enable/disable moving/editing for all text items
        for item in self._text_items:
            if isinstance(item, ResizableTextItem):
                item.set_interaction_enabled(enable)
                continue

            if enable:
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True
                )
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True
                )
            else:
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, False
                )
                item.setFlag(
                    QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, False
                )
