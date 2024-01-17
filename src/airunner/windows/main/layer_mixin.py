import base64
import io
import uuid

from PyQt6.QtGui import QPixmap

from PIL import Image


class LayerMixin:
    def add_layer(self):
        settings = self.settings
        total_layers = len(self.settings['layers'])
        name=f"Layer {total_layers + 1}"
        settings["layers"].append(dict(
            name=name,
            visible=True,
            opacity=100,
            position=total_layers,
            base_64_image="",
            pos_x=0,
            pos_y=0,
            pivot_point_x=0,
            pivot_point_y=0,
            root_point_x=0,
            root_point_y=0,
            uuid=str(uuid.uuid4()),
            pixmap=QPixmap(),
        ))
        self.settings = settings
        return total_layers

    def current_draggable_pixmap(self):
        return self.current_layer()["pixmap"]

    def delete_layer(self, index, layer):
        self.logger.info(f"delete_layer requested index {index}")
        layers = self.settings["layers"]
        current_index = index
        if layer and current_index is None:
            for layer_index, layer_object in enumerate(layers):
                if layer_object is layer:
                    current_index = layer_index
        self.logger.info(f"current_index={current_index}")
        if current_index is None:
            current_index = self.settings["current_layer_index"]
        self.logger.info(f"Deleting layer {current_index}")
        self.standard_image_panel.canvas_widget.delete_image()
        try:
            layer = layers.pop(current_index)
            layer.layer_widget.deleteLater()
        except IndexError as e:
            self.logger.error(f"Could not delete layer {current_index}. Error: {e}")
        if len(layers) == 0:
            self.add_layer()
            self.switch_layer(0)
        settings = self.settings
        settings["layers"] = layers
        self.settings = settings
        self.show_layers()
        self.update()
    
    def clear_layers(self):
        # delete all widgets from self.container.layout()
        layers = self.settings["layers"]
        for index, layer in enumerate(layers):
            if not layer.layer_widget:
                continue
            layer.layer_widget.deleteLater()
        self.add_layer()
        settings = self.settings
        settings["layers"] = layers
        self.settings = settings
        self.switch_layer(0)
    
    def set_current_layer(self, index):
        self.logger.info(f"set_current_layer current_layer_index={index}")
        self.current_layer_index = index
        if not hasattr(self, "container"):
            return
        if self.canvas.container:
            item = self.canvas.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.css("layer_normal_style"))
        self.current_layer_index = index
        if self.canvas.container:
            item = self.canvas.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.css("layer_highlight_style"))

    def move_layer_up(self):
        layer = self.current_layer()
        settings = self.settings
        index = self.settings["current_layer_index"]
        if index == 0:
            return
        layers = settings["layers"]
        layers.remove(layer)
        layers.insert(index - 1, layer)
        self.settings["current_layer_index"] = index - 1
        settings["layers"] = layers
        self.settings = settings
    
    def move_layer_down(self):
        layer = self.current_layer()
        settings = self.settings
        index = self.settings["current_layer_index"]
        if index == len(settings["layers"]) - 1:
            return
        layers = settings["layers"]
        layers.remove(layer)
        layers.insert(index + 1, layer)
        self.settings["current_layer_index"] = index + 1
        settings["layers"] = layers
        self.settings = settings
    
    def current_layer(self):
        if len(self.settings["layers"]) == 0:
            self.add_layer()
        try:
            return self.settings["layers"][self.settings["current_layer_index"]]
        except IndexError:
            self.logger.error(f"Unable to get current layer with index {self.settings['current_layer_index']}")

    def update_current_layer(self, data):
        settings = self.settings
        layer = settings["layers"][settings["current_layer_index"]]
        for k, v in data.items():
            layer[k] = v
        settings["layers"][settings["current_layer_index"]] = layer
        self.settings = settings
    
    def update_layer(self, data):
        uuid = data["uuid"]
        settings = self.settings
        for index, layer in enumerate(settings["layers"]):
            if layer["uuid"] == uuid:
                for k, v in data.items():
                    layer[k] = v
                settings["layers"][index] = layer
                self.settings = settings
                return
        self.logger.error(f"Unable to find layer with uuid {uuid}")

    
    def switch_layer(self, layer_index):
        settings = self.settings
        settings["current_layer_index"] = layer_index
        self.settings = settings

    def delete_current_layer(self):
        self.delete_layer(self.settings["current_layer_index"], None)

    def get_image_from_current_layer(self):
        layer = self.current_layer()
        return self.get_image_from_layer(layer)

    def get_image_from_layer(self, layer):
        if layer["base_64_image"]:
            decoded_image = base64.b64decode(layer["base_64_image"])
            bytes_image = io.BytesIO(decoded_image)
            # convert bytes to PIL iamge:
            image = Image.open(bytes_image)
            image = image.convert("RGBA")
            return image
        return None

    def add_image_to_current_layer(self, value):
        self.add_image_to_layer(self.settings["current_layer_index"], value)

    def add_image_to_layer(self, layer_index, value):
        if value:
            buffered = io.BytesIO()
            value.save(buffered, format="PNG")
            base_64_image = base64.b64encode(buffered.getvalue())
        else:
            base_64_image = ""
        
        settings = self.settings
        settings["layers"][layer_index]["base_64_image"] = base_64_image
        self.settings = settings