from typing import Dict, Type

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.core.base_core_node import (
    BaseCoreNode,
)
from airunner.gui.widgets.nodegraph.nodes.core.variable_types import (
    get_variable_color,
    VariableType,
)


class VariableGetterNode(BaseCoreNode):
    """
    A node that represents getting the value of a graph variable.
    It is created by dragging a variable from the Variables panel.
    """

    # Define a unique identifier for the node type
    NODE_NAME = "Get Variable"  # Default name, will be updated

    # This node doesn't have execution pins
    has_exec_in_port: bool = False
    has_exec_out_port: bool = False

    def __init__(self):
        super().__init__()
        self.variable_name = ""  # Name of the variable this node represents
        self.variable_type = None  # VariableType enum member
        self.output_port = None  # Reference to the output port
        self.value_property_name = (
            "variable_value"  # Name for the value property
        )

        # Create a variable value property that will be displayed in the properties panel
        self.create_property(
            self.value_property_name,
            None,  # Initial value will be set in set_variable
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,  # Default widget type
        )

    def set_variable(self, name: str, var_type: VariableType):
        """
        Set the variable this node represents and configure the output port.

        Args:
            name (str): Name of the variable
            var_type (VariableType): Type of the variable
        """
        self.variable_name = name
        self.variable_type = var_type

        # Update the node name to match variable
        self.set_name(f"Get {name}")

        # Set node color to match the variable type color
        color = get_variable_color(var_type)
        if color:
            # Handle QColor object correctly
            self.set_color(color.red(), color.green(), color.blue())

        # Remove any existing output ports
        # Use safer approach to handle outputs() that might return a list or dict
        outputs = self.outputs()
        if isinstance(outputs, dict):
            for port in list(outputs.values()):
                self.delete_output(port.name())
        else:
            # If outputs() returns a list, iterate through the list directly
            for port in list(outputs):
                self.delete_output(port.name())

        # Create a new output port with the variable type
        # Fix: display_name should be True (boolean) and we'll set the actual name as a port attribute
        self.output_port = self.add_output("value", display_name=True)

        # Set the display name for the port
        if hasattr(self.view, "get_output_text") and callable(
            getattr(self.view, "get_output_text")
        ):
            output_text = self.view.get_output_text("value")
            if output_text:
                output_text.setPlainText(name)

        # Get the variable object to set up the property widget and initial value
        if self.graph and hasattr(self.graph, "widget_ref"):
            variable = self.graph.widget_ref._find_variable_by_name(name)
            if variable:
                self._setup_property_widget(variable)
                self.set_property(
                    self.value_property_name, variable.get_value()
                )

        # Update the view
        self.update()

    def _setup_property_widget(self, variable):
        """
        Set up the appropriate property widget based on the variable type.

        Args:
            variable: The variable object to set up the widget for
        """
        # Remove the existing property if it exists
        self.view.add_property = (
            lambda *args, **kwargs: None
        )  # Temporarily disable add_property
        self.view.properties.pop(self.value_property_name, None)
        self.view.add_property = self.__class__.view.add_property.__get__(
            self.view
        )  # Re-enable add_property

        # Set up the appropriate widget type based on variable type
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
        elif variable.var_type in [VariableType.FLOAT, VariableType.DOUBLE]:
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

    def update_variable_value(self):
        """Update the variable's value from the property widget."""
        if (
            self.graph
            and hasattr(self.graph, "widget_ref")
            and self.variable_name
        ):
            variable = self.graph.widget_ref._find_variable_by_name(
                self.variable_name
            )
            if variable:
                value = self.get_property(self.value_property_name)
                variable.set_value(value)

                # Update all other VariableGetterNodes for this variable
                for node in self.graph.all_nodes():
                    if (
                        isinstance(node, VariableGetterNode)
                        and node.variable_name == self.variable_name
                        and node != self
                    ):
                        node.set_property(node.value_property_name, value)

                return True
        return False

    def on_property_changed(self, prop_name):
        """Called when a property value has changed in the properties bin."""
        if prop_name == self.value_property_name:
            self.update_variable_value()

    def execute(self, input_data: Dict):
        """
        Execute the node to get the variable's value.

        Args:
            input_data (Dict): Input data dictionary (not used for this node)

        Returns:
            Dict: Output data containing the variable value
        """
        # The connection itself represents the data flow.
        # Get the current value from the variable
        variable = self.graph.widget_ref._find_variable_by_name(
            self.variable_name
        )  # Access via widget ref
        if variable:
            # First update our property to match the variable if needed
            current_value = self.get_property(self.value_property_name)
            var_value = variable.get_value()

            # Update property if values don't match
            if current_value != var_value:
                self.set_property(self.value_property_name, var_value)

            return {"value": var_value}  # Return the actual value
        else:
            # Handle case where variable might have been deleted
            self.logger.warning(
                f"Variable '{self.variable_name}' not found for node {self.id}"
            )
            return {"value": None}

    def draw(self, painter, option, widget):
        """Override to draw the variable's value on the node."""
        super().draw(painter, option, widget)

        # Add label to display the current value
        if hasattr(self, "view") and self.view:
            from PySide6.QtGui import QColor, QPen, QFont
            from PySide6.QtCore import Qt

            value = self.get_property(self.value_property_name)
            if value is not None:
                # Format the value for display
                if isinstance(value, bool):
                    value_text = "True" if value else "False"
                elif isinstance(value, (int, float)):
                    value_text = str(value)
                else:
                    # For strings and other types, limit length for display
                    value_text = str(value)
                    if len(value_text) > 10:
                        value_text = value_text[:10] + "..."

                # Create a rect for the value label
                rect = self.view.boundingRect()
                width = rect.width()
                height = rect.height()

                # Prepare painter
                painter.save()

                # Draw value text at the bottom of the node
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)

                # Draw with white text on a semi-transparent dark background
                painter.setPen(QPen(QColor(255, 255, 255)))
                text_rect = painter.fontMetrics().boundingRect(value_text)
                bg_rect = text_rect.adjusted(-5, -3, 5, 3)
                bg_rect.moveCenter(rect.center())
                bg_rect.moveBottom(height - 5)

                painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
                painter.drawText(bg_rect, Qt.AlignCenter, value_text)

                painter.restore()

    # Optional: Override methods for saving/loading if extra data needed
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
        var_name = custom_data.get("variable_name")
        var_type_str = custom_data.get("variable_type")

        if var_name and var_type_str:
            from airunner.gui.widgets.nodegraph.nodes.core.variable_types import (
                get_variable_type_from_string,
            )

            var_type = get_variable_type_from_string(var_type_str)
            if var_type:
                self.set_variable(var_name, var_type)

                # Set the value if it was serialized
                if "value" in custom_data:
                    self.set_property(
                        self.value_property_name, custom_data["value"]
                    )
                    self.update_variable_value()


# Variable node factory for dynamic node registration
def create_variable_getter_node_class(
    variable_name: str, variable_type: VariableType
) -> Type[VariableGetterNode]:
    """
    Factory function that creates a customized VariableGetterNode class for a specific variable.

    Args:
        variable_name: Name of the variable
        variable_type: Type of the variable

    Returns:
        A new VariableGetterNode subclass preconfigured for the variable
    """
    class_name = f"VariableGetter_{variable_name}"

    # Create a new class that inherits from VariableGetterNode
    var_node_class = type(
        class_name,
        (VariableGetterNode,),
        {
            "__identifier__": f"airunner.variables.{variable_name}",
            "NODE_NAME": f"Get {variable_name}",
        },
    )

    # Override the __init__ method to preconfigure the node for the variable
    original_init = var_node_class.__init__

    def new_init(self):
        original_init(self)
        self.set_variable(variable_name, variable_type)

    var_node_class.__init__ = new_init

    return var_node_class
