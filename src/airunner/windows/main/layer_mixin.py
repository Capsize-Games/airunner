import base64
import io
import uuid

from PyQt6.QtGui import QPixmap

from PIL import Image

from airunner.enums import SignalCode, ServiceCode
from airunner.service_locator import ServiceLocator


class LayerMixin:
    def __init__(self):
        self.settings = None
        self.settings = None
        self.settings = None
        self.settings = None
        self.current_layer_index = None
        self.settings = None
        self.settings = None
        self.settings = None
        self.settings = None
        self.register(SignalCode.LAYER_SWITCH_SIGNAL, self.on_switch_layer_signal)
        self.register(SignalCode.LAYER_ADD_SIGNAL, self.on_add_layer_signal)
        self.register(SignalCode.LAYER_CREATE_SIGNAL, self.on_create_layer_signal)
        self.register(SignalCode.LAYER_UPDATE_CURRENT_SIGNAL, self.on_update_current_layer_signal)
        self.register(SignalCode.LAYER_UPDATE_SIGNAL, self.on_update_layer_signal)
        self.register(SignalCode.LAYER_DELETE_CURRENT_SIGNAL, self.on_delete_current_layer_signal)
        self.register(SignalCode.LAYER_DELETE_SIGNAL, self.on_delete_layer_signal)
        self.register(SignalCode.LAYER_MOVE_UP_SIGNAL, self.on_move_layer_up_signal)
        self.register(SignalCode.LAYER_MOVE_DOWN_SIGNAL, self.on_move_layer_down_signal)
        self.register(SignalCode.LAYER_CLEAR_LAYERS_SIGNAL, self.on_clear_layers_signal)
        self.register(SignalCode.LAYER_SET_CURRENT_SIGNAL, self.on_set_current_layer_signal)

        ServiceLocator.register(ServiceCode.CURRENT_LAYER, self.current_layer)
        ServiceLocator.register(ServiceCode.CURRENT_DRAGGABLE_PIXMAP, self.current_draggable_pixmap)
        ServiceLocator.register(ServiceCode.CURRENT_ACTIVE_IMAGE, self.current_active_image)
        ServiceLocator.register(ServiceCode.GET_IMAGE_FROM_LAYER, self.get_image_from_layer)

    def on_delete_layer_signal(self, data):
        layer = data.get("layer", None)
        index = data.get("index", None)
        self.delete_layer(index, layer)

    def on_delete_current_layer_signal(self, _ignore):
        self.delete_layer(self.settings["current_layer_index"], None)

    def on_update_layer_signal(self, data):
        self.update_layer_by_index(data)
    
    def on_create_layer_signal(self, _ignore):
        index = self.add_layer()
        self.switch_layer(index)
    
    def on_switch_layer_signal(self, index):
        self.switch_layer(index)

    def on_add_layer_signal(self, _ignore):
        self.add_layer()
    
    def on_update_current_layer_signal(self, data):
        current_layer_index = self.settings["current_layer_index"]
        settings = self.settings
        layer = settings["layers"][current_layer_index]
        for k, v in data.items():
            layer[k] = v
        settings["layers"][current_layer_index] = layer
        self.settings = settings

    def add_layer(self) -> int:
        settings = self.settings
        total_layers = len(self.settings['layers'])
        name=f"Layer {total_layers + 1}"
        settings["layers"].append({
            'name': name,
            'visible': True,
            'opacity': 100,
            'position': total_layers,
            'base_64_image': "",
            'pos_x': 0,
            'pos_y': 0,
            'pivot_point_x': 0,
            'pivot_point_y': 0,
            'root_point_x': 0,
            'root_point_y': 0,
            'uuid': str(uuid.uuid4()),
            'pixmap': QPixmap(),
        })
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
    
    def on_clear_layers_signal(self, _ignore):
        # delete all widgets from self.container.layout()
        layers = self.settings["layers"]
        # for index, layer in enumerate(layers):
        #     if not layer["layer_widget"]:
        #         continue
        #     layer["layer_widget"].deleteLater()
        self.add_layer()
        settings = self.settings
        settings["layers"] = layers
        self.settings = settings
        self.switch_layer(0)
    
    def on_set_current_layer_signal(self, index):
        self.logger.info(f"set_current_layer current_layer_index={index}")
        self.current_layer_index = index
        if not hasattr(self, "container"):
            return
        self.current_layer_index = index

    def on_move_layer_up_signal(self, _ignore):
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
    
    def on_move_layer_down_signal(self, _ignore):
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
    
    def current_active_image(self):
        return self.get_image_from_current_layer()

    def update_layer_by_index(self, data):
        index = data["index"]
        layer = data["layer"]
        settings = self.settings
        settings["layers"][index] = layer
        self.settings = settings

    def switch_layer(self, layer_index):
        settings = self.settings
        settings["current_layer_index"] = layer_index
        self.settings = settings

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
