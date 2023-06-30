from airunner.canvas import Canvas


class CanvasMixin:
    def initialize(self):
        self.canvas = Canvas(parent=self)
        self.settings_manager.settings.show_grid.my_signal.connect(self.canvas.update)
        self.settings_manager.settings.snap_to_grid.my_signal.connect(self.canvas.update)
        self.settings_manager.settings.line_color.my_signal.connect(self.canvas.update_grid_pen)
