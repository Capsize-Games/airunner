from NodeGraphQt import (
    NodeGraph,
    PropertiesBinWidget,
    BaseNode,  # Added BaseNode import
)
from PySide6.QtCore import Qt, QMimeData, QPoint
from PySide6.QtWidgets import QApplication  # Added QApplication import

from NodeGraphQt.constants import ViewerEnum

from airunner.gui.widgets.nodegraph.nodes.variable_getter_node import (
    VariableGetterNode,
)

# Define the MIME type constant
VARIABLE_MIME_TYPE = "application/x-airunner-variable"


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
        # self.port_connected.connect(self._on_port_connected) # Keep commented if not needed
        # Remove the data_dropped connection as we'll handle drops via events
        # self.data_dropped.connect(self._on_node_data_dropped)

        # Enable drop events on the viewer widget
        self.viewer().setAcceptDrops(True)

    def display_prop_bin(self, node):
        """
        function for displaying the properties bin when a node
        is double clicked
        """
        if not self._prop_bin.isVisible():
            self._prop_bin.show()

    # Keep commented if not needed
    # def _on_port_connected(self, in_port, out_port):
    #     # grab the value from the upstream node
    #     val = out_port.node().get_property(out_port.name())
    #     # set it into the downstream node
    #     in_port.node().set_property(in_port.name(), val)

    # --- Drag and Drop Event Handling ---

    def dragEnterEvent(self, event):
        """Accept drag events if they contain our custom variable MIME type."""
        if event.mimeData().hasFormat(VARIABLE_MIME_TYPE):
            event.acceptProposedAction()
        else:
            # Important: Pass unhandled events to the base class
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Accept move events if they contain our custom variable MIME type."""
        if event.mimeData().hasFormat(VARIABLE_MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """Handle drop events for variables."""
        if event.mimeData().hasFormat(VARIABLE_MIME_TYPE):
            event.acceptProposedAction()

            variable_name = (
                event.mimeData().data(VARIABLE_MIME_TYPE).data().decode()
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
                    # Convert scene position to graph position if necessary (might not be needed)
                    pos = self.viewer().mapToScene(event.pos())

                    # Use the correct registered identifier for VariableGetterNode
                    # Assuming default registration based on class path
                    node_identifier = "airunner.gui.widgets.nodegraph.nodes.variable_getter_node.VariableGetterNode"

                    try:
                        getter_node: VariableGetterNode = self.create_node(
                            node_identifier,
                            pos=[pos.x(), pos.y()],
                        )
                        if getter_node:
                            getter_node.set_variable(
                                variable.name, variable.var_type
                            )
                            self.widget_ref.logger.info(  # Use logger from widget_ref
                                f"Created Getter node for variable: {variable.name} at {pos.x()},{pos.y()}"
                            )
                        else:
                            self.widget_ref.logger.error(  # Use logger from widget_ref
                                f"Failed to create node with identifier: {node_identifier}"
                            )
                    except Exception as e:
                        self.widget_ref.logger.error(  # Use logger from widget_ref
                            f"Error creating VariableGetterNode: {e}",
                            exc_info=True,
                        )

                else:
                    if self.widget_ref:
                        self.widget_ref.logger.warning(  # Use logger from widget_ref
                            f"Dropped variable '{variable_name}' not found."
                        )
            else:
                print(
                    "Error: Cannot access variable list from graph (widget_ref missing or invalid)."
                )  # Keep print for critical failure

        else:
            # Important: Pass unhandled events to the base class for default node dropping etc.
            super().dropEvent(event)

    # Removed _on_node_data_dropped as it's replaced by dropEvent override
    # def _on_node_data_dropped(self, mime_data: QMimeData, pos: QPoint):
    #     ...
