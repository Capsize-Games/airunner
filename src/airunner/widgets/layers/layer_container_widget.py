from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.layer_widget import LayerWidget
from airunner.widgets.layers.templates.layer_container_ui import Ui_layer_container


class LayerContainerWidget(BaseWidget):
    widget_class_ = Ui_layer_container

    def initialize(self):
        self.load_layer_widgets()

    def load_layer_widgets(self):
        for index, layer_data in enumerate(self.app.canvas.layers):
            self.add_layer_widget(layer_data, index)

    def add_layer_widget(self, layer_data, index):
        layer_widget = LayerWidget(self, layer_data=layer_data, layer_index=index)
        self.ui.scrollAreaWidgetContents.layout().addWidget(layer_widget)
        layer_widget.show()

    def action_clicked_button_add_new_layer(self):
        layer_data, index = self.canvas.add_layer()
        self.add_layer_widget(layer_data, index)

    def action_clicked_button_move_layer_up(self):
        self.canvas.move_layer_up(self.canvas.current_layer)

    def action_clicked_button_move_layer_down(self):
        self.canvas.move_layer_down(self.canvas.current_layer)

    def action_clicked_button_merge_selected_layers(self):
        self.canvas.merge_selected_layers()

    def action_clicked_button_delete_selected_layers(self):
        self.canvas.delete_selected_layers()
