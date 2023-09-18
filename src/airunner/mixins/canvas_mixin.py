from airunner.canvas import Canvas


class CanvasMixin:
    def initialize(self):
        self.canvas = Canvas(parent=self)
