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


from airunner.gui.widgets.nodegraph.nodes import (
    AgentActionNode,
    BaseWorkflowNode,
    ImageGenerationNode,
    PromptNode,
    TextboxNode,
    RandomNumberNode,
    NumberNode,
    FloatNode,
    BooleanNode,
    LLMRequestNode,
    ImageRequestNode,
    RunLLMNode,
    ImageDisplayNode,
    StartNode,
    BranchNode,
    ForEachLoopNode,
    ForLoopNode,
    WhileLoopNode,
    ReverseForEachLoopNode,
)

from airunner.gui.widgets.nodegraph.add_port_dialog import AddPortDialog
from airunner.gui.widgets.nodegraph.custom_node_graph import CustomNodeGraph

# Import database models and managers
from airunner.data.models.workflow import Workflow
from airunner.data.models.workflow_node import WorkflowNode
from airunner.data.models.workflow_connection import WorkflowConnection


# Properties to explicitly ignore during save/load
IGNORED_NODE_PROPERTIES = {
    "selected",
    "disabled",
    "visible",
    "width",
    "height",
    "pos",
    "border_color",
    "text_color",
    "type",
    "id",
    "icon",
    # Add any other internal NodeGraphQt properties you don't want persisted
}


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

        # Register the new loop nodes
        self.graph.register_node(ForEachLoopNode)
        self.graph.register_node(ForLoopNode)
        self.graph.register_node(WhileLoopNode)
        self.graph.register_node(ReverseForEachLoopNode)

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
        # Allow deleting any node, not just BaseWorkflowNode
        # if not isinstance(node, BaseWorkflowNode):
        #     return
        self.graph.delete_node(node)  # Use graph's delete method

    # --- Database Interaction ---
    def save_workflow(self, name, description=""):
        """Saves the current node graph state to the database."""
        print(f"Saving workflow '{name}'...")

        # 1. Find or create the Workflow record
        workflow = Workflow.objects.filter_by_first(name=name)
        if workflow:
            print(f"Updating existing workflow ID: {workflow.id}")
            # Clear existing nodes and connections for this workflow before saving new ones
            # Note: Deleting nodes should cascade delete connections via relationships
            deleted_node_count = WorkflowNode.objects.delete_by(
                workflow_id=workflow.id
            )
            print(
                f"  Deleted {deleted_node_count} existing nodes (and their connections)."
            )
            # Connections are deleted via cascade from nodes
        else:
            print(f"Creating new workflow '{name}'")
            workflow = Workflow.objects.create(
                name=name, description=description
            )
            if not workflow:
                print("Error: Failed to create workflow database entry.")
                return
            print(f"Created new workflow with ID: {workflow.id}")

        # 2. Save Nodes
        nodes_map = {}  # Map graph node ID to database node ID
        all_graph_nodes = self.graph.all_nodes()
        print(f"Found {len(all_graph_nodes)} nodes in the graph.")

        for node in all_graph_nodes:
            # Get node properties, excluding ignored ones
            properties_to_save = {}
            raw_properties = node.properties()  # Get all properties
            for key, value in raw_properties.items():
                if key not in IGNORED_NODE_PROPERTIES:
                    properties_to_save[key] = value

            # Store dynamic ports if they exist (these are custom, so keep them)
            dynamic_inputs = getattr(node, "_dynamic_inputs", {})
            dynamic_outputs = getattr(node, "_dynamic_outputs", {})
            if dynamic_inputs:  # Only save if not empty
                properties_to_save["_dynamic_inputs"] = dynamic_inputs
            if dynamic_outputs:  # Only save if not empty
                properties_to_save["_dynamic_outputs"] = dynamic_outputs

            # Ensure color is saved as a list (JSON compatible) if it exists
            if "color" in properties_to_save and isinstance(
                properties_to_save["color"], tuple
            ):
                properties_to_save["color"] = list(properties_to_save["color"])

            db_node = WorkflowNode.objects.create(
                workflow_id=workflow.id,
                node_identifier=node.type_,  # Use node.type_ which is like 'ai_runner.nodes.AgentActionNode'
                name=node.name(),
                pos_x=node.pos()[0],
                pos_y=node.pos()[1],
                properties=properties_to_save,  # Save filtered properties
            )
            if db_node:
                nodes_map[node.id] = (
                    db_node.id
                )  # Map graph node ID to DB node ID
                print(
                    f"  Saved node: {node.name()} (Graph ID: {node.id}, DB ID: {db_node.id}) Properties: {properties_to_save}"
                )
            else:
                print(f"  Error saving node: {node.name()}")

        # 3. Save Connections
        all_connections = self.graph.all_connections()
        print(f"Found {len(all_connections)} connections in the graph.")
        for conn in all_connections:
            output_node_graph_id = conn.out_port.node().id
            input_node_graph_id = conn.in_port.node().id

            # Ensure both nodes were saved successfully
            if (
                output_node_graph_id in nodes_map
                and input_node_graph_id in nodes_map
            ):
                output_node_db_id = nodes_map[output_node_graph_id]
                input_node_db_id = nodes_map[input_node_graph_id]

                WorkflowConnection.objects.create(
                    workflow_id=workflow.id,
                    output_node_id=output_node_db_id,
                    output_port_name=conn.out_port.name(),
                    input_node_id=input_node_db_id,
                    input_port_name=conn.in_port.name(),
                )
                print(
                    f"  Saved connection: {conn.out_port.node().name()}.{conn.out_port.name()} -> {conn.in_port.node().name()}.{conn.in_port.name()}"
                )
            else:
                print(
                    f"  Skipping connection due to missing node DB ID: {conn}"
                )

        print(f"Workflow '{name}' saved successfully.")

    def load_workflow(self, workflow_id_or_name):
        """Loads a workflow from the database into the node graph."""
        print(f"Loading workflow '{workflow_id_or_name}'...")

        # 1. Find the workflow
        if isinstance(workflow_id_or_name, int):
            workflow = Workflow.objects.get(pk=workflow_id_or_name)
        else:
            workflow = Workflow.objects.filter_by_first(
                name=workflow_id_or_name
            )

        if not workflow:
            print(f"Error: Workflow '{workflow_id_or_name}' not found.")
            return

        # Initialize lists to hold data, default to empty
        db_nodes = []
        db_connections = []

        # Try eager loading first
        try:
            # Use filter_by_first with eager loading
            workflow_data = Workflow.objects.filter_by_first(
                id=workflow.id,  # Filter by ID to get the specific workflow
                eager_load=["nodes", "connections"],
            )
            if (
                workflow_data
                and hasattr(workflow_data, "nodes")
                and hasattr(workflow_data, "connections")
            ):
                db_nodes = (
                    workflow_data.nodes
                    if workflow_data.nodes is not None
                    else []
                )
                db_connections = (
                    workflow_data.connections
                    if workflow_data.connections is not None
                    else []
                )
                print(
                    f"Successfully fetched workflow data with eager loading for ID {workflow.id}"
                )
            else:
                raise ValueError(
                    "Eager loading failed or returned incomplete data."
                )  # Force fallback

        except Exception as e_eager:
            print(
                f"Warning: Eager loading failed ({e_eager}). Falling back to separate queries."
            )
            # Fallback to fetching separately
            try:
                nodes_result = WorkflowNode.objects.filter_by(
                    workflow_id=workflow.id
                )
                connections_result = WorkflowConnection.objects.filter_by(
                    workflow_id=workflow.id
                )

                db_nodes = nodes_result if nodes_result is not None else []
                db_connections = (
                    connections_result
                    if connections_result is not None
                    else []
                )
                print(
                    f"Successfully fetched nodes ({len(db_nodes)}) and connections ({len(db_connections)}) separately."
                )
            except Exception as e_fallback:
                print(
                    f"Error: Fallback query also failed ({e_fallback}). Cannot load workflow."
                )
                # Clear graph maybe? Or just return
                self.graph.clear_session()
                return

        if not db_nodes:
            print(f"Workflow '{workflow.name}' has no nodes to load.")
            # Clear the graph if loading an empty/failed workflow
            self.graph.clear_session()
            return  # Proceed to clear and show empty graph

        # 2. Clear the current graph
        print("Clearing current graph session...")
        self.graph.clear_session()

        # 3. Load Nodes
        node_map = {}  # Map database node ID to graph node instance
        print(f"Loading {len(db_nodes)} nodes...")
        for db_node in db_nodes:
            try:
                # Create the node instance using its identifier and saved position
                node_instance = self.graph.create_node(
                    db_node.node_identifier,
                    name=db_node.name,
                    pos=(
                        db_node.pos_x,
                        db_node.pos_y,
                    ),  # Set position during creation
                )
                if node_instance:
                    # Restore properties (like text in TextboxNode, etc.)
                    if db_node.properties:
                        print(
                            f"  Restoring properties for {node_instance.name()}: {db_node.properties}"
                        )
                        for (
                            prop_name,
                            prop_value,
                        ) in db_node.properties.items():
                            # Skip ignored properties explicitly (double safety)
                            if prop_name in IGNORED_NODE_PROPERTIES:
                                continue

                            try:
                                # Handle dynamic ports first
                                if prop_name == "_dynamic_inputs":
                                    if hasattr(
                                        node_instance, "add_dynamic_input"
                                    ) and isinstance(prop_value, dict):
                                        for (
                                            port_name,
                                            port_data,
                                        ) in prop_value.items():
                                            node_instance.add_dynamic_input(
                                                port_name
                                            )
                                    # Store for reference if needed, though adding should suffice
                                    # node_instance._dynamic_inputs = prop_value
                                elif prop_name == "_dynamic_outputs":
                                    if hasattr(
                                        node_instance, "add_dynamic_output"
                                    ) and isinstance(prop_value, dict):
                                        for (
                                            port_name,
                                            port_data,
                                        ) in prop_value.items():
                                            node_instance.add_dynamic_output(
                                                port_name
                                            )
                                    # node_instance._dynamic_outputs = prop_value
                                # Handle color: convert list back to tuple
                                elif prop_name == "color" and isinstance(
                                    prop_value, list
                                ):
                                    node_instance.set_color(
                                        *prop_value
                                    )  # Unpack list as args
                                    print(
                                        f"    Set color: {tuple(prop_value)}"
                                    )
                                # Try standard setters first (e.g., set_text)
                                elif hasattr(
                                    node_instance, f"set_{prop_name}"
                                ):
                                    getattr(node_instance, f"set_{prop_name}")(
                                        prop_value
                                    )
                                    print(
                                        f"    Set property using set_{prop_name}: {prop_value}"
                                    )
                                # Try direct attribute setting
                                elif hasattr(node_instance, prop_name):
                                    setattr(
                                        node_instance, prop_name, prop_value
                                    )
                                    print(
                                        f"    Set property using setattr: {prop_name} = {prop_value}"
                                    )
                                # else: # Property not found or settable - ignore silently now
                                #    print(f"    Warning: Property '{prop_name}' not found or settable on node {node_instance.name()}")

                            except Exception as prop_e:
                                print(
                                    f"    Warning: Could not set property '{prop_name}' on node {node_instance.name()}: {prop_e}"
                                )

                    node_map[db_node.id] = (
                        node_instance  # Map DB ID to graph node
                    )
                    print(
                        f"  Loaded node: {node_instance.name()} (DB ID: {db_node.id}, Graph ID: {node_instance.id})"
                    )
                else:
                    print(
                        f"  Error creating node instance for DB ID: {db_node.id} (Identifier: {db_node.node_identifier})"
                    )

            except Exception as e:
                # Catch potential errors during node creation itself (e.g., identifier not found)
                print(
                    f"  FATAL Error loading node DB ID {db_node.id} (Identifier: {db_node.node_identifier}): {e}"
                )
                import traceback

                traceback.print_exc()  # Print full traceback for node creation errors

        # 4. Load Connections
        print(f"Loading {len(db_connections)} connections...")
        for db_conn in db_connections:
            output_node = node_map.get(db_conn.output_node_id)
            input_node = node_map.get(db_conn.input_node_id)
            output_port_name = db_conn.output_port_name
            input_port_name = db_conn.input_port_name

            if output_node and input_node:
                # Find the actual port objects on the node instances
                out_port = output_node.outputs().get(output_port_name)
                in_port = input_node.inputs().get(input_port_name)

                if out_port and in_port:
                    try:
                        self.graph.connect_ports(out_port, in_port)
                        print(
                            f"  Connected: {output_node.name()}.{output_port_name} -> {input_node.name()}.{input_port_name}"
                        )
                    except Exception as e:
                        print(
                            f"  Error connecting ports: {output_node.name()}.{output_port_name} -> {input_node.name()}.{input_port_name}: {e}"
                        )
                else:
                    # More detailed logging for port finding issues
                    out_ports_avail = list(output_node.outputs().keys())
                    in_ports_avail = list(input_node.inputs().keys())
                    print(f"  Skipping connection: Port not found.")
                    print(
                        f"    Output: Wanted '{output_port_name}' on {output_node.name()}. Available: {out_ports_avail}"
                    )
                    print(
                        f"    Input:  Wanted '{input_port_name}' on {input_node.name()}. Available: {in_ports_avail}"
                    )
            else:
                print(
                    f"  Skipping connection: Node instance not found for DB IDs {db_conn.output_node_id} or {db_conn.input_node_id}"
                )

        print(f"Workflow '{workflow.name}' loaded successfully.")

    # --- End Database Interaction ---

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
