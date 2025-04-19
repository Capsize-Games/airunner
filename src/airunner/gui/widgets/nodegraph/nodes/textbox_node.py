from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.textedit_node import (
    TextEditNode,
)

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class TextboxNode(BaseWorkflowNode):
    NODE_NAME = "Textbox"

    def __init__(self):
        super().__init__()
        self.text_box = None
        self.in_prompt_port = self.add_input("prompt")
        self.out_prompt_port = self.add_output("prompt")
        self.add_multiline_textbox("prompt", "Prompt", tab="settings")

    def execute(self, input_data):
        prompt = self.get_property("prompt")
        # Using proper way to pass data between nodes by returning a dictionary
        return {"prompt": prompt}

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
        # Handle the text change event
        in_connections = self.in_prompt_port.connected_ports()
        if len(in_connections) > 0:
            text = (
                in_connections[0].node().get_property(in_connections[0].name())
            )
            self.text_box.blockSignals(True)
            self.text_box.set_value(text)
            self.text_box.blockSignals(False)
        self.set_property(name, text)
        for port in self.out_prompt_port.connected_ports():
            # set it into the downstream node
            port.node().set_property(port.name(), text)
