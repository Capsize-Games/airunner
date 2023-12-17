from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QMovie

from airunner.widgets.canvas_plus.standard_base_widget import StandardBaseWidget
from airunner.widgets.canvas_plus.templates.standard_gif_widget_ui import Ui_standard_gif_widget


class StandardGifWidget(StandardBaseWidget):
    widget_class_ = Ui_standard_gif_widget
    gif_path = None

    def handle_image_data(self, data):
        pass

    def load_image_from_path(self, gif_path):
        self.gif_path = gif_path

        # Create a QMovie object
        movie = QMovie(gif_path)

        # Create a QLabel object
        label = QLabel(self.ui.image_frame)

        # Set the movie to the label
        label.setMovie(movie)

        self.ui.image_frame.show()

        # Start the movie
        movie.start()