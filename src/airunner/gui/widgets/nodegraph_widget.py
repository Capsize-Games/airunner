from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QMenu,
    QLabel,
    QToolBar,
)
from PySide6.QtCore import QPoint, Qt
from NodeGraphQt import NodeGraph, BaseNode, NodeGraphMenu


# Base class for all workflow nodes in this system
class BaseWorkflowNode(BaseNode):
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


# Node representing a single Agent Action
class AgentActionNode(BaseWorkflowNode):
    NODE_NAME = (
        "Agent Action"  # Default name, can be overridden or set instance-wise
    )

    def __init__(self):
        super().__init__()
        # Default ports - can be customized via properties or methods
        self.add_input("in_message")
        self.add_output("out_message")
        # Add a text input widget to specify the action class/name
        self.add_text_input("action_name", "Action Name", tab="widgets")

    # Override execute for AgentAction specific logic (placeholder)
    def execute(self, input_data):
        action_name = self.get_property("action_name")
        in_message = input_data.get(
            "in_message", None
        )  # Get data from the connected input port
        print(
            f"Executing Agent Action: {action_name} with input: {in_message}"
        )
        # Dummy logic: Find the corresponding AgentAction class based on action_name
        # and call its run method. For now, just pass data through.
        output_data = f"Action '{action_name}' processed: {in_message}"
        return {
            "out_message": output_data
        }  # Return data for the 'out_message' port


# Node representing a nested Workflow
class WorkflowNode(BaseWorkflowNode):
    NODE_NAME = "Workflow"  # Default name

    def __init__(self):
        super().__init__()
        # Ports for triggering and receiving results from the nested workflow
        self.add_input("start_flow")
        self.add_output("flow_complete")
        # Add a property to store the ID or name of the nested workflow
        self.add_text_input(
            "nested_workflow_id", "Workflow ID/Name", tab="widgets"
        )

    # Override execute for Workflow specific logic (placeholder)
    def execute(self, input_data):
        nested_workflow_id = self.get_property("nested_workflow_id")
        start_data = input_data.get("start_flow", None)
        print(
            f"Executing nested Workflow: {nested_workflow_id} with start data: {start_data}"
        )
        # Dummy logic: Load and execute the nested workflow based on nested_workflow_id.
        # For now, just pass data through.
        output_data = f"Workflow '{nested_workflow_id}' completed, result from: {start_data}"
        return {
            "flow_complete": output_data
        }  # Return data for the 'flow_complete' port


class AddPortDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Port")
        layout = QFormLayout(self)

        self.port_name_input = QLineEdit(self)
        self.port_type_input = QLineEdit(
            self
        )  # Simple text for now, could be dropdown

        layout.addRow("Port Name:", self.port_name_input)
        layout.addRow("Port Type (optional):", self.port_type_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_port_info(self):
        return self.port_name_input.text(), self.port_type_input.text()


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
        self.graph = NodeGraph()

        # Register node types
        self.graph.register_node(AgentActionNode)
        self.graph.register_node(WorkflowNode)

        # --- Setup Custom Node Context Menu ---
        # Get the default node context menu
        node_menu = self.graph.get_context_menu("nodes")

        # Add custom actions using add_command
        # The provided function will receive graph and node objects
        node_menu.add_command(
            "Rename Node",
            self.rename_node_action,
            node_type="BaseWorkflowNode",
        )
        node_menu.add_separator()
        node_menu.add_command(
            "Add Input Port",
            self.add_input_port_action,
            node_type="BaseWorkflowNode",
        )
        node_menu.add_command(
            "Add Output Port",
            self.add_output_port_action,
            node_type="BaseWorkflowNode",
        )
        # --- End Custom Context Menu Setup ---

        # Create the graph view and add to layout
        viewer = self.graph.widget
        layout.addWidget(viewer)

        # Example node creation
        node1 = self.graph.create_node(
            "airunner.workflow.nodes.AgentActionNode",
            name="Analyze Convo Action",
            pos=[100, 100],
        )
        node1.set_property("action_name", "AnalyzeConversation")

        node2 = self.graph.create_node(
            "airunner.workflow.nodes.AgentActionNode",
            name="Update Mood Action",
            pos=[400, 100],
        )
        node2.set_property("action_name", "UpdateMood")

        # Connect nodes - correct way to connect output to input
        if node1.outputs() and node2.inputs():
            output_port = list(node1.outputs().values())[0]
            input_port = list(node2.inputs().values())[0]
            output_port.connect_to(input_port)

        # Example Workflow Node
        workflow_node = self.graph.create_node(
            "airunner.workflow.nodes.WorkflowNode",
            name="Sub Workflow",
            pos=[100, 300],
        )
        workflow_node.set_property(
            "nested_workflow_id", "mood_update_sub_flow"
        )

    def add_agent_node(self):
        """Add a new agent action node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.AgentActionNode", name="New Agent Action"
        )
        # Position the new node in view
        self.graph.center_on([node])
        return node

    def add_workflow_node(self):
        """Add a new workflow node at the center of the view."""
        node = self.graph.create_node(
            "airunner.workflow.nodes.WorkflowNode", name="New Workflow"
        )
        # Position the new node in view
        self.graph.center_on([node])
        return node

    # Modified action handlers to accept graph and node arguments
    def rename_node_action(self, graph, node):
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

    def add_input_port_action(self, graph, node):
        """Adds a dynamic input port to the node."""
        if not isinstance(node, BaseWorkflowNode):
            return

        dialog = AddPortDialog(self)
        if dialog.exec():
            port_name, port_type = dialog.get_port_info()
            if port_name:
                node.add_dynamic_input(port_name)
                # TODO: Update node properties in DB model if saving is implemented

    def add_output_port_action(self, graph, node):
        """Adds a dynamic output port to the node."""
        if not isinstance(node, BaseWorkflowNode):
            return

        dialog = AddPortDialog(self)
        if dialog.exec():
            port_name, port_type = dialog.get_port_info()
            if port_name:
                node.add_dynamic_output(port_name)
                # TODO: Update node properties in DB model if saving is implemented

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
