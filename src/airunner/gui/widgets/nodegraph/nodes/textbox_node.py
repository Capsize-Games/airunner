from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.textedit_node import (
    TextEditNode,
)

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class TextboxNode(BaseWorkflowNode):
    NODE_NAME = "Textbox"
    has_exec_in_port: bool = False
    has_exec_out_port: bool = False

    def __init__(self):
        super().__init__()
        self.text_box = None
        self.in_prompt_port = self.add_input("prompt")
        self.out_prompt_port = self.add_output("prompt")
        self.add_multiline_textbox("prompt", "Prompt", tab="settings")

    def execute(self, input_data):
        # If input data is provided for the 'prompt' port, update the property and widget
        if "prompt" in input_data and input_data["prompt"] is not None:
            new_prompt = input_data["prompt"]
            # Use set_property to ensure widget updates too
            self.set_property("prompt", new_prompt)
        else:
            # Otherwise, get the current property value
            new_prompt = self.get_property("prompt")

        return {"prompt": new_prompt}

    def on_input_connected(self, in_port, out_port):
        """Called when an input port is connected to an output port."""
        super().on_input_connected(in_port, out_port)

        # When something connects to our prompt input, immediately request data from it
        if in_port == self.in_prompt_port:
            # Get the connected node
            connected_node = out_port.node()
            if connected_node:
                # Get the output data from the connected node
                out_data = connected_node.execute({})

                # If there's data in the expected format, update our textbox right away
                if (
                    "value" in out_data
                ):  # Variable node outputs use "value" key
                    self.set_property("prompt", out_data["value"])
                elif (
                    "prompt" in out_data
                ):  # Other nodes might use "prompt" key
                    self.set_property("prompt", out_data["prompt"])
            else:
                print("X" * 100)
                print("FAILED TO GET CONNECTED NODE")

    def add_multiline_textbox(
        self,
        name,
        label="",
        text="",
        placeholder_text="",
        tooltip=None,
        tab=None,
    ):
        self.create_property(
            name,
            value=text,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            widget_tooltip=tooltip,
            tab=tab,
        )
        self.text_box = TextEditNode(
            self.view, name, label, text, placeholder_text
        )
        self.text_box.setToolTip(tooltip or "")
        self.text_box.value_changed.connect(self.handle_text_change)
        self.view.add_widget(self.text_box)
        self.text_box.set_value(text)
        #: redraw node to address calls outside the "__init__" func.
        self.view.draw_node()

    def handle_text_change(self, name, text):
        # Triggered when the user edits the text_box widget.
        # Update the internal property with the new text from the widget.
        # Use blockSignals on the *widget* to prevent feedback loops.
        if self.text_box:
            self.text_box.blockSignals(True)
        self.set_property(
            name, text, push_undo=False
        )  # Update internal property silently first
        if self.text_box:
            self.text_box.blockSignals(False)

        # Propagation is handled by set_property or NodeGraphQt's mechanisms

    # Override set_property to update the widget when the property changes externally
    def set_property(self, name, value, push_undo=True):
        super().set_property(name, value, push_undo=push_undo)
        # If the 'prompt' property is updated, also update the text_box widget
        if name == "prompt" and self.text_box:
            # Block signals on the widget to prevent handle_text_change from firing unnecessarily
            self.text_box.blockSignals(True)
            self.text_box.set_value(str(value))  # Ensure value is string
            self.text_box.blockSignals(False)
