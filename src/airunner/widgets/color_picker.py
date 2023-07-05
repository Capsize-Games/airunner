from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QColorDialog


class ColorPicker(QColorDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setOptions(
            QColorDialog.ColorDialogOption.DontUseNativeDialog |
            QColorDialog.ColorDialogOption.NoButtons
        )
