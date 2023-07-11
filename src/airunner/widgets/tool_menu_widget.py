from PyQt6.QtWidgets import QTabWidget, QGridLayout, QColorDialog, QVBoxLayout, QWidget, QLineEdit
from airunner.widgets.base_widget import BaseWidget
#from airunner.widgets.brush_widget import BrushWidget
from airunner.widgets.color_picker import ColorPicker
from airunner.widgets.embeddings_container_widget import EmbeddingsContainerWidget
from airunner.widgets.layer_container_widget import LayerContainerWidget
from airunner.widgets.lora_container_widget import LoraContainerWidget
from airunner.widgets.slider_widget import SliderWidget


class ToolMenuWidget(BaseWidget):
    name = "tool_menu"

    def initialize(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setLayout(QGridLayout())
        self.tab_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.lora_container_widget = LoraContainerWidget(app=self.app)
        self.embeddings_container_widget = EmbeddingsContainerWidget(app=self.app)
        self.tab_widget.setStyleSheet(self.app.css("toolmenu_tab_widget"))

        self.tab_widget.addTab(self.embeddings_container_widget, "Embeddings")
        self.tab_widget.addTab(self.lora_container_widget, "LoRa")

        self.layer_container_widget = LayerContainerWidget(app=self.app)
        self.opacity_widget = SliderWidget(
            app=self.app,
            label_text="Layer Opacity:",
            slider_callback=self.app.canvas.set_layer_opacity
        )
        self.opacity_widget.slider.setValue(100)

        # self.lora_container_widget.toggleAllLora.clicked.connect(lambda checked, _tab=tab: self.toggle_all_lora(checked, _tab))

        # create QColorDialog as a widget and add it to the right_toolbar
        color_dialog = ColorPicker()
        color_dialog.currentColorChanged.connect(self.handle_current_color_changed)
        # add a input box to the layout
        input_box = QLineEdit()
        input_box.setPlaceholderText("Enter a hex color")
        input_box.setFixedWidth(200)
        input_box.setFixedHeight(30)
        input_box.setObjectName("color_picker_input_box")
        self.layout().addWidget(input_box)
        self.color_input_box = input_box

        widget = QWidget()
        grid = QGridLayout(widget)
        grid.addWidget(color_dialog, 0, 0, 1, 1)
        grid.addWidget(input_box, 1, 0, 1, 1)
        self.tab_widget.addTab(widget, "Pen Color")
        # prevent grid from stretching
        widget.setMaximumHeight(260)

        # add to grid
        #self.right_toolbar.layout().addWidget(self.brush_widget, 1, 0, 1, 1)
        self.right_toolbar.layout().addWidget(self.tab_widget, 0, 0, 1, 1)
        self.right_toolbar.layout().addWidget(self.opacity_widget, 1, 0, 1, 1)
        self.right_toolbar.layout().addWidget(self.layer_container_widget, 2, 0, 1, 1)

        self.initialize_layer_buttons()
        #self.brush_widget.primary_color_button.clicked.connect(self.app.set_primary_color)

    def handle_current_color_changed(self, val):
        self.color_input_box.setText(val.name())
        self.settings_manager.settings.primary_color.set(val.name())

    def set_opacity_slider(self, val):
        self.opacity_widget.update_value(val)

    def reset_brush_colors(self):
        # self.brush_widget.primary_color_button.setStyleSheet(
        #     f"background-color: {self.settings_manager.settings.primary_color.get()};")
        # self.brush_widget.brush_size_slider.setValue(
        #     self.settings_manager.settings.size.get())
        pass

    def initialize_layer_buttons(self):
        self.layer_container_widget.new_layer_button.clicked.connect(self.app.canvas.new_layer)
        self.layer_container_widget.layer_up_button.clicked.connect(self.app.canvas.layer_up)
        self.layer_container_widget.layer_down_button.clicked.connect(self.app.canvas.layer_down)
        self.layer_container_widget.delete_layer_button.clicked.connect(self.app.canvas.delete_layer)

    def set_stylesheet(self):
        self.layer_container_widget.setStyleSheet(self.app.css("layer_container_widget"))
        self.layer_container_widget.setStyleSheet(self.app.css("layer_container_widget"))
        self.embeddings_container_widget.setStyleSheet(self.app.css("embeddings_container"))
        self.lora_container_widget.setStyleSheet(self.app.css("lora_container"))
