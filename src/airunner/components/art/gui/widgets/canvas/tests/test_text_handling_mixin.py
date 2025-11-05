"""Tests for TextHandlingMixin."""

import json
from unittest.mock import Mock, patch
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsTextItem

from airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin import (
    TextHandlingMixin,
)
from airunner.enums import CanvasToolName


class BaseStub:
    """Stub base class providing methods that mixins call via super()."""

    def update_drawing_pad_settings(self, **kwargs):
        """Stub update_drawing_pad_settings."""


class TestableTextHandlingMixin(TextHandlingMixin, BaseStub):
    """Testable version of TextHandlingMixin with required dependencies."""

    def __init__(self):
        """Initialize testable mixin with mocked dependencies."""
        self._scene = Mock()
        self._scene.items = Mock(return_value=[])
        self._scene.addItem = Mock()
        self._scene.removeItem = Mock()
        self._scene._history_transactions = {}
        self._scene._begin_layer_history_transaction = Mock()
        self._scene._commit_layer_history_transaction = Mock()

        self._text_items = []
        self._text_item_layer_map = {}
        self._editing_text_item = None
        self._text_inspector = None

        self._canvas_offset_x = 0
        self._canvas_offset_y = 0

        self.current_tool = CanvasToolName.TEXT

        self.logger = Mock()
        self.logger.exception = Mock()

        self.layers = []

    @property
    def scene(self):
        """Scene property."""
        return self._scene

    @property
    def canvas_offset_x(self):
        """Canvas offset X coordinate."""
        return self._canvas_offset_x

    @property
    def canvas_offset_y(self):
        """Canvas offset Y coordinate."""
        return self._canvas_offset_y

    def _get_current_selected_layer_id(self):
        """Get current selected layer ID."""
        return 1


