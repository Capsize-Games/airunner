from NodeGraphQt.constants import NodePropWidgetEnum
from airunner.gui.widgets.nodegraph.nodes.textedit_node import (
    TextEditNode,
)

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)


class PromptNode(BaseWorkflowNode):
    NODE_NAME = "Prompt"

    def __init__(self):
        super().__init__()
        self.text_box = None
        self.ports = {
            "in": {
                "prompt": self.add_input("prompt"),
                "prompt_2": self.add_input("prompt_2"),
                "negative_prompt": self.add_input("negative_prompt"),
                "negative_prompt_2": self.add_input("negative_prompt_2"),
            },
            "out": {
                "prompt_data": self.add_output("prompt_data"),
            },
        }
        self.add_multiline_textbox("prompt", "Prompt", tab="settings")
        self.add_multiline_textbox("prompt_2", "Prompt 2", tab="settings")
        self.add_multiline_textbox(
            "negative_prompt", "Negative Prompt", tab="settings"
        )
        self.add_multiline_textbox(
            "negative_prompt_2", "Negative Prompt 2", tab="settings"
        )

    def execute(self, input_data):
        # return {"image": img}
        pass

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
        in_connections = self.ports["in"]["prompt"].connected_ports()
        if len(in_connections) > 0:
            for in_conn in in_connections:
                if in_conn.name() == name:
                    text = in_conn.node().get_property(name)
                    break
            self.text_box.blockSignals(True)
            self.text_box.set_value(text)
            self.text_box.blockSignals(False)
        self.set_property(name, text)
        for port in self.ports["out"]["prompt_data"].connected_ports():
            # set it into the downstream node
            port.node().set_property(port.name(), text)

    def execute(self, input_data):
        prompt_data = {
            "prompt": self.get_property("prompt"),
            "prompt_2": self.get_property("prompt_2"),
            "negative_prompt": self.get_property("negative_prompt"),
            "negative_prompt_2": self.get_property("negative_prompt_2"),
        }
        self.out_prompt_data_port.set_data(prompt_data)
