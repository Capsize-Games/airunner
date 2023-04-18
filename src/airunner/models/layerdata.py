import uuid
from PyQt6.QtCore import QPoint


class LayerData:
    @property
    def image(self):
        if len(self.images) > 0:
            return self.images[0]
        return None

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
        self.images = []
        self.widgets = []
        self.uuid = uuid.uuid4()

    def clear(self, index):
        self.index = index
        self.lines = []
        self.images = []
        self.widgets = []
        self.visible = True
        self.opacity = 1.0
        self.name = f"Layer {self.index + 1}"
