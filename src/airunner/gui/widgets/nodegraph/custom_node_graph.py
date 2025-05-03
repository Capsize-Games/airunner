from NodeGraphQt import (
    NodeGraph,
    PropertiesBinWidget,
)
from PySide6.QtCore import Qt


from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.widgets.nodegraph.nodes.core.variable_getter_node import (
    VariableGetterNode,
)

# Define the MIME type constant
VARIABLE_MIME_TYPE = "application/x-airunner-variable"


class CustomNodeGraph(MediatorMixin, SettingsMixin, NodeGraph):
    """Custom NodeGraph class to handle specific events like variable drops."""

    widget_ref = None

    def __init__(self, parent=None):
        super(CustomNodeGraph, self).__init__(parent)
        self._prop_bin = PropertiesBinWidget(node_graph=self)
        self._prop_bin.setWindowFlags(Qt.WindowType.Tool)
        self.node_double_clicked.connect(self.display_prop_bin)
        self.port_connected.connect(self._on_port_connected)
        self.viewer().setAcceptDrops(True)

    def display_prop_bin(self, node):
        """
        function for displaying the properties bin when a node
        is double clicked
        """
        if not self._prop_bin.isVisible():
            self._prop_bin.show()

    def _on_port_connected(self, in_port, out_port):
        """
        Handle connections between ports by transferring values.
        This is particularly important for variable nodes to transfer their values.
        """
        # Check if the output port is from a VariableGetterNode
        if isinstance(out_port.node(), VariableGetterNode):
            var_node = out_port.node()
            # Get the variable value
            variable = None
            if (
                hasattr(self, "widget_ref")
                and self.widget_ref
                and hasattr(var_node, "variable_name")
            ):
                variable = self.widget_ref._find_variable_by_name(
                    var_node.variable_name
                )

            if variable:
                value = variable.get_value()
                target_node = in_port.node()
                port_name = in_port.name()

                # Set the value on the target node if it has the corresponding property
                if target_node.has_property(port_name):
                    target_node.set_property(port_name, value)
                    if hasattr(self, "widget_ref") and self.widget_ref:
                        self.logger.info(
                            f"Set property '{port_name}' on node '{target_node.name()}' to value '{value}' from variable '{var_node.variable_name}'"
                        )

                    # If the target node has an update method, call it
                    if hasattr(target_node, "update") and callable(
                        getattr(target_node, "update")
                    ):
                        target_node.update()

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
                            self.logger.info(
                                f"Created Getter node for variable: {variable.name} at {pos.x()},{pos.y()}"
                            )
                        else:
                            self.logger.error(
                                f"Failed to create node with identifier: {node_identifier}"
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Error creating VariableGetterNode: {e}",
                            exc_info=True,
                        )

                else:
                    if self.widget_ref:
                        self.logger.warning(
                            f"Dropped variable '{variable_name}' not found."
                        )
            else:
                print(
                    "Error: Cannot access variable list from graph (widget_ref missing or invalid)."
                )

        else:
            # Important: Pass unhandled events to the base class for default node dropping etc.
            super().dropEvent(event)
