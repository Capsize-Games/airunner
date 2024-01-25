from PIL import Image
from PyQt6.QtCore import QRect, QPoint, Qt
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.enums import SignalCode, ServiceCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.layer_widget import LayerWidget
from airunner.widgets.layers.templates.layer_container_ui import Ui_layer_container

class LayerContainerWidget(BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.SHOW_LAYERS_SIGNAL, self.on_show_layers_signal)
        self.register(SignalCode.ADD_LAYER_SIGNAL, self)
        self.register_service("get_index_by_layer", self.get_index_by_layer)
        self.widget_class_ = Ui_layer_container
        self.selected_layers = {}
        self.layers = []
        self.current_layer_index = 0

    def initialize(self):
        current_layer = self.get_service(ServiceCode.CURRENT_LAYER)()
        self.ui.layers.scrollAreaWidgetContents.layout().addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        # set the current_value property of the slider
        self.ui.opacity_slider_widget.set_slider_and_spinbox_values(current_layer["opacity"])
        self.ui.opacity_slider_widget.initialize()
        self.set_layer_opacity(current_layer["opacity"])

    def action_clicked_button_add_new_layer(self):
        self.add_layer()

    def action_clicked_button_move_layer_up(self):
        self.move_layer_up()

    def action_clicked_button_move_layer_down(self):
        self.move_layer_down()

    def action_clicked_button_merge_selected_layers(self):
        self.merge_selected_layers()

    def action_clicked_button_delete_selected_layers(self):
        self.delete_selected_layers()
        self.delete_layer()
    
    def on_add_layer_signal(self, layer):
        self.add_layer()

    def add_layers(self):
        for layer in self.settings["layers"]:
            self.add_layer_widget(layer, layer.position)

    def add_layer(self):
        self.emit(SignalCode.CREATE_LAYER_SIGNAL)

    def add_layer_widget(self, layer_data, index):
        self.logger.info(f"add_layer_widget index={index}")
        layer_widget = LayerWidget(layer_container=self, layer_data=layer_data, layer_index=index)

        self.ui.scrollAreaWidgetContents.layout().insertWidget(0, layer_widget)
        layer_widget.show()
        for layer_widget in self.ui.scrollAreaWidgetContents.findChildren(LayerWidget):
            layer_widget.reset_position()

    def move_layer_up(self):
        self.emit(SignalCode.MOVE_LAYER_UP_SIGNAL)
        self.show_layers()
        self.emit(SignalCode.UPDATE_CANVAS_SIGNAL)

    def move_layer_down(self):
        self.emit(SignalCode.MOVE_LAYER_DOWN_SIGNAL)
        self.show_layers()
        self.emit(SignalCode.UPDATE_CANVAS_SIGNAL)

    def merge_selected_layers(self):
        with self.current_layer() as current_layer:
            if self.current_layer_index not in self.selected_layers:
                self.selected_layers[self.current_layer_index] = current_layer

            selected_layer = self.current_layer

            # get the rect of the new image based on the existing images extremities
            # (left, top, width and height)
            rect = QRect()
            for layer in self.selected_layers.values():
                image = layer.image_data.image
                if image:
                    if (image.width+layer.image_data.position.x()) > rect.width():
                        rect.setWidth(image.width+abs(layer.image_data.position.x()))
                    if (image.height+layer.image_data.position.y()) > rect.height():
                        rect.setHeight(image.height+abs(layer.image_data.position.y()))
                    if layer.image_data.position.x() < rect.x():
                        rect.setX(layer.image_data.position.x())
                    if layer.image_data.position.y() < rect.y():
                        rect.setY(layer.image_data.position.y())

            new_image = Image.new("RGBA", (rect.width(), rect.height()), (0, 0, 0, 0))

            for index, layer in self.selected_layers.items():
                # get an image object and merge it into the new image if it exists
                image = layer.image_data.image
                if image:
                    x = layer.image_data.position.x()
                    if x < 0:
                        x = 0
                    y = layer.image_data.position.y()
                    if y < 0:
                        y = 0
                    new_image.alpha_composite(
                        image,
                        (x, y)
                    )

                # delete any layers which are not the current layer index
                if index != self.current_layer_index:
                    self.emit(SignalCode.DELETE_LAYER_SIGNAL, dict(
                        layer=layer,
                    ))

            # if we have a new image object, set it as the current layer image
            layer_index = self.get_service("get_index_by_layer", selected_layer)
            self.logger.info("Setting current_layer_index={layer_index}")
            self.current_layer_index = layer_index
            settings = self.settings
            if new_image:
                settings["layers"][self.current_layer_index].image_data.image = new_image
                settings["layers"][self.current_layer_index].image_data.position = QPoint(rect.x(), rect.y())
            self.settings = settings

            # reset the selected layers dictionary and refresh the canvas
            self.selected_layers = {}
            self.show_layers()
            self.emit(SignalCode.UPDATE_CANVAS_SIGNAL)

    selected_layers = {}

    def delete_selected_layers(self):
        self.logger.info("Deleting selected layers")
        for index, layer in self.selected_layers.items():
            self.delete_layer(index=index, layer=layer)
        self.selected_layers = {}
        self.show_layers()
        self.emit(SignalCode.CANVAS_DO_DRAW_SIGNAL)

    def delete_layer(self, _value=False, index=None, layer=None):
        self.emit(SignalCode.DELETE_LAYER_SIGNAL, dict(
            index=index,
            layer=layer
        ))

    def clear_layers(self):
        self.emit(SignalCode.CLEAR_LAYERS_SIGNAL)
    
    def set_current_layer(self, index):
        self.emit(SignalCode.SET_CURRENT_LAYER_SIGNAL, index)

    def handle_layer_click(self, layer, index, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.emit(SignalCode.CANVAS_HANDLE_LAYER_CLICK_SIGNAL, dict(
                layer=layer,
                index=index,
                selected_layers=self.selected_layers,
                current_layer_index=self.current_layer_index
            ))
        else:
            self.set_current_layer((index, self.current_layer_index))
            self.selected_layers = {}

    def track_layer_move_history(self):
        layers = self.settings["layers"]
        layer_order = []
        for layer in layers:
            layer_order.append(layer["uuid"])

    def get_index_by_layer(self, layer):
        for index, layer_object in enumerate(self.settings["layers"]):
            if layer is layer_object:
                return index
        return 0

    def toggle_layer_visibility(self, layer, layer_obj):
        # change the eye icon of the visible_button on the layer
        layer.visible = not layer.visible
        self.update()
        layer_obj.set_icon()
        self.emit(SignalCode.CANVAS_DO_DRAW_SIGNAL)

    def handle_move_layer(self, event):
        point = QPoint(
            event.pos().x() if self.get_service("canvas_drag_pos")() is not None else 0,
            event.pos().y() if self.get_service("canvas_drag_pos")() is not None else 0
        )
        # snap to grid
        grid_size = self.grid_settings["cell_size"]
        point.setX(point.x() - (point.x() % grid_size))
        point.setY(point.y() - (point.y() % grid_size))

        # center the image
        # point.setX(int((point.x() - self.current_layer.images[0].image.size[0] / 2)))
        # point.setY(int((point.y() - self.current_layer.images[0].image.size[1] / 2)))

        # establish a rect based on line points - we need the area that is being moved
        # so that we can center the point on it
        with self.current_layer() as current_layer:
            rect = QRect()
            for line in current_layer.lines:
                rect = rect.united(QRect(line.start_point, line.end_point))

            try:
                rect = rect.united(QRect(
                    current_layer.image_data.position.x(),
                    current_layer.image_data.position.y(),
                    current_layer.image_data.image.size[0],
                    current_layer.image_data.image.size[1]
                ))
            except IndexError:
                pass

        # center the point on the rect
        point.setX(int(point.x() - int(rect.width() / 2)))
        point.setY(int(point.y() - int(rect.height() / 2)))

        self.emit(SignalCode.UPDATE_CURRENT_LAYER_SIGNAL, dict(
            offset=point
        ))
        self.emit(SignalCode.UPDATE_CANVAS_SIGNAL)

    def get_layer_opacity(self, index):
        layers = self.settings["layers"]
        return layers[index]["opacity"]

    def set_layer_opacity(self, opacity: int):
        self.emit(SignalCode.UPDATE_CURRENT_LAYER_SIGNAL, dict(
            opacity=opacity
        ))

    def on_show_layers_signal(self):
        self.show_layers()

    def show_layers(self):
        self.logger.info("TODO: show_layers")