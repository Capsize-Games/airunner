from NodeGraphQt import BaseNode

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class BaseWorkflowNode(
    MediatorMixin,
    SettingsMixin,
    BaseNode,
):
    # Base identifier for easier registration and type checking
    __identifier__ = "airunner.workflow.nodes"

    def __init__(self):
        super().__init__()
        # Add common properties or methods if needed

    # Method to dynamically add an input port
    def add_dynamic_input(
        self, name="input", multi_input=False, display_name=True, color=None
    ):
        # Ensure port name is unique before adding
        if name not in self.inputs():
            return self.add_input(
                name,
                multi_input=multi_input,
                display_name=display_name,
                color=color,
            )
        return self.input(name)

    # Method to dynamically add an output port
    def add_dynamic_output(
        self, name="output", multi_output=True, display_name=True, color=None
    ):
        # Ensure port name is unique before adding
        if name not in self.outputs():
            return self.add_output(
                name,
                multi_output=multi_output,
                display_name=display_name,
                color=color,
            )
        return self.output(name)

    # Placeholder for execution logic - subclasses should override
    def execute(self, input_data):
        print(
            f"Executing node {self.name()} - Base implementation does nothing."
        )
        # By default, pass input data through if an output exists
        if self.outputs():
            output_port_name = list(self.outputs().keys())[0]
            return {
                output_port_name: input_data
            }  # Return data keyed by output port name
        return {}
