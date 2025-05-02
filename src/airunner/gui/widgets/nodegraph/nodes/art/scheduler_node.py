from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.gui.widgets.nodegraph.nodes.art.scheduler_art_node_widget import SchedulerArtNodeWidget


class SchedulerNode(BaseArtNode):
    """
    Node for choosing a scheduler for Stable Diffusion models
    """

    NODE_NAME = "Scheduler Node"
    has_exec_in_port = False
    has_exec_out_port = False
    _input_ports = []
    _output_ports = [
        dict(name="scheduler", display_name="Scheduler"),
    ]
    _propertes = []
    _signal_handlers = {}
    widget_class_ = SchedulerArtNodeWidget

    # on export port connected
    def on_output_connected(self, out_port, in_port):
        in_port.set_data(self.widget._scheduler)
