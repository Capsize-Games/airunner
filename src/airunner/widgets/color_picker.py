from PySide6.QtCore import Qt, QObject
from PySide6.QtWidgets import QColorDialog


class ColorPicker(QColorDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setOptions(
            QColorDialog.ColorDialogOption.DontUseNativeDialog |
            QColorDialog.ColorDialogOption.NoButtons
        )
        self.delete_elements(self)
        try:
            color_picker_widget = self.findChild(QObject, "color_picker")
            # change this layout to qgridlayout
            # remove color_picker_widget from its parent
            color_picker_widget.setParent(None)
            # delete all children from this widget
            self.delete_elements(self)
            # add grid_layout to this widget
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.layout().addWidget(color_picker_widget)
        except Exception as e:
            print(e)

    def delete_elements(self, widget):
        # iterate over all children in layout and print their label names
        try:
            for child in widget.children():
                class_name = child.metaObject().className()
                if class_name in [
                    "QGridLayout", "QVBoxLayout",
                    "QWellArray", "QPushButton", "QDialogButtonBox", "QLabel",
                ]:
                    child.deleteLater()
                elif class_name == "QColorPicker":
                    # set a label name
                    child.setObjectName("color_picker")
                self.delete_elements(child)
        except Exception as e:
            print(e)
