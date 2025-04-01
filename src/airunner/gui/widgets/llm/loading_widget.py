import os

from PySide6.QtGui import QMovie
from PySide6.QtCore import QSize

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.templates.loading_ui import Ui_loading_message


class LoadingWidget(BaseWidget):
    widget_class_ = Ui_loading_message

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        here = os.path.dirname(os.path.abspath(__file__))
        movie = QMovie(os.path.join(here, "../../icons/dark/Spinner-1s-200px.gif"))
        movie.setScaledSize(QSize(64, 64))  # Resize the GIF
        self.ui.label.setMovie(movie)  # Set the QMovie object to the label
        movie.start()  # Start the animation

    def set_size(self, spinner_size: QSize, label_size: QSize):
        self.ui.label.movie().setScaledSize(spinner_size)
        self.ui.label.setFixedSize(label_size)
        self.ui.label.update()
        self.ui.label.repaint()
