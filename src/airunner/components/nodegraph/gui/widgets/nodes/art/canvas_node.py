from airunner.components.nodegraph.gui.widgets.nodes.art.base_art_node import (
    BaseArtNode,
)


class CanvasNode(BaseArtNode):
    NODE_NAME = "Canvas Node"
    _input_ports = [
        dict(name="image_response", display_name="Image Response"),
    ]
    _output_ports = [
        dict(name="image_response_out", display_name="Image Response Out"),
    ]

    def execute(self, input_data):
        image_response = self.get_input_data("image_response", input_data)
        self.api.art.canvas.send_image_to_canvas(image_response)

        return {
            "image_response_out": image_response,
        }