class TestTextHandlingMixin:
    """Tests for TextHandlingMixin class."""

    def test_find_text_item_at_no_scene(self, qapp):
        """Test _find_text_item_at returns None when no scene."""
        mixin = TestableTextHandlingMixin()
        mixin._scene = None

        result = mixin._find_text_item_at(QPointF(10, 10))

        assert result is None

    def test_find_text_item_at_found(self, qapp):
        """Test _find_text_item_at returns text item when found."""
        mixin = TestableTextHandlingMixin()
        text_item = Mock(spec=QGraphicsTextItem)
        other_item = Mock()
        mixin.scene.items = Mock(return_value=[other_item, text_item])

        result = mixin._find_text_item_at(QPointF(10, 10))

        assert result == text_item
        mixin.scene.items.assert_called_once_with(QPointF(10, 10))

    def test_find_text_item_at_not_found(self, qapp):
        """Test _find_text_item_at returns None when not found."""
        mixin = TestableTextHandlingMixin()
        other_item = Mock()
        mixin.scene.items = Mock(return_value=[other_item])

        result = mixin._find_text_item_at(QPointF(10, 10))

        assert result is None

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin.DraggableTextItem"
    )
    def test_add_text_item_inline(self, mock_draggable, qapp):
        """Test _add_text_item_inline creates and configures text item."""
        mixin = TestableTextHandlingMixin()
        mixin._text_inspector = Mock()
        mixin._save_text_items_to_db = Mock()
        mock_item = Mock(spec=QGraphicsTextItem)
        mock_draggable.return_value = mock_item

        mixin._add_text_item_inline(QPointF(50, 100))

        mock_draggable.assert_called_once_with(mixin)
        mock_item.setPlainText.assert_called_once_with("")
        mock_item.setTextInteractionFlags.assert_called_once_with(
            Qt.TextEditorInteraction
        )
        mock_item.setPos.assert_called_once_with(QPointF(50, 100))
        mock_item.setZValue.assert_called_once_with(2000)
        mock_item.setFocus.assert_called_once()

        mixin.scene.addItem.assert_called_once_with(mock_item)
        assert mock_item in mixin._text_items
        assert mixin._text_item_layer_map[mock_item] == 1
        assert mixin._editing_text_item == mock_item
        mixin._text_inspector.bind_to.assert_called_once_with(mock_item)

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin.DraggableTextItem"
    )
    def test_add_text_item_inline_no_scene(self, mock_draggable, qapp):
        """Test _add_text_item_inline returns early when no scene."""
        mixin = TestableTextHandlingMixin()
        mixin._scene = None

        mixin._add_text_item_inline(QPointF(50, 100))

        mock_draggable.assert_not_called()

    def test_edit_text_item(self, qapp):
        """Test _edit_text_item enables editing mode."""
        mixin = TestableTextHandlingMixin()
        mixin.current_tool = CanvasToolName.TEXT
        mixin._text_inspector = Mock()
        item = Mock(spec=QGraphicsTextItem)

        mixin._edit_text_item(item)

        item.setTextInteractionFlags.assert_called_once_with(
            Qt.TextEditorInteraction
        )
        item.setFlag.assert_any_call(QGraphicsTextItem.ItemIsMovable, True)
        item.setFlag.assert_any_call(QGraphicsTextItem.ItemIsSelectable, True)
        item.setFocus.assert_called_once()
        assert mixin._editing_text_item == item
        mixin._text_inspector.bind_to.assert_called_once_with(item)

    def test_edit_text_item_wrong_tool(self, qapp):
        """Test _edit_text_item does nothing when wrong tool active."""
        mixin = TestableTextHandlingMixin()
        mixin.current_tool = CanvasToolName.BRUSH
        item = Mock(spec=QGraphicsTextItem)

        mixin._edit_text_item(item)

        item.setTextInteractionFlags.assert_not_called()

    def test_get_default_text_font(self, qapp):
        """Test _get_default_text_font returns configured font."""
        mixin = TestableTextHandlingMixin()

        font = mixin._get_default_text_font()

        assert isinstance(font, QFont)
        assert font.pointSize() == 18
        assert font.family() == "Arial"

    def test_make_text_key_press_handler_delete_key(self, qapp):
        """Test key press handler removes item on Delete."""
        mixin = TestableTextHandlingMixin()
        mixin._remove_text_item = Mock()

        item = Mock(spec=QGraphicsTextItem)
        handler = mixin._make_text_key_press_handler(item)
        event = Mock()
        event.key.return_value = Qt.Key.Key_Delete

        handler(event)

        mixin._remove_text_item.assert_called_once_with(item)

    def test_remove_text_item_with_transaction(self, qapp):
        """Test _remove_text_item manages history transaction."""
        mixin = TestableTextHandlingMixin()
        mixin._save_text_items_to_db = Mock()

        item = Mock(spec=QGraphicsTextItem)
        item.scene.return_value = mixin.scene
        mixin._text_items.append(item)
        mixin._text_item_layer_map[item] = 5

        mixin._remove_text_item(item, manage_transaction=True)

        mixin.scene._begin_layer_history_transaction.assert_called_once_with(
            5, "text"
        )
        mixin.scene.removeItem.assert_called_once_with(item)
        assert item not in mixin._text_items
        assert item not in mixin._text_item_layer_map
        mixin._save_text_items_to_db.assert_called_once()
        mixin.scene._commit_layer_history_transaction.assert_called_once_with(
            5, "text"
        )

    def test_remove_text_item_without_transaction(self, qapp):
        """Test _remove_text_item skips transaction when flag is False."""
        mixin = TestableTextHandlingMixin()
        mixin._save_text_items_to_db = Mock()

        item = Mock(spec=QGraphicsTextItem)
        item.scene.return_value = mixin.scene
        mixin._text_items.append(item)
        mixin._text_item_layer_map[item] = 5

        mixin._remove_text_item(item, manage_transaction=False)

        mixin.scene._begin_layer_history_transaction.assert_not_called()
        mixin.scene.removeItem.assert_called_once_with(item)
        assert item not in mixin._text_items
        mixin.scene._commit_layer_history_transaction.assert_not_called()

    def test_remove_text_item_clears_editing_item(self, qapp):
        """Test _remove_text_item clears editing reference."""
        mixin = TestableTextHandlingMixin()
        mixin._save_text_items_to_db = Mock()
        mixin._text_inspector = Mock()

        item = Mock(spec=QGraphicsTextItem)
        item.scene.return_value = mixin.scene
        mixin._text_items.append(item)
        mixin._text_item_layer_map[item] = 5
        mixin._editing_text_item = item

        mixin._remove_text_item(item, manage_transaction=False)

        assert mixin._editing_text_item is None
        mixin._text_inspector.bind_to.assert_called_once_with(None)

    def test_clear_text_items(self, qapp):
        """Test _clear_text_items removes all items."""
        mixin = TestableTextHandlingMixin()

        item1 = Mock()
        item2 = Mock()
        mixin._text_items = [item1, item2]
        mixin._text_item_layer_map = {item1: 1, item2: 2}

        mixin._clear_text_items()

        mixin.scene.removeItem.assert_any_call(item1)
        mixin.scene.removeItem.assert_any_call(item2)
        assert len(mixin._text_items) == 0
        assert len(mixin._text_item_layer_map) == 0

    def test_set_text_items_interaction_enable(self, qapp):
        """Test _set_text_items_interaction enables interaction."""
        mixin = TestableTextHandlingMixin()

        item = Mock(spec=QGraphicsTextItem)
        mixin._text_items = [item]

        mixin._set_text_items_interaction(True)

        item.setFlag.assert_any_call(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True
        )
        item.setFlag.assert_any_call(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True
        )

    def test_set_text_items_interaction_disable(self, qapp):
        """Test _set_text_items_interaction disables interaction."""
        mixin = TestableTextHandlingMixin()

        item = Mock(spec=QGraphicsTextItem)
        mixin._text_items = [item]

        mixin._set_text_items_interaction(False)

        item.setFlag.assert_any_call(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, False
        )
        item.setFlag.assert_any_call(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, False
        )

    def test_update_drawing_pad_settings_specific_layer(self, qapp):
        """Test update_drawing_pad_settings for specific layer."""
        mixin = TestableTextHandlingMixin()

        with patch.object(
            BaseStub, "update_drawing_pad_settings"
        ) as mock_super:
            mixin.update_drawing_pad_settings(layer_id=5, text_items="[]")

            mock_super.assert_called_once_with(layer_id=5, text_items="[]")

    def test_update_drawing_pad_settings_all_layers(self, qapp):
        """Test update_drawing_pad_settings updates all layers."""
        mixin = TestableTextHandlingMixin()
        layer1 = Mock()
        layer1.id = 1
        layer2 = Mock()
        layer2.id = 2
        mixin.layers = [layer1, layer2]

        with patch.object(
            BaseStub, "update_drawing_pad_settings"
        ) as mock_super:
            mixin.update_drawing_pad_settings(text_items="[]")

            assert mock_super.call_count == 2
            mock_super.assert_any_call(layer_id=1, text_items="[]")
            mock_super.assert_any_call(layer_id=2, text_items="[]")

    def test_save_text_items_to_db_inline_item(self, qapp):
        """Test _save_text_items_to_db serializes inline text item."""
        mixin = TestableTextHandlingMixin()
        mixin.update_drawing_pad_settings = Mock()
        mixin._canvas_offset_x = 100
        mixin._canvas_offset_y = 200

        item = Mock(spec=QGraphicsTextItem)
        item.pos.return_value = QPointF(50, 75)
        item.toPlainText.return_value = "Hello"
        item.defaultTextColor.return_value = QColor("red")
        item.font.return_value = QFont("Arial", 12)

        mixin._text_items.append(item)
        mixin._text_item_layer_map[item] = 3

        mixin._save_text_items_to_db()

        call_args = mixin.update_drawing_pad_settings.call_args
        assert call_args[1]["layer_id"] == 3
        saved_json = call_args[1]["text_items"]
        data = json.loads(saved_json)
        assert len(data) == 1
        assert data[0]["type"] == "inline"
        assert data[0]["text"] == "Hello"
        assert data[0]["x"] == 150
        assert data[0]["y"] == 275

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin.CanvasLayer"
    )
    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin.DrawingPadSettings"
    )
    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.text_handling_mixin.DraggableTextItem"
    )
    def test_restore_text_items_from_db(
        self, mock_draggable, mock_settings_class, mock_layer_class, qapp
    ):
        """Test _restore_text_items_from_db loads items from database."""
        mixin = TestableTextHandlingMixin()
        mixin._clear_text_items = Mock()
        mixin._canvas_offset_x = 100
        mixin._canvas_offset_y = 200

        layer = Mock()
        layer.id = 5
        mock_layer_class.objects.order_by.return_value.all.return_value = [
            layer
        ]

        settings = Mock()
        text_data = [
            {
                "type": "inline",
                "text": "Test",
                "x": 150,
                "y": 275,
                "color": "white",
                "font": "Arial,12,-1,5,50,0,0,0,0,0",
            }
        ]
        settings.text_items = json.dumps(text_data)
        mock_settings_class.objects.filter_by_first.return_value = settings

        mock_item = Mock(spec=QGraphicsTextItem)
        mock_draggable.return_value = mock_item

        mixin._restore_text_items_from_db()

        mixin._clear_text_items.assert_called_once()
        mock_draggable.assert_called_once_with(mixin)
        mock_item.setPlainText.assert_called_once_with("Test")
        mock_item.setPos.assert_called_once()
        mixin.scene.addItem.assert_called_once_with(mock_item)
        assert mock_item in mixin._text_items
        assert mixin._text_item_layer_map[mock_item] == 5
