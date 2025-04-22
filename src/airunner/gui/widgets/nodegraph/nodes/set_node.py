from typing import Dict

# Import QTimer
from PySide6.QtCore import QTimer

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.gui.widgets.nodegraph.variable_types import (
    get_variable_color,
    VariableType,
)


class SetNode(BaseWorkflowNode):
    """
    A node that sets a variable to a new value.

    This node is generic and adapts to the type of variable connected to its input.
    - Connect a variable to the 'variable' input to select which variable to set
    - Connect a value to the 'value' input to determine what value to set
    - The output port passes the set value to the next node
    - When executed, the selected variable will be updated with the input value
    """

    # Define a unique identifier for the node type
    __identifier__ = "airunner.variables"
    NODE_NAME = "Set Variable"

    # This node has execution pins for workflow control
    has_exec_in_port: bool = True
    has_exec_out_port: bool = True

    def __init__(self):
        super().__init__()

        # Track the connected variable
        self.variable_name = ""
        self.variable_type = None

        # Reference to our ports
        self.variable_input_port = None
        self.value_input_port = None
        self.value_output_port = None

        # Setup property for the current value
        self.value_property_name = "variable_value"
        self.create_property(
            self.value_property_name,
            None,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
        )

        # Create generic input ports
        self.variable_input_port = self.add_input(
            "variable", display_name=True
        )
        self.value_input_port = self.add_input("value", display_name=True)

        # Create generic output port
        self.value_output_port = self.add_output("value", display_name=True)

        # Set initial text on ports
        if hasattr(self, "view"):
            # Set input port texts
            if hasattr(self.view, "get_input_text") and callable(
                getattr(self.view, "get_input_text")
            ):
                var_text = self.view.get_input_text("variable")
                if var_text:
                    var_text.setPlainText("Variable")

                value_text = self.view.get_input_text("value")
                if value_text:
                    value_text.setPlainText("Value")

            # Set output port text
            if hasattr(self.view, "get_output_text") and callable(
                getattr(self.view, "get_output_text")
            ):
                out_text = self.view.get_output_text("value")
                if out_text:
                    out_text.setPlainText("Value")

        # Initialize in a neutral state - but without recreating the property
        self._set_neutral_state(skip_property_create=True)

        # Queue registration for port events
        self._register_port_events()

    def _register_port_events(self):
        """Register for port connection/disconnection events."""
        # We need to hook into the node graph's signals to capture connections/disconnections
        if self.graph:
            self.logger.debug(f"Registering port events for SetNode {self.id}")

            # Ensure we're not already connected to avoid duplicate connections
            try:
                if hasattr(self.graph, "connection_changed"):
                    connected_slots = self.graph.connection_changed.slots()
                    # Check if our method is already connected
                    if not any(
                        slot.__self__ is self
                        for slot in connected_slots
                        if hasattr(slot, "__self__")
                    ):
                        self.graph.connection_changed.connect(
                            self._on_connection_changed
                        )
                        self.logger.debug(
                            "Connected to connection_changed signal"
                        )
            except Exception as e:
                self.logger.debug(f"Error connecting to signals: {e}")

            # Check for existing connections
            self._check_existing_connection()

    def _check_existing_connection(self):
        """Check for any existing connections when node is created or loaded."""
        if not self.graph or not self.variable_input_port:
            return

        try:
            # Get connected nodes to our variable input port
            connected_ports = self.variable_input_port.connected_ports()
            if connected_ports:
                self.logger.debug(
                    f"Found existing connections: {len(connected_ports)}"
                )
                connected_port = connected_ports[0]
                connected_node = connected_port.node()

                # Check if connected to a variable getter node
                if hasattr(connected_node, "variable_name") and hasattr(
                    connected_node, "variable_type"
                ):
                    self.logger.debug(
                        f"Connected to variable: {connected_node.variable_name}"
                    )
                    self._on_variable_connected(connected_node)
        except Exception as e:
            self.logger.debug(f"Error checking existing connections: {e}")

    def _on_connection_changed(self, disconnected, connected):
        """Handle connection change events from the node graph.

        Args:
            disconnected (list): List of disconnected port pairs (port1, port2)
            connected (list): List of connected port pairs (port1, port2)
        """
        # Check disconnections
        for port1, port2 in disconnected:
            # If our variable input was disconnected, reset to neutral state
            if (
                port1 == self.variable_input_port
                or port2 == self.variable_input_port
            ):
                self.logger.debug(
                    "Variable input disconnected, resetting node"
                )
                self._set_neutral_state()
                return

        # Check connections
        for port1, port2 in connected:
            # Find which port is ours and which is the external one
            our_port = None
            other_port = None

            if port1.node() == self and port1.name() == "variable":
                our_port = port1
                other_port = port2
            elif port2.node() == self and port2.name() == "variable":
                our_port = port2
                other_port = port1

            if our_port and other_port:
                connected_node = other_port.node()
                self.logger.debug(
                    f"Connected to node: {connected_node.name()} of type {type(connected_node).__name__}"
                )

                # Check if connected to a variable getter node
                if hasattr(connected_node, "variable_name") and hasattr(
                    connected_node, "variable_type"
                ):
                    self.logger.debug(
                        f"Variable detected: {connected_node.variable_name}"
                    )
                    self._on_variable_connected(connected_node)

    def _on_variable_connected(
        self, variable_node, variable
    ):  # Added variable parameter
        """Process a connection to a variable node.

        Args:
            variable_node: The node providing the variable information
            variable: The actual Variable object from the graph context
        """
        # Extract variable information from the node
        self.variable_name = variable_node.variable_name
        self.variable_type = variable_node.variable_type

        self.logger.debug(
            f"Setting up for variable: {self.variable_name} of type {self.variable_type}"
        )

        # Update node appearance
        self.set_name(f"Set {self.variable_name}")

        # Set node color based on variable type
        color = get_variable_color(self.variable_type)
        if color:
            self.logger.debug(
                f"Setting color: r={color.red()}, g={color.green()}, b={color.blue()}"
            )
            self.set_color(color.red(), color.green(), color.blue())

        # Update the property widget using the passed variable object
        self._setup_property_widget(variable)
        # Set the property value using the actual variable's current value
        self.set_property(self.value_property_name, variable.get_value())

        # Update the view
        self.update()

    def _get_properties(self):
        """Helper method to get properties regardless of how they're stored.

        Returns:
            dict: Dictionary of properties
        """
        # Try different approaches to get properties
        if hasattr(self, "get_properties") and callable(self.get_properties):
            return self.get_properties()
        elif hasattr(self, "model") and hasattr(self.model, "properties"):
            return self.model.properties
        elif hasattr(self, "properties"):
            return self.properties
        elif hasattr(self, "view") and hasattr(self.view, "properties"):
            return self.view.properties
        else:
            # Return empty dict as fallback
            return {}

    def _set_neutral_state(self, skip_property_create=False):
        """Reset the node to its generic neutral state with no variable connected.

        Args:
            skip_property_create (bool): If True, skip creating the property (for initial setup)
        """
        self.variable_name = ""
        self.variable_type = None

        # Reset node appearance
        self.set_name("Set Variable")
        self.set_color(150, 150, 150)  # Neutral gray color

        # Reset our property to a generic type - only if not skipping
        if not skip_property_create:
            try:
                if hasattr(self, "view") and hasattr(self.view, "properties"):
                    # Remove existing property if it exists
                    if self.value_property_name in self.view.properties:
                        self.view.properties.pop(
                            self.value_property_name, None
                        )

                    # Only create if it doesn't exist (avoid duplication)
                    props = self._get_properties()
                    if self.value_property_name not in props:
                        self.create_property(
                            self.value_property_name,
                            None,
                            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
                        )
            except Exception as e:
                self.logger.error(f"Error resetting property: {e}")

        # Update the view
        self.update()

    def _setup_property_widget(self, variable):
        """
        Set up the appropriate property widget based on the variable type.
        Uses QTimer.singleShot to defer creation after deletion.

        Args:
            variable: The variable object to set up the widget for
        """
        try:
            # Check if the property exists using the node's own method
            if self.has_property(self.value_property_name):
                self.logger.debug(
                    f"Property '{self.value_property_name}' exists, deleting."
                )
                # Use the built-in delete_property method
                self.delete_property(self.value_property_name)
                # Defer the creation to the next event loop cycle
                QTimer.singleShot(
                    0, lambda: self._create_property_for_variable(variable)
                )
            else:
                self.logger.debug(
                    f"Property '{self.value_property_name}' does not exist, creating directly."
                )
                # If it doesn't exist, create it immediately
                self._create_property_for_variable(variable)

        except Exception as e:
            # Log error if property setup fails
            if hasattr(self, "logger"):
                import traceback

                self.logger.error(
                    f"Error in _setup_property_widget: {e}\n{traceback.format_exc()}"
                )

    def _create_property_for_variable(self, variable):
        """Creates the property based on the variable type."""
        try:
            self.logger.debug(
                f"Creating property '{self.value_property_name}' for type {variable.var_type}"
            )
            # Now create the new property based on the variable type
            if variable.var_type == VariableType.BOOLEAN:
                self.create_property(
                    self.value_property_name,
                    variable.get_value() or False,
                    widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
                    tab="Variable",
                )
            elif variable.var_type in [
                VariableType.BYTE,
                VariableType.INTEGER,
                VariableType.INTEGER64,
            ]:
                self.create_property(
                    self.value_property_name,
                    variable.get_value() or 0,
                    widget_type=NodePropWidgetEnum.INT.value,
                    tab="Variable",
                )
            elif variable.var_type in [
                VariableType.FLOAT,
                VariableType.DOUBLE,
            ]:
                self.create_property(
                    self.value_property_name,
                    variable.get_value() or 0.0,
                    widget_type=NodePropWidgetEnum.FLOAT.value,
                    tab="Variable",
                )
            else:  # Default to text input for other types
                self.create_property(
                    self.value_property_name,
                    variable.get_value() or "",
                    widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
                    tab="Variable",
                )
            self.logger.debug(
                f"Successfully created property: {self.value_property_name}"
            )
            # Explicitly update the view after property creation if needed
            self.update()

        except Exception as e:
            # Log error if property creation fails
            if hasattr(self, "logger"):
                import traceback

                self.logger.error(
                    f"Error in _create_property_for_variable: {e}\n{traceback.format_exc()}"
                )

    def on_property_changed(self, prop_name):
        """Called when a property value has changed in the properties bin."""
        if prop_name == self.value_property_name and self.variable_name:
            self.update_variable_value(
                self.get_property(self.value_property_name)
            )

    def update_variable_value(self, value):
        """
        Update the variable's value with the provided value.

        Args:
            value: The new value for the variable

        Returns:
            bool: Whether the update was successful
        """
        if not self.variable_name:
            return False

        if self.graph and hasattr(self.graph, "widget_ref"):
            variable = self.graph.widget_ref._find_variable_by_name(
                self.variable_name
            )
            if variable:
                # Update the variable's value
                variable.set_value(value)

                # Update the property to reflect the new value
                self.set_property(self.value_property_name, value)

                # Update all VariableGetterNodes for this variable
                for node in self.graph.all_nodes():
                    if (
                        hasattr(node, "variable_name")
                        and node.variable_name == self.variable_name
                        and node != self
                        and hasattr(node, "value_property_name")
                    ):
                        node.set_property(node.value_property_name, value)

                return True
        return False

    def execute(self, input_data: Dict) -> Dict:
        """
        Execute the node to set the variable's value.

        Args:
            input_data (Dict): Input data dictionary containing the new value

        Returns:
            Dict: Output data containing the variable value
        """
        # If no variable is connected, do nothing
        if not self.variable_name:
            self.logger.warning("Set Variable node has no variable connected")
            return {}

        # Get input value from the 'value' input
        input_value = input_data.get("value")

        # Also check for a value from the variable input (fallback mechanism)
        if input_value is None and "variable" in input_data:
            var_data = input_data.get("variable")
            # If the variable data has a value field, use that
            if isinstance(var_data, dict) and "value" in var_data:
                input_value = var_data["value"]

        # Only update if we have a value
        if input_value is not None:
            self.update_variable_value(input_value)

        # Return the current value to pass through to the next node
        return {"value": self.get_property(self.value_property_name)}

    def draw(self, painter, option, widget):
        """Override to draw the variable name and current value on the node."""
        super().draw(painter, option, widget)

        # Add dynamic text showing which variable is being set
        if hasattr(self, "view"):
            from PySide6.QtGui import QColor, QPen, QFont
            from PySide6.QtCore import Qt

            # Create a rect for the label
            rect = self.view.boundingRect()
            width = rect.width()
            height = rect.height()

            # Prepare painter
            painter.save()
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 255, 255)))

            # Draw variable name if we have one
            if self.variable_name:
                # Draw with the variable name
                var_text = f"Variable: {self.variable_name}"
                text_rect = painter.fontMetrics().boundingRect(var_text)
                bg_rect = text_rect.adjusted(-5, -3, 5, 3)
                bg_rect.moveCenter(rect.center())
                bg_rect.moveTop(5)  # Place at top of node

                painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
                painter.drawText(bg_rect, Qt.AlignCenter, var_text)

                # Add value display at bottom
                value = self.get_property(self.value_property_name)
                if value is not None:
                    # Format value for display
                    if isinstance(value, bool):
                        value_text = "True" if value else "False"
                    elif isinstance(value, (int, float)):
                        value_text = str(value)
                    else:
                        value_text = str(value)
                        if len(value_text) > 10:
                            value_text = value_text[:10] + "..."

                    text_rect = painter.fontMetrics().boundingRect(value_text)
                    bg_rect = text_rect.adjusted(-5, -3, 5, 3)
                    bg_rect.moveCenter(rect.center())
                    bg_rect.moveBottom(height - 5)  # Place at bottom

                    painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
                    painter.drawText(bg_rect, Qt.AlignCenter, value_text)
            else:
                # Draw a hint message when no variable is connected
                hint_text = "Connect to a variable"
                text_rect = painter.fontMetrics().boundingRect(hint_text)
                bg_rect = text_rect.adjusted(-5, -3, 5, 3)
                bg_rect.moveCenter(rect.center())

                painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
                painter.drawText(bg_rect, Qt.AlignCenter, hint_text)

            painter.restore()

    # Methods for saving/loading node data
    def serialize(self):
        """
        Serialize this node to include variable data.

        Returns:
            dict: serialized node data
        """
        data = super().serialize()
        data["custom"] = {
            "variable_name": self.variable_name,
            "variable_type": (
                self.variable_type.value if self.variable_type else None
            ),
            "value": self.get_property(self.value_property_name),
        }
        return data

    def deserialize(self, data, hash_missing=False):
        """
        Deserialize the node and restore variable data.

        Args:
            data (dict): serialized node data
            hash_missing (bool): optional flag
        """
        super().deserialize(data, hash_missing)
        custom_data = data.get("custom", {})

        # Store variable data for when connections are restored
        self.variable_name = custom_data.get("variable_name", "")
        var_type_str = custom_data.get("variable_type")

        if var_type_str:
            from airunner.gui.widgets.nodegraph.variable_types import (
                get_variable_type_from_string,
            )

            self.variable_type = get_variable_type_from_string(var_type_str)

        # Set the value if it was serialized
        if "value" in custom_data:
            self.set_property(self.value_property_name, custom_data["value"])

        # Schedule a check for existing connections after node construction is complete
        if self.graph and hasattr(self.graph, "node_item_constructed"):
            self.graph.node_item_constructed.connect(
                lambda: self._check_existing_connection()
            )

    def on_input_connected(self, in_port, out_port):
        """Called when an input port is connected to an output port.
        This is a built-in method that may be called by the NodeGraph framework.

        Args:
            in_port: input port (our port).
            out_port: connected output port.
        """
        # Call super method first
        super().on_input_connected(in_port, out_port)

        # Handle connection to the variable input port
        if in_port == self.variable_input_port:
            connected_node = out_port.node()

            # Check if connected to a variable getter node
            if hasattr(connected_node, "variable_name") and hasattr(
                connected_node, "variable_type"
            ):
                self.logger.debug(
                    f"Input connected callback: Variable {connected_node.variable_name}"
                )
                # Find the actual variable object
                if self.graph and hasattr(self.graph, "widget_ref"):
                    variable = self.graph.widget_ref._find_variable_by_name(
                        connected_node.variable_name
                    )
                    if variable:
                        # Pass both the connected node and the actual variable object
                        self._on_variable_connected(
                            variable_node=connected_node, variable=variable
                        )
                    else:
                        self.logger.warning(
                            f"Variable '{connected_node.variable_name}' not found in graph context."
                        )
                else:
                    self.logger.warning(
                        "Graph or widget_ref not available to find variable."
                    )

    def on_input_disconnected(self, in_port, out_port):
        """Called when an input port has been disconnected.
        This is a built-in method that may be called by the NodeGraph framework.

        Args:
            in_port: input port (our port).
            out_port: disconnected output port.
        """
        super().on_input_disconnected(in_port, out_port)

        # Reset state if variable port disconnected
        if in_port == self.variable_input_port:
            self.logger.debug("Variable input disconnected via callback")
            self._set_neutral_state()
