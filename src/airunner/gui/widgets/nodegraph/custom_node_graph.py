from NodeGraphQt import (
    NodeGraph,
    PropertiesBinWidget,
)
from PySide6.QtCore import Qt


class CustomNodeGraph(NodeGraph):
    def __init__(self, parent=None):
        super(CustomNodeGraph, self).__init__(parent)
        # properties bin widget.
        self._prop_bin = PropertiesBinWidget(node_graph=self)
        self._prop_bin.setWindowFlags(Qt.WindowType.Tool)
        # wire signal.
        self.node_double_clicked.connect(self.display_prop_bin)
        self.port_connected.connect(self._on_port_connected)

    def display_prop_bin(self, node):
        """
        function for displaying the properties bin when a node
        is double clicked
        """
        if not self._prop_bin.isVisible():
            self._prop_bin.show()

    def _on_port_connected(self, in_port, out_port):
        # grab the value from the upstream node
        val = out_port.node().get_property(out_port.name())
        # set it into the downstream node
        in_port.node().set_property(in_port.name(), val)
