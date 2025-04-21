from NodeGraphQt import (
    NodeGraph,
    PropertiesBinWidget,
)
from PySide6.QtCore import Qt, QMimeData, QPoint

from NodeGraphQt import NodeGraph, BaseNode
from NodeGraphQt.constants import ViewerEnum

from airunner.gui.widgets.nodegraph.nodes.variable_getter_node import (
    VariableGetterNode,
)


class CustomNodeGraph(NodeGraph):
    """Custom NodeGraph class to handle specific events like variable drops."""

    # Add a reference to the parent widget if needed for accessing variables
    widget_ref = None  # Set this from NodeGraphWidget.__init__

    def __init__(self, parent=None):
        super(CustomNodeGraph, self).__init__(parent)
        # properties bin widget.
        self._prop_bin = PropertiesBinWidget(node_graph=self)
        self._prop_bin.setWindowFlags(Qt.WindowType.Tool)
        # wire signal.
        self.node_double_clicked.connect(self.display_prop_bin)
        self.port_connected.connect(self._on_port_connected)
        # Connect the data_dropped signal from the base class
        self.data_dropped.connect(self._on_node_data_dropped)

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

    def _on_node_data_dropped(self, mime_data: QMimeData, pos: QPoint):
        """Handles drop events emitted by the base graph's data_dropped signal."""
        # Call the base class implementation to ensure default behavior is preserved
        super()._on_node_data_dropped(mime_data, pos)

        # Check if the dropped data is our custom variable type
        if mime_data.hasFormat(
            "application/x-airunner-variable"
        ):  # Use the same MIME type
            variable_name = (
                mime_data.data("application/x-airunner-variable")
                .data()
                .decode()
            )

            # Get the variable details (type) from the NodeGraphWidget
            if self.widget_ref and hasattr(
                self.widget_ref, "_find_variable_by_name"
            ):
                variable = self.widget_ref._find_variable_by_name(
                    variable_name
                )
                if variable:
                    # Create the VariableGetterNode at the drop position
                    # Use the position provided by the signal
                    getter_node: VariableGetterNode = self.create_node(
                        "airunner.variables.VariableGetterNode",  # Use the registered identifier
                        pos=[pos.x(), pos.y()],
                    )
                    if getter_node:
                        getter_node.set_variable(
                            variable.name, variable.var_type
                        )
                        print(
                            f"Created Getter node for variable: {variable.name}"
                        )
                        return  # Handled
                else:
                    print(
                        f"Error: Dropped variable '{variable_name}' not found."
                    )
                    return
            else:
                print("Error: Cannot access variable list from graph.")
                return

        # If not our variable type, the base class handles other drop types
        # or ignores them if not configured. No need for explicit handling here.
