from typing import Dict

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPen, QFont
from PySide6.QtCore import Qt

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.core.base_core_node import (
    BaseCoreNode,
)
from airunner.gui.widgets.nodegraph.nodes.core.variable_types import (
    get_variable_color,
    VariableType,
    get_variable_type_from_string,
)


class SetNode(BaseCoreNode):
    """
    A node that sets a variable to a new value.

    This node is generic and adapts to the type of variable connected to its input.
    - Connect a variable to the 'variable' input to select which variable to set
    - Connect a value to the 'value' input to determine what value to set
    - The output port passes the set value to the next node
    - When executed, the selected variable will be updated with the input value
    """

    NODE_NAME = "Set Variable"
    has_exec_in_port: bool = True
    has_exec_out_port: bool = True
    _input_ports = [
        {"name": "variable", "display_name": True},
        {"name": "value", "display_name": True},
    ]
    _output_ports = [
        {"name": "value", "display_name": True},
    ]
    _properties = [
        {
            "name": "variable_value",
            "value": None,
            "widget_type": NodePropWidgetEnum.QLINE_EDIT,
            "tab": "Variable",
        }
    ]

    def __init__(self):
        super().__init__()
        self.variable_name = ""
        self.variable_type = None
        self.variable_input_port = None
        self.value_input_port = None
        self.value_output_port = None
        self.value_property_name = "variable_value"
        if hasattr(self, "view"):
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
        self._set_neutral_state(skip_property_create=True)
        self._register_port_events()

    def _register_port_events(self):
        """Register for port connection/disconnection events."""
        if self.graph:
            self.logger.debug(f"Registering port events for SetNode {self.id}")
            try:
                if hasattr(self.graph, "connection_changed"):
                    connected_slots = self.graph.connection_changed.slots()
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

            self._check_existing_connection()

    def _check_existing_connection(self):
        """Check for any existing connections when node is created or loaded."""
        if not self.graph or not self.variable_input_port:
            return

        try:
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
        for port1, port2 in disconnected:
            if (
                port1 == self.variable_input_port
                or port2 == self.variable_input_port
            ):
                self.logger.debug(
                    "Variable input disconnected, resetting node"
                )
                self._set_neutral_state()
                return

        for port1, port2 in connected:
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

                if hasattr(connected_node, "variable_name") and hasattr(
                    connected_node, "variable_type"
                ):
                    self.logger.debug(
                        f"Variable detected: {connected_node.variable_name}"
                    )
                    self._on_variable_connected(connected_node)

    def _on_variable_connected(self, variable_node, variable):
        """Process a connection to a variable node.

        Args:
            variable_node: The node providing the variable information
            variable: The actual Variable object from the graph context
        """
        self.variable_name = variable_node.variable_name
        self.variable_type = variable_node.variable_type
        self.logger.debug(
            f"Setting up for variable: {self.variable_name} of type {self.variable_type}"
        )
        self.set_name(f"Set {self.variable_name}")
        color = get_variable_color(self.variable_type)
        if color:
            self.logger.debug(
                f"Setting color: r={color.red()}, g={color.green()}, b={color.blue()}"
            )
            self.set_color(color.red(), color.green(), color.blue())
        self._setup_property_widget(variable)
        self.set_property(self.value_property_name, variable.get_value())
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
            return {}

    def _set_neutral_state(self, skip_property_create=False):
        """Reset the node to its generic neutral state with no variable connected.

        Args:
            skip_property_create (bool): If True, skip creating the property (for initial setup)
        """
        self.variable_name = ""
        self.variable_type = None
        self.set_name("Set Variable")
        self.set_color(150, 150, 150)  # Neutral gray color
        if not skip_property_create:
            try:
                if hasattr(self, "view") and hasattr(self.view, "properties"):
                    if self.value_property_name in self.view.properties:
                        self.view.properties.pop(
                            self.value_property_name, None
                        )
                    props = self._get_properties()
                    if self.value_property_name not in props:
                        self.create_property(
                            self.value_property_name,
                            None,
                            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
                        )
            except Exception as e:
                self.logger.error(f"Error resetting property: {e}")
        self.update()

    def _setup_property_widget(self, variable):
        """
        Set up the appropriate property widget based on the variable type.
        Uses QTimer.singleShot to defer creation after deletion.

        Args:
            variable: The variable object to set up the widget for
        """
        try:
            if self.has_property(self.value_property_name):
                self.logger.debug(
                    f"Property '{self.value_property_name}' exists, deleting."
                )
                self.delete_property(self.value_property_name)
                QTimer.singleShot(
                    0, lambda: self._create_property_for_variable(variable)
                )
            else:
                self.logger.debug(
                    f"Property '{self.value_property_name}' does not exist, creating directly."
                )
                self._create_property_for_variable(variable)

        except Exception as e:
            self.logger.error(f"Error in _setup_property_widget: {e}")

    def _create_property_for_variable(self, variable):
        """Creates the property based on the variable type."""
        try:
            self.logger.debug(
                f"Creating property '{self.value_property_name}' for type {variable.var_type}"
            )
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
            self.logger.error(f"Error in _create_property_for_variable: {e}")

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
                variable.set_value(value)
                self.set_property(self.value_property_name, value)
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
            Dict: Output data containing the variable value that was set or the current value.
        """
        if not self.variable_name:
            self.logger.warning("Set Variable node has no variable connected")
            return {}

        input_value = input_data.get("value")
        value_to_output = None
        if input_value is not None:
            self.update_variable_value(input_value)
            value_to_output = input_value
        else:
            value_to_output = self.get_property(self.value_property_name)
        return {"value": value_to_output}

    def draw(self, painter, option, widget):
        """Override to draw the variable name and current value on the node."""
        super().draw(painter, option, widget)

        if hasattr(self, "view"):
            # Create a rect for the label
            rect = self.view.boundingRect()
            width = rect.width()
            height = rect.height()

            painter.save()
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 255, 255)))

            if self.variable_name:
                var_text = f"Variable: {self.variable_name}"
                text_rect = painter.fontMetrics().boundingRect(var_text)
                bg_rect = text_rect.adjusted(-5, -3, 5, 3)
                bg_rect.moveCenter(rect.center())
                bg_rect.moveTop(5)  # Place at top of node
                painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
                painter.drawText(bg_rect, Qt.AlignCenter, var_text)
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
        self.variable_name = custom_data.get("variable_name", "")
        var_type_str = custom_data.get("variable_type")
        if var_type_str:
            self.variable_type = get_variable_type_from_string(var_type_str)
        if "value" in custom_data:
            self.set_property(self.value_property_name, custom_data["value"])
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
        super().on_input_connected(in_port, out_port)
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
        if in_port == self.variable_input_port:
            self.logger.debug("Variable input disconnected via callback")
            self._set_neutral_state()
