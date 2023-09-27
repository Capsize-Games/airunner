from functools import partial
from airunner.pyqt.widgets.base_widget import BaseWidget


class EmbeddingWidget(BaseWidget):
    name = "widgets/embedding"

    def __init__(self, *args, **kwargs):
        name = kwargs.pop("name", None)
        super().__init__(*args, **kwargs)
        self.label.setText(name)
        self.to_prompt_button.clicked.connect(partial(self.app.insert_into_prompt, f"{name}"))
        self.to_negative_prompt_button.clicked.connect(partial(self.app.insert_into_prompt, f"{name}", True))
        button_styles = """
        QPushButton {
        font-size: 8pt;
        border: 1px solid #222222;
        }
        QPushButton:hover {
        background-color: #2e3440;
        }
        QPushButton:pressed {
        background-color: #3b4252;
        }
        """
        self.to_prompt_button.setStyleSheet(button_styles)
        self.to_negative_prompt_button.setStyleSheet(button_styles)
        self.layout().setVerticalSpacing(3)
        self.layout().setHorizontalSpacing(6)
