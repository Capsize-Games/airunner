from PIL import Image
from PyQt6.QtCore import QRect, QPoint, Qt
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
from contextlib import contextmanager

from airunner.aihandler.logger import Logger
from airunner.data.models import Layer
from airunner.models.layerdata import LayerData
from airunner.data.session_scope import session_scope
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.layers.layer_widget import LayerWidget
from airunner.widgets.layers.templates.layer_container_ui import Ui_layer_container

class LayerContainerWidget(BaseWidget):
    widget_class_ = Ui_layer_container
    current_layer_index = 0
    layers = []
    selected_layers = {}

    @contextmanager
    def current_layer(self):
        with self.app.settings_manager.layers() as layers:
            if len(layers) == 0:
                self.add_layer()
            try:
                yield layers[self.current_layer_index]
            except IndexError:
                Logger.error(f"No current layer for index {self.current_layer_index}")

    def initialize(self):
        with self.current_layer() as current_layer:
            self.ui.scrollAreaWidgetContents.layout().addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
            # set the current_value property of the slider
            self.ui.opacity_slider_widget.set_slider_and_spinbox_values(current_layer.opacity)
            self.ui.opacity_slider_widget.initialize_properties()
            self.set_layer_opacity(current_layer.opacity)

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

    def add_layers(self):
        with self.app.settings_manager.layers() as layers:
            for layer in layers:
                self.add_layer_widget(layer, layer.position)

    def add_layer(self):
        self.app.history.add_event({
            "event": "new_layer",
            "layers": self.get_layers_copy(),
            "layer_index": self.current_layer_index
        })
        return self.create_layer()

    def create_layer(self):
        with self.app.settings_manager.document() as document:
            with self.app.settings_manager.layers() as layers:
                layer_data = Layer(
                    name=f"Layer {len(layers) + 1}",
                    document=document,
                    position=len(layers) + 1,
                    visible=True
                )
        
        with session_scope() as session:
            session.add(layer_data)

        # layer_name = f"Layer {len(self.layers) + 1}"
        index = 0
        with self.app.settings_manager.layers() as layers:
            layers.insert(index, layer_data)
            self.set_current_layer(index)
            self.add_layer_widget(layer_data, index)
        return index

    def add_layer_widget(self, layer_data, index):
        Logger.info(f"add_layer_widget index={index}")
        layer_widget = LayerWidget(layer_container=self, layer_data=layer_data, layer_index=index)

        self.ui.scrollAreaWidgetContents.layout().insertWidget(0, layer_widget)
        layer_widget.show()
        for layer_widget in self.ui.scrollAreaWidgetContents.findChildren(LayerWidget):
            layer_widget.reset_position()

    def move_layer_up(self):
        with self.app.settings_manager.layers() as layers:
            with self.current_layer() as current_layer:
                layer = current_layer
                index = layers.index(layer)
                if index == 0:
                    return
                # track the current layer order
                self.app.canvas.track_layer_move_history()
                layers.remove(layer)
                layers.insert(index - 1, layer)
                self.current_layer_index = index - 1
                self.show_layers()
                self.app.canvas.update()

    def move_layer_down(self):
        with self.app.settings_manager.layers() as layers:
            with self.current_layer() as layer:
                index = layers.index(layer)
                if index == len(layers) - 1:
                    return
                self.app.canvas.track_layer_move_history()
                layers.remove(layer)
                layers.insert(index + 1, layer)
                self.current_layer_index = index + 1
                self.show_layers()
                self.app.canvas.update()

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
                    self.app.canvas.delete_layer(layer=layer)

            # if we have a new image object, set it as the current layer image
            layer_index = self.app.canvas.get_index_by_layer(selected_layer)
            Logger.info("Setting current_layer_index={layer_index}")
            self.current_layer_index = layer_index
            with self.app.settings_manager.layers() as layers:
                if new_image:
                    layers[self.current_layer_index].image_data.image = new_image
                    layers[self.current_layer_index].image_data.position = QPoint(rect.x(), rect.y())

            # reset the selected layers dictionary and refresh the canvas
            self.selected_layers = {}
            self.show_layers()
            self.app.canvas.update()

    def get_layers_copy(self):
        with self.app.settings_manager.layers() as layers:
            return [layer for layer in layers]
    
    selected_layers = {}

    def delete_selected_layers(self):
        Logger.info("Deleting selected layers")
        self.app.history.add_event({
            "event": "delete_layer",
            "layers": self.get_layers_copy(),
            "layer_index": self.current_layer_index
        })
        for index, layer in self.selected_layers.items():
            self.delete_layer(index=index, layer=layer)
        self.selected_layers = {}
        self.show_layers()
        self.app.standard_image_panel.canvas_widget.do_draw()

    def delete_layer(self, _value=False, index=None, layer=None):
        Logger.info(f"delete_layer requested index {index}")
        with self.app.settings_manager.layers() as layers:
            current_index = index
            if layer and current_index is None:
                for layer_index, layer_object in enumerate(layers):
                    if layer_object is layer:
                        current_index = layer_index
            Logger.info(f"current_index={current_index}")
            if current_index is None:
                current_index = self.current_layer_index
            Logger.info(f"Deleting layer {current_index}")
            self.app.standard_image_panel.canvas_widget.delete_image()
            self.app.history.add_event({
                "event": "delete_layer",
                "layers": self.get_layers_copy(),
                "layer_index": current_index
            })
            try:
                with session_scope() as session:
                    session.delete(layers[current_index])
                with self.app.settings_manager.layers() as layers:
                    layer = layers.pop(current_index)
                layer.layer_widget.deleteLater()
            except IndexError as e:
                Logger.error(f"Could not delete layer {current_index}. Error: {e}")
            if len(layers) == 0:
                layers = [LayerData(0, "Layer 1")]
            self.show_layers()
            self.update()

    def clear_layers(self):
        # delete all widgets from self.container.layout()
        with self.app.settings_manager.layers() as layers:
            for index, layer in enumerate(layers):
                if not layer.layer_widget:
                    continue
                layer.layer_widget.deleteLater()
            layers = [LayerData(0, "Layer 1")]
            self.current_layer_index = 0

    def handle_layer_click(self, layer, index, event):
        Logger.info(f"handle_layer_click index={index}")
        # check if the control key is pressed
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if self.app.canvas.container:
                if index in self.selected_layers:
                    widget = self.selected_layers[index].layer_widget
                    if widget and index != self.current_layer_index:
                        widget.frame.setStyleSheet(self.app.css("layer_normal_style"))
                        del self.selected_layers[index]
                else:
                    item = self.app.canvas.container.layout().itemAt(index)
                    if item and index != self.current_layer_index:
                        self.selected_layers[index] = layer
                        self.selected_layers[index].layer_widget.frame.setStyleSheet(
                            self.app.css("secondary_layer_highlight_style")
                        )
        else:
            for data in self.selected_layers.values():
                data.layer_widget.frame.setStyleSheet(self.app.css("layer_normal_style"))
            self.set_current_layer(index)
            self.selected_layers = {}

    def set_current_layer(self, index):
        Logger.info(f"set_current_layer current_layer_index={index}")
        self.current_layer_index = index
        if not hasattr(self, "container"):
            return
        if self.app.canvas.container:
            item = self.app.canvas.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.app.css("layer_normal_style"))
        self.current_layer_index = index
        if self.app.canvas.container:
            item = self.app.canvas.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.app.css("layer_highlight_style"))
        # change the layer opacity
        # self.app.tool_menu_widget.set_opacity_slider(
        #     int(self.current_layer.opacity * 100)
        # )

    def track_layer_move_history(self):
        with self.app.settings_manager.layers() as layers:
            layer_order = []
            for layer in layers:
                layer_order.append(layer.uuid)
            self.app.history.add_event({
                "event": "move_layer",
                "layer_order": layer_order,
                "layer_index": self.current_layer_index
            })

    def get_layers_copy(self):
        with self.app.settings_manager.layers() as layers:
            return [layer for layer in layers]

    def get_index_by_layer(self, layer):
        with self.app.settings_manager.layers() as layers:
            for index, layer_object in enumerate(layers):
                if layer is layer_object:
                    return index
            return 0

    def toggle_layer_visibility(self, layer, layer_obj):
        # change the eye icon of the visible_button on the layer
        layer.visible = not layer.visible
        self.update()
        layer_obj.set_icon()
        self.app.canvas_widget.do_draw()

    def handle_move_layer(self, event):
        point = QPoint(
            event.pos().x() if self.app.canvas.drag_pos is not None else 0,
            event.pos().y() if self.app.canvas.drag_pos is not None else 0
        )
        # snap to grid
        grid_size = self.app.settings_manager.grid_settings.cell_size
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

        with self.app.settings_manager.layers() as layers:
            layers[self.current_layer_index].offset = point
        self.app.canvas.update()

    def get_layer_opacity(self, index):
        with self.app.settings_manager.layers() as layers:
            return layers[index].opacity

    def set_layer_opacity(self, opacity: int):
        with self.current_layer() as current_layer:
            current_layer.opacity = opacity

    def show_layers(self):
        pass