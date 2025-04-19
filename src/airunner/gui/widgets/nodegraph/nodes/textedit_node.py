from PySide6 import QtWidgets
from NodeGraphQt import NodeBaseWidget
from NodeGraphQt.constants import ViewerEnum


class TextEditNode(NodeBaseWidget):
    NODE_NAME = "TextEdit Node"

    def __init__(
        self, parent=None, name="", label="", text="", placeholder_text=""
    ):
        super(TextEditNode, self).__init__(parent, name, label)
        bg_color = ViewerEnum.BACKGROUND_COLOR.value
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255), bg_color))
        text_sel_color = text_color
        style_dict = {
            "QPlainTextEdit": {
                "background": "rgba({0},{1},{2},20)".format(*bg_color),
                "border": "1px solid rgb({0},{1},{2})".format(
                    *ViewerEnum.GRID_COLOR.value
                ),
                "border-radius": "3px",
                "color": "rgba({0},{1},{2},150)".format(*text_color),
                "selection-background-color": "rgba({0},{1},{2},100)".format(
                    *text_sel_color
                ),
            }
        }
        stylesheet = ""
        for css_class, css in style_dict.items():
            style = "{} {{\n".format(css_class)
            for elm_name, elm_val in css.items():
                style += "  {}:{};\n".format(elm_name, elm_val)
            style += "}\n"
            stylesheet += style
        editor = QtWidgets.QPlainTextEdit()
        editor.setPlainText(text)
        editor.setPlaceholderText(placeholder_text)
        editor.setStyleSheet(stylesheet)
        editor.textChanged.connect(self.on_value_changed)
        editor.clearFocus()
        self.set_custom_widget(editor)
        self.widget().setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    @property
    def type_(self):
        return "LineEditNodeWidget"

    def get_value(self):
        """
        Returns the widgets current text.

        Returns:
            str: current text.
        """
        return str(self.get_custom_widget().toPlainText())

    def set_value(self, text=""):
        """
        Sets the widgets current text.

        Args:
            text (str): new text.
        """
        if text != self.get_value():
            self.get_custom_widget().setPlainText(text)
            self.on_value_changed()
