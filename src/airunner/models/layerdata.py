import uuid
from PySide6.QtCore import QPoint

from airunner.models.imagedata import ImageData


class LayerData:
    def __init__(
        self,
        index: int,
        name: str,
        visible: bool = True,
        opacity: float = 1.0,
        offset: QPoint = QPoint(0, 0)
    ):
        self.index = index
        self.name = name
        self.visible = visible
        self.opacity = opacity
        self.offset = offset
        self.lines = []
        self.image_data = ImageData(
            position=QPoint(0, 0),
            image=None,
            opacity=1.0
        )
        self.widgets = []
        self.uuid = uuid.uuid4()

        self.left_line_extremity = None
        self.right_line_extremity = None
        self.top_line_extremity = None
        self.bottom_line_extremity = None
        self.last_left = 0
        self.last_top = 0
        self.min_x = 0
        self.min_y = 0
        self.last_pos = None
        self.color = None

    def clear(self):
        self.lines = []
        self.image_data = ImageData(
            position=QPoint(0, 0),
            image=None,
            opacity=1.0
        )
        self.widgets = []
        self.visible = True
        self.opacity = 1.0
