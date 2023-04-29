from PyQt6.QtCore import QPointF
from airunner.balloon import Balloon


class ComicMixin:
    def initialize(self):
        self.window.wordballoon_button.clicked.connect(self.word_balloon_button_clicked)

    def word_balloon_button_clicked(self):
        """
        Create and add a word balloon to the canvas.
        :return:
        """
        # create a word balloon
        word_balloon = Balloon()
        word_balloon.setGeometry(100, 100, 200, 100)
        word_balloon.set_tail_pos(QPointF(50, 100))
        # add the widget to the canvas
        self.history.add_event({
            "event": "add_widget",
            "layer_index": self.canvas.current_layer_index,
            "widgets": self.canvas.current_layer.widgets.copy(),
        })
        self.canvas.current_layer.widgets.append(word_balloon)
        self.show_layers()
        self.canvas.update()
