from functools import partial

from airunner.widgets.base_widget import BaseWidget


class LayerContainerWidget(BaseWidget):
    name = "layer_container_widget"
    icons = {
        "new_layer_button": "035-new",
        "layer_up_button": "041-up-arrow",
        "layer_down_button": "042-down-arrow",
        "merge_layer_button": "002-merge",
        "delete_layer_button": "006-trash",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initialize_buttons()

        # add stretch to bottom of scrollAreaWidgetContents
        self.scrollAreaWidgetContents.layout().addStretch()
        self.set_stylesheet()

    def initialize_buttons(self):
        self.template.new_layer_button.clicked.connect(self.app.canvas.new_layer)
        self.template.layer_up_button.clicked.connect(self.app.canvas.layer_up)
        self.template.layer_down_button.clicked.connect(self.app.canvas.layer_down)
        self.template.delete_layer_button.clicked.connect(self.app.canvas.delete_layer)
        self.template.merge_layer_button.clicked.connect(self.app.canvas.merge_selected_layers)

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet("""
            QFrame {
                padding: 0px;
            }
        """)
