from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtWidgets import QFrame, QLabel, QGridLayout

from airunner.widgets.base_widget import BaseWidget


class CanvasWidget(BaseWidget):
    name = "canvas"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.initialize_debugging()

    def initialize_debugging(self):
        # create a panel that will contain labels for debugging
        # and add the panel to the canvas, overlapping it
        frame = QFrame(self)
        grid = QGridLayout()
        frame.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); font-size: 9pt;")
        frame.setFixedSize(300, 300)
        frame.move(0, 300)

        # create labels
        labels = [
            "outpaint_box_rect",
            "image_pivot_point",
            "image_root_point",
            "is_drawing_left",
            "is_drawing_right",
            "is_drawing_up",
            "is_drawing_down",
            "x_overlap",
            "y_overlap",
            "new_dimensions",
            "current_image_position",
            "image_dimensions",
            "pos",
        ]
        for row, label_name in enumerate(labels):
            label = QLabel(frame)
            label.setStyleSheet("color: white;")
            label.setText(f"{label_name}: ")
            grid.addWidget(label, row, 0)
            setattr(self, label_name, QLabel(frame))
            getattr(self, label_name).setStyleSheet("color: white;")
            grid.addWidget(getattr(self, label_name), row, 1)

        # add stretch to bottom of frame to push labels to top
        grid.setRowStretch(len(labels), 1)

        frame.setLayout(grid)
        # self.set_debug_text()

    def set_debug_text(self, **kwargs):
        outpaint_box_rect = kwargs.get("outpaint_box_rect", QRect())
        image_pivot_point = kwargs.get("image_pivot_point", QPoint())
        image_root_point = kwargs.get("image_root_point", QPoint())
        is_drawing_left = kwargs.get("is_drawing_left", False)
        is_drawing_right = kwargs.get("is_drawing_right", False)
        is_drawing_up = kwargs.get("is_drawing_up", False)
        is_drawing_down = kwargs.get("is_drawing_down", False)
        x_overlap = kwargs.get("x_overlap", 0)
        y_overlap = kwargs.get("y_overlap", 0)
        new_dimensions = kwargs.get("new_dimensions", (0, 0))
        current_image_position = kwargs.get("current_image_position", QPoint())
        image_dimensions = kwargs.get("image_dimensions", (0, 0))
        pos = kwargs.get("pos", (0, 0))
        self.outpaint_box_rect.setText(f"{outpaint_box_rect.x()}, {outpaint_box_rect.y()}, {outpaint_box_rect.width()}, {outpaint_box_rect.height()}")
        self.image_pivot_point.setText(f"{image_pivot_point.x()}, {image_pivot_point.y()}")
        self.image_root_point.setText(f"{image_root_point.x()}, {image_root_point.y()}")
        self.is_drawing_left.setText(f"{is_drawing_left}")
        self.is_drawing_right.setText(f"{is_drawing_right}")
        self.is_drawing_up.setText(f"{is_drawing_up}")
        self.is_drawing_down.setText(f"{is_drawing_down}")
        self.x_overlap.setText(f"{x_overlap}")
        self.y_overlap.setText(f"{y_overlap}")
        self.new_dimensions.setText(f"{new_dimensions[0]}, {new_dimensions[1]}")
        self.current_image_position.setText(f"{current_image_position.x()}, {current_image_position.y()}")
        self.image_dimensions.setText(f"{image_dimensions[0]}, {image_dimensions[1]}")
        self.pos.setText(f"{pos[0]}, {pos[1]}")
