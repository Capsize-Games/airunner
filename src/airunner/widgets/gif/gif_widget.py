import os

from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.gif.templates.gif_widget_ui import Ui_gif_widget


class GifWidget(BaseWidget):
    widget_class_ = Ui_gif_widget
    gif_path = None

    def set_gif(self, gif_path):
        self.gif_path = gif_path

        # Create a QMovie object
        movie = QMovie(gif_path)

        # Create a QLabel object
        label = QLabel(self.ui.gif_frame)

        # Set the movie to the label
        label.setMovie(movie)

        # Start the movie
        movie.start()
    
    def delete_gif(self):
        if not self.gif_path:
            return
        os.remove(self.gif_path)
        # delete this widget
        self.deleteLater()