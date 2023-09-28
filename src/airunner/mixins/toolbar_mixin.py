from PyQt6.QtWidgets import QColorDialog


class ToolbarMixin:
    def initialize(self):
        self.add_filters_to_action_bar()

    def add_filters_to_action_bar(self):
        pass

    def run_custom_filter(self):
        pass

    def do_invert(self):
        self.history.add_event({
            "event": "apply_filter",
            "layer_index": self.canvas.current_layer_index,
            "images": self.canvas.image_data_copy(self.canvas.current_layer_index),
        })
        self.canvas.invert_image()
        self.canvas.update()

    def do_film(self):
        self.canvas.film_filter()

    def show_canvas_color(self):
        # show a color widget dialog and set the canvas color
        color = QColorDialog.getColor()
        if color.isValid():
            color = color.name()
            self.settings_manager.set_value("canvas_color", color)
            self.canvas.set_canvas_color()
