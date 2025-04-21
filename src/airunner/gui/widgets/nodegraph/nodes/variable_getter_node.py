from typing import Dict, Type

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.gui.widgets.nodegraph.variable_types import (
    get_variable_color,
    VariableType,
)


class VariableGetterNode(BaseWorkflowNode):
    """
    A node that represents getting the value of a graph variable.
    It is created by dragging a variable from the Variables panel.
    """

    # Define a unique identifier for the node type
    __identifier__ = "airunner.variables"
    NODE_NAME = "Get Variable"  # Default name, will be updated

    # This node doesn't have execution pins
    has_exec_in_port: bool = False
    has_exec_out_port: bool = False

    def __init__(self):
        super().__init__()
        self.variable_name = ""  # Name of the variable this node represents
        self.variable_type = None  # VariableType enum member
        self.output_port = None  # Reference to the output port

        # We will add the output port dynamically in set_variable
        # self.add_output("value") # Placeholder, will be configured

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

        # Update the view
        self.update()

    def execute(self, input_data: Dict):
        """
        Execute the node to get the variable's value.

        Args:
            input_data (Dict): Input data dictionary (not used for this node)

        Returns:
            Dict: Output data containing the variable value
        """
        # The connection itself represents the data flow.
        # Let's return the default value for now if needed.
        # This requires access to the variable definition (e.g., via the graph)
        variable = self.graph.widget_ref._find_variable_by_name(
            self.variable_name
        )  # Access via widget ref
        if variable:
            return {"value": variable.default_value}  # Return default for now
        else:
            # Handle case where variable might have been deleted
            self.logger.warning(
                f"Variable '{self.variable_name}' not found for node {self.id}"
            )
            return {"value": None}

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
            from airunner.gui.widgets.nodegraph.variable_types import (
                get_variable_type_from_string,
            )

            var_type = get_variable_type_from_string(var_type_str)
            if var_type:
                self.set_variable(var_name, var_type)


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
