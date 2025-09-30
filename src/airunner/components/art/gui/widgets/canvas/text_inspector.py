from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QFontComboBox,
    QSpinBox,
    QPushButton,
    QColorDialog,
)
from PySide6.QtGui import QColor, QFont


class TextInspector(QWidget):
    """A small inline inspector for editing text item font, size and color."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target = None
        self._font_box = QFontComboBox()
        self._size_box = QSpinBox()
        self._size_box.setRange(6, 200)
        self._color_btn = QPushButton("Color")

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._font_box)
        layout.addWidget(self._size_box)
        layout.addWidget(self._color_btn)
        self.setLayout(layout)

        self._font_box.currentFontChanged.connect(self._on_font_changed)
        self._size_box.valueChanged.connect(self._on_size_changed)
        self._color_btn.clicked.connect(self._on_pick_color)

    def bind_to(self, qgraphics_text_item):
        """Bind inspector to a QGraphicsTextItem (or None)."""
        # Keep a reference to the target and if available, parent the
        # inspector to the view's viewport so clicks inside the inspector do
        # not remove selection from the scene. Position the inspector next
        # to the target item's viewport coordinates.
        self._target = qgraphics_text_item
        if qgraphics_text_item is None:
            self.setVisible(False)
            return

        # Find the owning view (ancestor widget that implements
        # on_inspector_changed). We'll parent the inspector to that view's
        # viewport so it behaves as an overlay and clicking controls does
        # not clear the QGraphicsScene selection.
        self._view = None
        try:
            # Start from the original parent (usually the view) and walk up
            # until we find a widget with on_inspector_changed or a viewport()
            p = self.parent()
            while p is not None:
                if hasattr(p, "on_inspector_changed") and hasattr(
                    p, "viewport"
                ):
                    self._view = p
                    break
                # If parent looks like a viewport, its parent is the view
                if hasattr(p, "parent") and p.parent() is not None:
                    p = p.parent()
                else:
                    break
            if self._view is None:
                # As a fallback, try parent().parent()
                pp = self.parent()
                if pp is not None and pp.parent() is not None:
                    self._view = pp.parent()
        except Exception:
            self._view = None

        try:
            if self._view is not None:
                vp = self._view.viewport()
                # Reparent to viewport so inspector acts as overlay
                self.setParent(vp)
        except Exception:
            pass

        font = qgraphics_text_item.font()
        self._font_box.setCurrentFont(font)
        self._size_box.setValue(font.pointSize() or 18)
        color = qgraphics_text_item.defaultTextColor()
        # store color on button for visual feedback
        self._color_btn.setStyleSheet(f"background: {color.name()}")

        # Position the inspector above the item so it doesn't overlap.
        try:
            if self._view and qgraphics_text_item is not None:
                scene_pos = qgraphics_text_item.scenePos()
                viewport_point = self._view.mapFromScene(scene_pos)
                # Prefer placing above the item; if there's not enough room,
                # place to the right.
                preferred_y = int(
                    viewport_point.y() - self.sizeHint().height() - 8
                )
                preferred_x = int(viewport_point.x() + 8)
                # Ensure inspector stays inside viewport bounds
                vp_rect = self._view.viewport().rect()
                x = max(
                    0,
                    min(
                        preferred_x, vp_rect.width() - self.sizeHint().width()
                    ),
                )
                y = max(
                    0,
                    min(
                        preferred_y,
                        vp_rect.height() - self.sizeHint().height(),
                    ),
                )
                # If preferred_y would put it below the top (negative), move to right of item
                if preferred_y < 0:
                    x = min(
                        vp_rect.width() - self.sizeHint().width(),
                        int(viewport_point.x() + 8),
                    )
                    y = max(0, int(viewport_point.y() + 8))
                self.move(x, y)
        except Exception:
            pass

        # Ensure it's visible after reparent/position
        self.setVisible(True)

    def _on_font_changed(self, font: QFont):
        if self._target is None:
            return
        f = self._target.font()
        f.setFamily(font.family())
        self._target.setFont(f)
        # notify external code to save (view will hook)
        # Re-assert selection on the target and notify the owning view so
        # it can persist the change. Use the discovered view (if any) to
        # avoid relying on the current parent widget.
        try:
            if hasattr(self._target, "setSelected"):
                self._target.setSelected(True)
            self._target.update()
        except Exception:
            pass
        try:
            if self._view and hasattr(self._view, "on_inspector_changed"):
                self._view.on_inspector_changed()
            elif hasattr(self.parent(), "on_inspector_changed"):
                # fallback
                self.parent().on_inspector_changed()
        except Exception:
            pass

    def _on_size_changed(self, size: int):
        if self._target is None:
            return
        f = self._target.font()
        f.setPointSize(int(size))
        self._target.setFont(f)
        try:
            if hasattr(self._target, "setSelected"):
                self._target.setSelected(True)
            self._target.update()
        except Exception:
            pass
        try:
            if self._view and hasattr(self._view, "on_inspector_changed"):
                self._view.on_inspector_changed()
            elif hasattr(self.parent(), "on_inspector_changed"):
                self.parent().on_inspector_changed()
        except Exception:
            pass

    def _on_pick_color(self):
        if self._target is None:
            return
        color = QColorDialog.getColor(self._target.defaultTextColor(), self)
        if color and color.isValid():
            self._target.setDefaultTextColor(color)
            self._color_btn.setStyleSheet(f"background: {color.name()}")
            try:
                if hasattr(self._target, "setSelected"):
                    self._target.setSelected(True)
                self._target.update()
            except Exception:
                pass
            try:
                if self._view and hasattr(self._view, "on_inspector_changed"):
                    self._view.on_inspector_changed()
                elif hasattr(self.parent(), "on_inspector_changed"):
                    self.parent().on_inspector_changed()
            except Exception:
                pass
