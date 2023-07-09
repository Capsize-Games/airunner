from airunner.widgets.base_widget import BaseWidget


class LayerContainerWidget(BaseWidget):
    name = "layer_container_widget"
    icons = {
        "new_layer_button": "035-new",
        "layer_up_button": "041-up-arrow",
        "layer_down_button": "042-down-arrow",
        "delete_layer_button": "006-trash"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # add stretch to bottom of scrollAreaWidgetContents
        self.scrollAreaWidgetContents.layout().addStretch()
        self.set_stylesheet()

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet("""
            QFrame {
                padding: 0px;
            }
        """)
