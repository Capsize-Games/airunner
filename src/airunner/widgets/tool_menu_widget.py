from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTabWidget, QGridLayout, QColorDialog, QVBoxLayout, QWidget, QLineEdit, QPushButton, \
    QSplitter
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.batch_widget import BatchWidget
from airunner.widgets.deterministic_widget import DeterministicWidget
from airunner.widgets.embeddings_container_widget import EmbeddingsContainerWidget
from airunner.widgets.layer_container_widget import LayerContainerWidget
from airunner.widgets.lora_container_widget import LoraContainerWidget
from airunner.widgets.slider_widget import SliderWidget


class ToolMenuWidget(BaseWidget):
    name = "tool_menu"

    def initialize(self):
        self.app.tab_widget = QTabWidget()
        self.app.tab_widget.setLayout(QGridLayout())
        self.app.tab_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.lora_container_widget = LoraContainerWidget(app=self.app)
        self.embeddings_container_widget = EmbeddingsContainerWidget(app=self.app)
        self.batch_widget = BatchWidget(app=self.app)
        self.deterministic_widget = DeterministicWidget(app=self.app)
        self.app.tab_widget.setStyleSheet(self.app.css("toolmenu_tab_widget"))

        self.app.track_tab_section("right", "embeddings", "Embeddings", self.embeddings_container_widget, self.app.tab_widget)
        self.app.track_tab_section("right", "lora", "LoRA", self.lora_container_widget, self.app.tab_widget)

        self.layer_container_widget = LayerContainerWidget(app=self.app)
        self.opacity_widget = SliderWidget(
            app=self.app,
            label_text="Layer Opacity",
            slider_callback=self.app.canvas.set_layer_opacity
        )
        self.opacity_widget.slider.setValue(100)

        # self.lora_container_widget.toggleAllLora.clicked.connect(lambda checked, _tab=tab: self.toggle_all_lora(checked, _tab))

        # create a button that is set to the primary color and on click open a QColorDialog
        brush_color_widget_size = 128
        self.brush_color_widget = QPushButton()
        self.brush_color_widget.setFixedWidth(brush_color_widget_size)
        self.brush_color_widget.setFixedHeight(brush_color_widget_size)
        self.brush_color_widget.setStyleSheet(
            f"background-color: {self.settings_manager.settings.primary_color.get()};")
        self.brush_color_widget.clicked.connect(self.pick_brush_color)

        # create QColorDialog as a widget and add it to the right_toolbar
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
        grid.addWidget(self.brush_color_widget, 0, 0, 1, 1)
        grid.addWidget(input_box, 1, 0, 1, 1)
        self.app.track_tab_section("right", "pen", "Pen Color", widget, self.app.tab_widget)
        # prevent grid from stretching
        widget.setMaximumHeight(260)

        # add to grid
        #self.right_toolbar.layout().addWidget(self.brush_widget, 1, 0, 1, 1)

        # create a split widget and add it to the right_toolbar
        splitter = QSplitter(Qt.Orientation.Vertical)

        splitter.addWidget(self.app.tab_widget)
        splitter.addWidget(self.deterministic_widget)
        splitter.addWidget(self.batch_widget)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(5, 5, 5, 5)
        vbox.addWidget(self.opacity_widget)
        vbox.addWidget(self.layer_container_widget)
        container = QWidget()
        container.setLayout(vbox)
        splitter.addWidget(container)

        for n in range(4):
            splitter.setCollapsible(n, False)

        self.right_toolbar.layout().addWidget(splitter)

        for tab_name in self.app.tabs.keys():
            tab = self.app.tabs[tab_name]
            self.app.load_embeddings(tab)

    def pick_brush_color(self):
        current_color = self.settings_manager.settings.primary_color.get()
        # open QColorDialog and set the current color to the primary color
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.settings_manager.settings.primary_color.set(color.name())
            self.brush_color_widget.setStyleSheet(
                f"background-color: {self.settings_manager.settings.primary_color.get()};")

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

    def set_stylesheet(self):
        self.embeddings_container_widget.setStyleSheet(self.app.css("embeddings_container"))
        self.lora_container_widget.setStyleSheet(self.app.css("lora_container"))
        self.opacity_widget.set_stylesheet()
