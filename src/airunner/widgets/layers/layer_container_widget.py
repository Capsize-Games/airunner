from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.layer_widget import LayerWidget
from airunner.widgets.layers.templates.layer_container_ui import Ui_layer_container


class LayerContainerWidget(BaseWidget):
    widget_class_ = Ui_layer_container

    def initialize(self):
        self.load_layer_widgets()

    def load_layer_widgets(self):
        for layer_data in self.app.canvas.layers:
            self.add_layer_widget(layer_data)

    def add_layer_widget(self, layer_data):
        layer_widget = LayerWidget(self, layer_data=layer_data)
        self.ui.scrollAreaWidgetContents.layout().addWidget(layer_widget)
        layer_widget.show()

    def action_clicked_button_add_new_layer(self):
        pass

    def action_clicked_button_move_layer_up(self):
        pass

    def action_clicked_button_move_layer_down(self):
        pass

    def action_clicked_button_merge_selected_layers(self):
        pass

    def action_clicked_button_delete_selected_layers(self):
        pass
