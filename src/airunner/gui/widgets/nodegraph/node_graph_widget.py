from NodeGraphQt import NodesPaletteWidget
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
    QSplitter,
)
from PySide6.QtCore import Qt

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
from airunner.gui.widgets.nodegraph.nodes.number_node import (
    NumberNode,
)
from airunner.gui.widgets.nodegraph.nodes.float_node import (
    FloatNode,
)
from airunner.gui.widgets.nodegraph.nodes.boolean_node import (
    BooleanNode,
)
from airunner.gui.widgets.nodegraph.nodes.llm_request_node import (
    LLMRequestNode,
)
from airunner.gui.widgets.nodegraph.nodes.image_request_node import (
    ImageRequestNode,
)
from airunner.gui.widgets.nodegraph.nodes.run_llm_node import (
    RunLLMNode,
)
from airunner.gui.widgets.nodegraph.nodes.image_display_node import (
    ImageDisplayNode,
)
from airunner.gui.widgets.nodegraph.nodes.start_node import StartNode  # Added
from airunner.gui.widgets.nodegraph.nodes.branch_node import (
    BranchNode,
)  # Added

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

        # Add workflow control buttons
        save_btn = QPushButton("Save Workflow")
        save_btn.clicked.connect(lambda: self.save_workflow("test_workflow"))
        toolbar.addWidget(save_btn)

        load_btn = QPushButton("Load Workflow")
        load_btn.clicked.connect(lambda: self.load_workflow("test_workflow"))
        toolbar.addWidget(load_btn)

        execute_btn = QPushButton("Execute Workflow")
        # Use a lambda to call execute_workflow without arguments
        execute_btn.clicked.connect(lambda: self.execute_workflow())
        toolbar.addWidget(execute_btn)

        # Hint about right-click
        hint_label = QLabel("Right-click on nodes for more options")
        hint_label.setFixedHeight(35)

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
        self.graph.register_node(NumberNode)
        self.graph.register_node(FloatNode)
        self.graph.register_node(BooleanNode)
        self.graph.register_node(LLMRequestNode)
        self.graph.register_node(ImageRequestNode)
        self.graph.register_node(RunLLMNode)
        self.graph.register_node(ImageDisplayNode)  # Register the new node
        self.graph.register_node(StartNode)  # Added
        self.graph.register_node(BranchNode)  # Added

        self.nodes_palette = NodesPaletteWidget(
            parent=None,
            node_graph=self.graph,
        )

        self.initialize_context_menu()

        # Get the viewer
        self.viewer = self.graph.widget

        # Create and configure the splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.viewer)
        splitter.addWidget(self.nodes_palette)

        # Set initial sizes - graph takes most of the space, palette gets 200px
        splitter.setSizes([700, 200])
        layout.addWidget(splitter)

        # Add layout to the widget
        self.setLayout(layout)

    def initialize_context_menu(self):
        context_menu = self.graph.get_context_menu("nodes")
        registered_nodes = self.graph.registered_nodes()
        for node_type in registered_nodes:
            context_menu.add_command(
                "Rename Node",
                func=lambda g, n: self.rename_node_action(n),
                node_type=node_type,
            )
            context_menu.add_separator()
            context_menu.add_command(
                "Add Input Port",
                func=lambda g, n: self.add_input_port_action(n),
                node_type=node_type,
            )
            context_menu.add_command(
                "Add Output Port",
                func=lambda g, n: self.add_output_port_action(n),
                node_type=node_type,
            )
            context_menu.add_separator()
            context_menu.add_command(
                "Delete Node",
                func=lambda g, n: self.delete_node_action(n),
                node_type=node_type,
            )

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
            initial_input_data = {}

        node_outputs = {}  # Store data outputs {node_id: {port_name: data}}
        execution_queue = []
        executed_nodes = (
            set()
        )  # Keep track of nodes already executed in this run
        node_map = {node.id: node for node in self.graph.all_nodes()}

        # Find all StartNodes to begin execution
        for node_id, node in node_map.items():
            if isinstance(node, StartNode):
                execution_queue.append(node_id)
                executed_nodes.add(node_id)  # Mark start node as executed

        print(f"Starting workflow execution from nodes: {execution_queue}")

        processed_count = 0
        max_steps = len(node_map) * 2  # Safety break for potential cycles

        while execution_queue and processed_count < max_steps:
            node_id = execution_queue.pop(0)
            current_node = node_map[node_id]
            processed_count += 1

            print(
                f"---\nExecuting node: {current_node.name()} (ID: {node_id})"
            )

            # 1. Prepare input data for the current node
            current_input_data = {}
            for port_name, port in current_node.inputs().items():
                # Skip execution ports for data collection
                if port_name == current_node.EXEC_IN_PORT_NAME:
                    continue

                connected_ports = port.connected_ports()
                if connected_ports:
                    # Assume only one connection for data ports for simplicity
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
                        print(
                            f"  Input '{port_name}' received data from '{source_port.node().name()}.{source_port_name}'"
                        )
                    else:
                        print(
                            f"  Warning: Input '{port_name}' missing data from source '{source_port.node().name()}.{source_port_name}'. Using None."
                        )
                        current_input_data[port_name] = None
                # else: # Input port not connected, might use default value or be optional
                # print(f"  Input '{port_name}' is not connected.")

            # Add initial data if this is a root node (like StartNode, though it usually has no data inputs)
            # This part might need refinement based on how initial data is intended to be used
            if not any(
                p.connected_ports()
                for p_name, p in current_node.inputs().items()
                if p_name != current_node.EXEC_IN_PORT_NAME
            ):
                for port_name in current_node.inputs():
                    if (
                        port_name != current_node.EXEC_IN_PORT_NAME
                        and port_name in initial_input_data
                    ):
                        current_input_data[port_name] = initial_input_data[
                            port_name
                        ]
                        print(f"  Input '{port_name}' received initial data.")

            # 2. Execute the node
            outputs = {}
            triggered_exec_port_name = None
            if hasattr(current_node, "execute") and callable(
                getattr(current_node, "execute")
            ):
                try:
                    outputs = current_node.execute(current_input_data)
                    if outputs is None:
                        outputs = {}
                    node_outputs[node_id] = outputs
                    print(
                        f"  Node '{current_node.name()}' executed. Raw Output: {outputs}"
                    )

                    # Check which execution port was triggered
                    triggered_exec_port_name = outputs.pop(
                        "_exec_triggered", None
                    )
                    if triggered_exec_port_name:
                        print(
                            f"  Execution triggered on port: {triggered_exec_port_name}"
                        )
                    else:
                        # If no specific exec port is triggered, try the default if it exists
                        if (
                            current_node.EXEC_OUT_PORT_NAME
                            in current_node.outputs()
                        ):
                            triggered_exec_port_name = (
                                current_node.EXEC_OUT_PORT_NAME
                            )
                            print(
                                f"  Default execution triggered on port: {triggered_exec_port_name}"
                            )

                except Exception as e:
                    print(f"  Error executing node {current_node.name()}: {e}")
                    node_outputs[node_id] = {}  # Mark as failed
            else:
                print(f"  Node {current_node.name()} has no execute method.")
                node_outputs[node_id] = {}

            # 3. Find and queue the next node(s) based on the triggered execution port
            if (
                triggered_exec_port_name
                and triggered_exec_port_name in current_node.outputs()
            ):
                exec_output_port = current_node.outputs()[
                    triggered_exec_port_name
                ]
                connected_exec_inputs = exec_output_port.connected_ports()

                for next_port in connected_exec_inputs:
                    next_node = next_port.node()
                    next_node_id = next_node.id
                    # Only queue if not already executed in this run to prevent immediate cycles
                    # More robust cycle detection might be needed for complex graphs
                    if next_node_id not in executed_nodes:
                        print(
                            f"  Queueing next node: {next_node.name()} (ID: {next_node_id}) via port {next_port.name()}"
                        )
                        execution_queue.append(next_node_id)
                        executed_nodes.add(next_node_id)
                    else:
                        print(
                            f"  Skipping already executed node: {next_node.name()} (ID: {next_node_id})"
                        )
            elif triggered_exec_port_name:
                print(
                    f"  Warning: Triggered execution port '{triggered_exec_port_name}' not found on node '{current_node.name()}'. Execution stops here."
                )
            else:
                print(
                    f"  Node '{current_node.name()}' did not trigger an execution output. Execution path ends here."
                )

        if processed_count >= max_steps:
            print(
                "Workflow execution stopped: Maximum processing steps reached (potential cycle detected)."
            )
        else:
            print("---\nWorkflow execution finished.")

        # Optional: Log final outputs from nodes that didn't trigger further execution
        final_outputs = {
            node_map[nid].name(): data for nid, data in node_outputs.items()
        }
        print("Final Node Outputs:", final_outputs)
