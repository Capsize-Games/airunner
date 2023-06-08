from airunner.models.layerdata import LayerData


class CanvasLayerMixin:
    def initialize(self):
        self.layers = []
        self.add_layer()

    def toggle_layer_visibility(self, layer):
        layer.visible = not layer.visible
        self.update()

    def track_layer_move_history(self):
        layer_order = []
        for layer in self.layers:
            layer_order.append(layer.uuid)
        self.parent.history.add_event({
            "event": "move_layer",
            "layer_order": layer_order,
            "layer_index": self.current_layer_index
        })

    def move_layer_up(self, layer):
        index = self.layers.index(layer)
        if index == 0:
            return
        # track the current layer order
        self.track_layer_move_history()
        self.layers.remove(layer)
        self.layers.insert(index - 1, layer)
        self.current_layer_index = index - 1
        self.parent.show_layers()
        self.update()

    def move_layer_down(self, layer):
        index = self.layers.index(layer)
        if index == len(self.layers) - 1:
            return
        self.track_layer_move_history()
        self.layers.remove(layer)
        self.layers.insert(index + 1, layer)
        self.current_layer_index = index + 1
        self.parent.show_layers()
        self.update()

    def add_layer(self):
        self.parent.history.add_event({
            "event": "new_layer",
            "layers": self.get_layers_copy(),
            "layer_index": self.current_layer_index
        })
        layer_name = f"Layer {len(self.layers) + 1}"
        self.layers.insert(0, LayerData(len(self.layers), layer_name))
        self.parent.set_current_layer(0)

    def get_layers_copy(self):
        return [layer for layer in self.layers]

    def delete_layer(self, index):
        self.parent.history.add_event({
            "event": "delete_layer",
            "layers": self.get_layers_copy(),
            "layer_index": self.current_layer_index
        })

        if len(self.layers) == 1:
            self.layers = [LayerData(0, "Layer 1")]
        else:
            try:
                self.layers.pop(index)
            except IndexError:
                pass
        self.current_layer_index = 0
        self.parent.show_layers()
        self.update()
