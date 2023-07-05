from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget, QGridLayout, QColorDialog, QVBoxLayout, QWidget
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
        self.tab_widget.setStyleSheet("""
            QTabBar::tab { 
                font-size: 10pt;
            }
            QTabWidget::pane { 
                border: 0;
                border-top: 1px solid #121212;
                border-bottom: 1px solid #121212;
                border-radius: 0px; 
            }
            QTabBar::tab { 
                border-radius: 0px; 
                margin: 0px; 
                padding: 5px 10px;
                border: 0px;
            }
            QTabBar::tab:selected { 
                background-color: #5483d0;
                color: white;
                border: 0px;
            }
        """)

        self.tab_widget.addTab(self.embeddings_container_widget, "Embeddings")
        self.tab_widget.addTab(self.lora_container_widget, "LoRa")
        self.embeddings_container_widget.setStyleSheet("""
        background-color: #151515;
        """)
        self.lora_container_widget.setStyleSheet("""
        background-color: #151515;
        """)

        self.layer_container_widget = LayerContainerWidget(app=self.app)
        self.opacity_widget = SliderWidget(
            label_text="Layer Opacity:",
            slider_callback=self.app.canvas.set_layer_opacity,
        )
        self.opacity_widget.slider.setValue(100)

        # self.lora_container_widget.toggleAllLora.clicked.connect(lambda checked, _tab=tab: self.toggle_all_lora(checked, _tab))

        # create QColorDialog as a widget and add it to the right_toolbar
        color_dialog = ColorPicker()
        color_dialog.colorSelected.connect(self.handle_color_selected)
        color_dialog.currentColorChanged.connect(self.handle_current_color_changed)

        self.tab_widget.addTab(color_dialog, "Pen Color")

        # add to grid
        #self.right_toolbar.layout().addWidget(self.brush_widget, 1, 0, 1, 1)
        self.right_toolbar.layout().addWidget(self.tab_widget, 0, 0, 1, 1)
        self.right_toolbar.layout().addWidget(self.opacity_widget, 1, 0, 1, 1)
        self.right_toolbar.layout().addWidget(self.layer_container_widget, 2, 0, 1, 1)

        self.initialize_layer_buttons()
        #self.brush_widget.primary_color_button.clicked.connect(self.app.set_primary_color)

    def handle_color_selected(self, val):
        print("color selected", val)

    def handle_current_color_changed(self, val):
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
        self.layer_container_widget.set_stylesheet()
        self.layer_container_widget.setStyleSheet("""
            #layers {
                border: 0px;
                background-color: #151515;
            }
        """)
