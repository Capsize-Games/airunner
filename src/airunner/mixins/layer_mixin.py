import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QIcon


class LayerMixin:
    """
    This is a mixin class for the main window that handles the layer manager.
    """
    @property
    def layer_highlight_style(self):
        return f"background-color: #c7f6fc; border: 1px solid #000000; color: #000000;"

    @property
    def layer_normal_style(self):
        return "background-color: #ffffff; border: 1px solid #333333; color: #333;"

    def initialize(self):
        self.window.new_layer.clicked.connect(self.new_layer)
        self.window.layer_up_button.clicked.connect(self.layer_up_button)
        self.window.layer_down_button.clicked.connect(self.layer_down_button)
        self.window.delete_layer_button.clicked.connect(self.delete_layer_button)

    def layer_up_button(self):
        self.canvas.move_layer_up(self.canvas.current_layer)
        self.show_layers()

    def layer_down_button(self):
        self.canvas.move_layer_down(self.canvas.current_layer)
        self.show_layers()

    def delete_layer_button(self):
        self.canvas.delete_layer(self.canvas.current_layer_index)
        self.show_layers()

    def new_layer(self):
        self.canvas.add_layer()
        self.show_layers()

    def show_layers(self):
        """
        This function is called when the layers need to be updated.
        :return:
        """

        # create an object which can contain a layer_obj and then be added to layers.setWidget
        container = QWidget()
        container.setLayout(QVBoxLayout())

        for layer in self.canvas.layers:
            index = self.canvas.layers.index(layer)
            layer_obj = uic.loadUi(os.path.join("pyqt/layer.ui"))
            layer_obj.layer_name.setText(layer.name)

            layer_obj.opacity_slider.valueChanged.connect(
                lambda val, _layer=layer_obj, _index=index: self.slider_set_layer_opacity(val, _layer, _index))
            layer_obj.opacity_spinbox.valueChanged.connect(
                lambda val, _layer=layer_obj, _index=index: self.spinbox_set_layer_opacity(val, _layer, _index))
            opacity = self.canvas.get_layer_opacity(index)
            layer_obj.opacity_slider.setValue(int(opacity * 100))
            layer_obj.opacity_spinbox.setValue(opacity)

            # onclick of layer_obj set as the current layer index on self.canvas
            layer_obj.mousePressEvent = lambda event, _layer=layer, _index=index: self.set_current_layer(_index)

            # show a border around layer_obj if it is the selected index
            if self.canvas.current_layer_index == index:
                layer_obj.frame.setStyleSheet(self.layer_highlight_style)
            else:
                layer_obj.frame.setStyleSheet(self.layer_normal_style)

            layer_obj.visible_button.setIcon(QIcon("src/icons/eye.png" if layer.visible else "src/icons/eye-off.png"))
            layer_obj.visible_button.clicked.connect(
                lambda _, _layer=layer, _layer_obj=layer_obj: self.toggle_layer_visibility(_layer, _layer_obj))

            container.layout().addWidget(layer_obj)

        # add a spacer to the bottom of the container
        container.layout().addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.window.layers.setWidget(container)
        self.container = container

    def slider_set_layer_opacity(self, val, layer_obj, index):
        val = val / 100
        self.canvas.set_layer_opacity(index, val)
        layer_obj.opacity_spinbox.setValue(val)
        self.canvas.layers[index].opacity = val

    def spinbox_set_layer_opacity(self, val, layer_obj, index):
        self.canvas.set_layer_opacity(index, val)
        val = int(val * 100)
        layer_obj.opacity_slider.setValue(val)
        self.canvas.layers[index].opacity = val

    def toggle_layer_visibility(self, layer, layer_obj):
        # change the eye icon of the visible_button on the layer
        self.canvas.toggle_layer_visibility(layer)
        layer_obj.visible_button.setIcon(QIcon("src/icons/eye.png" if layer.visible else "src/icons/eye-off.png"))

    def set_current_layer(self, index):
        if not hasattr(self, "container"):
            return
        if self.container:
            item = self.container.layout().itemAt(self.canvas.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.layer_normal_style)
        self.canvas.current_layer_index = index
        if self.container:
            item = self.container.layout().itemAt(self.canvas.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.layer_highlight_style)

    def delete_layer(self):
        pass
