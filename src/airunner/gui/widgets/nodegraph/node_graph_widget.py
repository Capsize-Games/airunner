from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QLabel,
    QToolBar,
)

from airunner.gui.widgets.nodegraph.nodes.agent_action_node import (
    AgentActionNode,
)
from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.gui.widgets.nodegraph.nodes.image_generation_node import (
    ImageGenerationNode,
)
from airunner.gui.widgets.nodegraph.nodes.prompt_node import (
    PromptNode,
)
from airunner.gui.widgets.nodegraph.nodes.textbox_node import (
    TextboxNode,
)
from airunner.gui.widgets.nodegraph.nodes.random_number_node import (
    RandomNumberNode,
)
from airunner.gui.widgets.nodegraph.add_port_dialog import (
    AddPortDialog,
)
from airunner.gui.widgets.nodegraph.custom_node_graph import (
    CustomNodeGraph,
)


class NodeGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        layout = QVBoxLayout(self)

        # Add toolbar with buttons
        toolbar = QToolBar()

        # Add node buttons
        add_agent_node_btn = QPushButton("Add Agent Action")
        add_agent_node_btn.clicked.connect(self.add_agent_node)
        toolbar.addWidget(add_agent_node_btn)

        add_workflow_node_btn = QPushButton("Add Workflow")
        add_workflow_node_btn.clicked.connect(self.add_workflow_node)
        toolbar.addWidget(add_workflow_node_btn)

        add_image_node_btn = QPushButton("Add Image node")
        add_image_node_btn.clicked.connect(self.add_image_node)
        toolbar.addWidget(add_image_node_btn)

        add_prompt_node_btn = QPushButton("Add Prompt node")
        add_prompt_node_btn.clicked.connect(self.add_prompt_node)
        toolbar.addWidget(add_prompt_node_btn)

        add_textbox_node_btn = QPushButton("Add Textbox node")
        add_textbox_node_btn.clicked.connect(self.add_textbox_node)
        toolbar.addWidget(add_textbox_node_btn)

        add_random_number_node_btn = QPushButton("Add Random Number node")
        add_random_number_node_btn.clicked.connect(self.add_random_number_node)
        toolbar.addWidget(add_random_number_node_btn)

        toolbar.addSeparator()

        # Add workflow control buttons
        save_btn = QPushButton("Save Workflow")
        save_btn.clicked.connect(lambda: self.save_workflow("test_workflow"))
        toolbar.addWidget(save_btn)

        load_btn = QPushButton("Load Workflow")
        load_btn.clicked.connect(lambda: self.load_workflow("test_workflow"))
        toolbar.addWidget(load_btn)

        execute_btn = QPushButton("Execute Workflow")
        execute_btn.clicked.connect(self.execute_workflow)
        toolbar.addWidget(execute_btn)

        # Hint about right-click
        hint_label = QLabel("Right-click on nodes for more options")

        # Add toolbar to layout
        layout.addWidget(toolbar)
        layout.addWidget(hint_label)

        # Initialize the graph
        self.graph = CustomNodeGraph()

        # get the main context menu.
        def my_test(graph):
            selected_nodes = graph.selected_nodes()
            print("Number of nodes selected: {}".format(len(selected_nodes)))

        # Register node types
        self.graph.register_node(AgentActionNode)
        self.graph.register_node(BaseWorkflowNode)
        self.graph.register_node(ImageGenerationNode)
        self.graph.register_node(PromptNode)
        self.graph.register_node(TextboxNode)
        self.graph.register_node(RandomNumberNode)

        # define a test function.
        def test_func(graph, node):
            print("Clicked on node: {}".format(node.name()))

        context_menu = self.graph.get_context_menu("nodes")
        # context_menu.add_command(
        #     "Test",
        #     func=test_func,
        #     node_type="airunner.workflow.nodes.AgentActionNode",
        # )
        # Check if the context menu is for a node and if it's one of our custom nodes
        # Add rename option
        context_menu.add_command(
            "Rename Node",
            func=lambda g, n: self.rename_node_action(n),
            node_type="airunner.workflow.nodes.AgentActionNode",
        )

        # Add port actions
        context_menu.add_separator()
        context_menu.add_command(
            "Add Input Port",
            func=lambda g, n: self.add_input_port_action(n),
            node_type="airunner.workflow.nodes.AgentActionNode",
        )
        context_menu.add_command(
            "Add Output Port",
            func=lambda g, n: self.add_output_port_action(n),
            node_type="airunner.workflow.nodes.AgentActionNode",
        )
        context_menu.add_separator()
        context_menu.add_command(
            "Delete Node",
            func=lambda g, n: self.delete_node_action(n),
            node_type="airunner.workflow.nodes.AgentActionNode",
        )
        context_menu.add_command(
            "Delete Node",
            func=lambda g, n: self.delete_node_action(n),
            node_type="airunner.workflow.nodes.BaseWorkflowNode",
        )

        # Get the viewer
        self.viewer = self.graph.widget

        # Connect to the context menu prompt signal to add custom actions
        # context_menu.connect(self.on_context_menu)

        # Add the viewer to layout
        layout.addWidget(self.viewer)

        # Add layout to the widget
        self.setLayout(layout)

        # # Example node creation
        # node1 = self.graph.create_node(
        #     "airunner.workflow.nodes.AgentActionNode",
        #     name="Analyze Convo Action",
        #     pos=[100, 100],
        # )
        # node1.set_property("action_name", "AnalyzeConversation")

        # node2 = self.graph.create_node(
        #     "airunner.workflow.nodes.AgentActionNode",
        #     name="Update Mood Action",
        #     pos=[400, 100],
        # )
        # node2.set_property("action_name", "UpdateMood")

        # # Connect nodes - correct way to connect output to input
        # if node1.outputs() and node2.inputs():
        #     output_port = list(node1.outputs().values())[0]
        #     input_port = list(node2.inputs().values())[0]
        #     output_port.connect_to(input_port)

        # # Example Workflow Node
        # workflow_node = self.graph.create_node(
        #     "airunner.workflow.nodes.WorkflowNode",
        #     name="Sub Workflow",
        #     pos=[100, 300],
        # )
        # workflow_node.set_property(
        #     "nested_workflow_id", "mood_update_sub_flow"
        # )

    def add_agent_node(self):
        """Add a new agent action node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.AgentActionNode", name="New Agent Action"
        )  # Ensure closing parenthesis is present
        # Position the new node in view
        self.graph.center_on([node])
        return node

    def add_workflow_node(self):
        """Add a new workflow node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.BaseWorkflowNode", name="New Workflow"
        )  # Ensure closing parenthesis is present
        # Position the new node in view
        self.graph.center_on([node])
        return node

    def add_image_node(self):
        """Add a new image generation node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.ImageGenerationNode",
            name="New Image Generation Node",
        )
        self.graph.center_on([node])
        return node

    def add_prompt_node(self):
        """Add a new prompt node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.PromptNode", name="New Prompt Node"
        )
        self.graph.center_on([node])
        return node

    def add_textbox_node(self):
        """Add a new textbox node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.TextboxNode", name="New Textbox Node"
        )
        self.graph.center_on([node])
        return node

    def add_random_number_node(self):
        """Add a new random number node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.RandomNumberNode",
            name="RND",
        )
        self.graph.center_on([node])
        return node

    def rename_node_action(self, node):
        """Show dialog to rename a node."""
        # Only act on our custom node types if needed (optional check)
        if not isinstance(node, BaseWorkflowNode):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Rename Node")
        layout = QFormLayout(dialog)

        name_input = QLineEdit(node.name(), dialog)
        layout.addRow("Node Name:", name_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            new_name = name_input.text().strip()
            if new_name:
                node.set_name(new_name)

    def add_input_port_action(self, node):
        """Adds a dynamic input port to the node."""
        if not isinstance(node, BaseWorkflowNode):
            return

        dialog = AddPortDialog(self)
        if dialog.exec():
            port_name, port_type = dialog.get_port_info()
            if port_name:
                node.add_dynamic_input(port_name)
                # TODO: Update node properties in DB model if saving is implemented

    def add_output_port_action(self, node):
        """Adds a dynamic output port to the node."""
        if not isinstance(node, BaseWorkflowNode):
            return

        dialog = AddPortDialog(self)
        if dialog.exec():
            port_name, port_type = dialog.get_port_info()
            if port_name:
                node.add_dynamic_output(port_name)
                # TODO: Update node properties in DB model if saving is implemented

    def delete_node_action(self, node):
        """Deletes the selected node from the graph."""
        if not isinstance(node, BaseWorkflowNode):
            return
        self.graph.delete_node(node)

    # --- Database Interaction Placeholders ---
    def save_workflow(self, name, description=""):
        print(f"Placeholder: Save workflow '{name}'")

    def load_workflow(self, workflow_id_or_name):
        print(f"Placeholder: Load workflow '{workflow_id_or_name}'")

    # --- End Database Interaction Placeholders ---

    def execute_workflow(self, initial_input_data=None):
        if initial_input_data is None:
            initial_input_data = {
                "start_data": "Initial Data"
            }  # Example initial data structure

        executed_order = []
        node_outputs = (
            {}
        )  # Store outputs of executed nodes {node_id: {port_name: data}}

        # Topological sort (simple version for DAGs)
        nodes_to_process = self.graph.all_nodes()
        execution_queue = []
        node_dependencies = {node.id: 0 for node in nodes_to_process}
        node_successors = {node.id: [] for node in nodes_to_process}
        node_map = {node.id: node for node in nodes_to_process}

        # Build dependency graph
        for node in nodes_to_process:
            for port in node.inputs().values():
                for connected_port in port.connected_ports():
                    source_node_id = connected_port.node().id
                    node_dependencies[node.id] += 1
                    node_successors[source_node_id].append(node.id)

        # Initialize queue with nodes having no dependencies (inputs not connected within the graph)
        for node_id, dep_count in node_dependencies.items():
            if dep_count == 0:
                execution_queue.append(node_id)

        # Process nodes in topological order
        while execution_queue:
            node_id = execution_queue.pop(0)
            current_node = node_map[node_id]
            executed_order.append(current_node.name())

            # Prepare input data for the current node
            current_input_data = {}
            for port_name, port in current_node.inputs().items():
                connected_ports = port.connected_ports()
                if connected_ports:
                    # Assuming single connection per input for simplicity here
                    source_port = connected_ports[0]
                    source_node_id = source_port.node().id
                    source_port_name = source_port.name()
                    if (
                        source_node_id in node_outputs
                        and source_port_name in node_outputs[source_node_id]
                    ):
                        current_input_data[port_name] = node_outputs[
                            source_node_id
                        ][source_port_name]
                    else:
                        # Input connected, but source hasn't run or didn't produce required output
                        print(
                            f"Warning: Input '{port_name}' on node '{current_node.name()}' missing data from source '{source_port.node().name()}.{source_port_name}'."
                        )
                        current_input_data[port_name] = None
                elif (
                    node_dependencies[node_id] == 0
                ):  # Root node, provide initial data if port matches
                    if port_name in initial_input_data:
                        current_input_data[port_name] = initial_input_data[
                            port_name
                        ]

            # Execute the node
            if hasattr(current_node, "execute") and callable(
                getattr(current_node, "execute")
            ):
                try:
                    outputs = current_node.execute(current_input_data)
                    node_outputs[node_id] = outputs if outputs else {}
                    print(
                        f"Node '{current_node.name()}' executed. Output: {outputs}"
                    )
                except Exception as e:
                    print(f"Error executing node {current_node.name()}: {e}")
                    node_outputs[node_id] = {}  # Mark as failed or store error
            else:
                print(f"Node {current_node.name()} has no execute method.")
                node_outputs[node_id] = {}

            # Decrement dependency count for successors and add to queue if ready
            for successor_id in node_successors[node_id]:
                node_dependencies[successor_id] -= 1
                if node_dependencies[successor_id] == 0:
                    execution_queue.append(successor_id)

        print("Workflow execution finished.")
        print("Execution order:", executed_order)
        # Find final output (e.g., from nodes with no successors)
        final_outputs = {}
        for node_id, outputs in node_outputs.items():
            if not node_successors[
                node_id
            ]:  # Node has no outgoing connections within the graph
                final_outputs[node_map[node_id].name()] = outputs
        print("Final output(s):", final_outputs)
