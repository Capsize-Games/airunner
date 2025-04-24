from typing import Dict

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)


class LoraNode(BaseArtNode):
    """
    A node that outputs a Lora configuration as a dictionary.

    This node provides input ports for all Lora model parameters and outputs
    a dictionary with the Lora configuration.
    """

    NODE_NAME = "Lora"

    def __init__(self):
        super().__init__()

        # Add inputs for Lora parameters
        self.add_input("name", display_name=True)
        self.add_input("scale", display_name=True)
        self.add_input("enabled", display_name=True)
        self.add_input("loaded", display_name=True)
        self.add_input("trigger_word", display_name=True)
        self.add_input("path", display_name=True)
        self.add_input("version", display_name=True)

        # Add output port for the Lora dictionary
        self.add_output("lora_config")

        # String parameters
        self.create_property(
            "lora_name",
            "",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "trigger_word",
            "",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "path",
            "",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "version",
            "",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        # Integer parameters
        self.create_property(
            "scale",
            0,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 100),
            tab="basic",
        )

        # Boolean parameters
        self.create_property(
            "enabled",
            False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="basic",
        )

        self.create_property(
            "loaded",
            False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="basic",
        )

    def execute(self, input_data: Dict):
        """
        Execute the node to create and output a Lora configuration dictionary.

        Args:
            input_data: Dictionary containing input values from connected nodes.

        Returns:
            dict: A dictionary with the key 'lora_config' containing the Lora configuration.
        """
        # Get values from inputs or use defaults from widget properties
        lora_config = {
            "name": self._get_value(input_data, "name", str),
            "scale": self._get_value(input_data, "scale", int),
            "enabled": self._get_value(input_data, "enabled", bool),
            "loaded": self._get_value(input_data, "loaded", bool),
            "trigger_word": self._get_value(input_data, "trigger_word", str),
            "path": self._get_value(input_data, "path", str),
            "version": self._get_value(input_data, "version", str),
        }

        return {
            "lora_config": lora_config,
            "_exec_triggered": self.EXEC_OUT_PORT_NAME,
        }

    def _get_value(self, input_data, name, expected_type):
        """
        Get a value from input data or fall back to the node property.

        Args:
            input_data: Dictionary containing input values.
            name: Name of the parameter.
            expected_type: Type to convert the value to.

        Returns:
            The value converted to the expected type.
        """
        if name in input_data and input_data[name] is not None:
            value = input_data[name]
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            return value
        else:
            # Get from node property
            value = self.get_property(name)
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            return value
