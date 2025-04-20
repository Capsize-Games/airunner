from NodeGraphQt import NodesPaletteWidget
from PySide6.QtWidgets import (
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QSplitter,
)
from PySide6.QtCore import Qt, Slot


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

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.nodegraph.add_port_dialog import AddPortDialog
from airunner.gui.widgets.nodegraph.custom_node_graph import CustomNodeGraph
from airunner.gui.widgets.nodegraph.templates.node_graph_ui import (
    Ui_node_graph_widget,
)

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


class NodeGraphWidget(BaseWidget):
    widget_class_ = Ui_node_graph_widget

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize the graph
        self.graph = CustomNodeGraph()

        # Register node types
        for node_cls in [
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
        ]:
            self.graph.register_node(node_cls)

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
        self.ui.graph_widget.layout().addWidget(splitter)

    @Slot()
    def on_run_workflow(self):
        self.execute_workflow()

    @Slot()
    def on_pause_workflow(self):
        print("TODO: PAUSE WORKFLOW")

    @Slot()
    def on_stop_workflow(self):
        print("TODO: STOP WORKFLOW")

    @Slot()
    def on_save_workflow(self):
        self.save_workflow()

    @Slot()
    def on_load_workflow(self):
        self.load_workflow("test_workflow")

    @Slot()
    def on_edit_workflow(self):
        print("TODO: EDIT WORKFLOW")

    @Slot()
    def on_delete_workflow(self):
        print("TODO: DELETE WORKFLOW")

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
        self.logger.info(f"Saving workflow '{name}'...")

        # Step 1: Find or create the workflow
        workflow = self._find_or_create_workflow(name, description)
        if not workflow:
            self.logger.error("Failed to create or retrieve workflow.")
            return

        # Step 2: Save nodes
        nodes_map = self._save_nodes(workflow)

        # Step 3: Save connections
        self._save_connections(workflow, nodes_map)

        self.logger.info(f"Workflow '{name}' saved successfully.")

    def _find_or_create_workflow(self, name, description):
        """Find an existing workflow or create a new one."""
        workflow = Workflow.objects.filter_by_first(name=name)
        if workflow:
            self.logger.info(f"Updating existing workflow ID: {workflow.id}")
            self._clear_existing_workflow_data(workflow)
        else:
            self.logger.info(f"Creating new workflow '{name}'")
            workflow = Workflow.objects.create(
                name=name, description=description
            )
            if workflow:
                self.logger.info(
                    f"Created new workflow with ID: {workflow.id}"
                )
            else:
                self.logger.error(
                    "Error: Failed to create workflow database entry."
                )
        return workflow

    def _clear_existing_workflow_data(self, workflow):
        """Clear existing nodes and connections for the workflow."""
        deleted_node_count = WorkflowNode.objects.delete_by(
            workflow_id=workflow.id
        )
        self.logger.info(
            f"Deleted {deleted_node_count} existing nodes (and their connections)."
        )

    def _save_nodes(self, workflow):
        """Save all nodes in the graph to the database."""
        nodes_map = {}  # Map graph node ID to database node ID
        all_graph_nodes = self.graph.all_nodes()
        self.logger.info(f"Found {len(all_graph_nodes)} nodes in the graph.")

        for node in all_graph_nodes:
            properties_to_save = self._extract_node_properties(node)
            db_node = WorkflowNode.objects.create(
                workflow_id=workflow.id,
                node_identifier=node.type_,
                name=node.name(),
                pos_x=node.pos()[0],
                pos_y=node.pos()[1],
                properties=properties_to_save,
            )
            if db_node:
                nodes_map[node.id] = db_node.id
                self.logger.info(
                    f"Saved node: {node.name()} (Graph ID: {node.id}, DB ID: {db_node.id}) Properties: {properties_to_save}"
                )
            else:
                self.logger.error(f"Error saving node: {node.name()}")
        return nodes_map

    def _extract_node_properties(self, node):
        """Extract and filter properties of a node for saving."""
        properties_to_save = {}
        raw_properties = node.properties()
        for key, value in raw_properties.items():
            if key not in IGNORED_NODE_PROPERTIES:
                properties_to_save[key] = value

        # Save dynamic ports if they exist
        dynamic_inputs = getattr(node, "_dynamic_inputs", {})
        dynamic_outputs = getattr(node, "_dynamic_outputs", {})
        if dynamic_inputs:
            properties_to_save["_dynamic_inputs"] = dynamic_inputs
        if dynamic_outputs:
            properties_to_save["_dynamic_outputs"] = dynamic_outputs

        # Ensure color is saved as a list (JSON compatible)
        if "color" in properties_to_save and isinstance(
            properties_to_save["color"], tuple
        ):
            properties_to_save["color"] = list(properties_to_save["color"])

        return properties_to_save

    def _save_connections(self, workflow, nodes_map):
        """Save all connections in the graph to the database."""
        all_connections = self.graph.all_connections()
        self.logger.info(
            f"Found {len(all_connections)} connections in the graph."
        )

        for conn in all_connections:
            output_node_graph_id = conn.out_port.node().id
            input_node_graph_id = conn.in_port.node().id

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
                self.logger.info(
                    f"Saved connection: {conn.out_port.node().name()}.{conn.out_port.name()} -> {conn.in_port.node().name()}.{conn.in_port.name()}"
                )
            else:
                self.logger.warning(
                    f"Skipping connection due to missing node DB ID: {conn}"
                )

    def load_workflow(self, workflow_id_or_name):
        """Loads a workflow from the database into the node graph."""
        self.logger.info(f"Loading workflow '{workflow_id_or_name}'...")

        # Find the workflow and fetch its data
        workflow, db_nodes, db_connections = self._find_workflow_and_data(
            workflow_id_or_name
        )
        if not workflow:
            return

        # Handle empty workflow
        if not db_nodes:
            self.logger.info(
                f"Workflow '{workflow.name}' has no nodes to load."
            )
            self.graph.clear_session()
            return

        # Clear the current graph
        self.logger.info("Clearing current graph session...")
        self.graph.clear_session()

        # Load nodes and create mapping
        node_map = self._load_workflow_nodes(db_nodes)

        # Load connections between nodes
        self._load_workflow_connections(db_connections, node_map)

        self.logger.info(f"Workflow '{workflow.name}' loaded successfully.")

    def _find_workflow_and_data(self, workflow_id_or_name):
        """Find workflow by ID/name and fetch its nodes and connections."""
        # Find the workflow
        if isinstance(workflow_id_or_name, int):
            workflow = Workflow.objects.get(pk=workflow_id_or_name)
        else:
            workflow = Workflow.objects.filter_by_first(
                name=workflow_id_or_name
            )

        if not workflow:
            self.logger.error(f"Workflow '{workflow_id_or_name}' not found.")
            return None, [], []

        # Get workflow data using eager loading first, then fallback to separate queries
        db_nodes, db_connections = self._fetch_workflow_data(workflow)
        return workflow, db_nodes, db_connections

    def _fetch_workflow_data(self, workflow):
        """Fetch workflow data using eager loading or separate queries as fallback."""
        db_nodes = []
        db_connections = []

        # Try eager loading first
        try:
            workflow_data = Workflow.objects.filter_by_first(
                id=workflow.id,
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
                self.logger.info(
                    f"Successfully fetched workflow data with eager loading for ID {workflow.id}"
                )
            else:
                raise ValueError(
                    "Eager loading failed or returned incomplete data."
                )

        except Exception as e_eager:
            self.logger.warning(
                f"Eager loading failed ({e_eager}). Falling back to separate queries."
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

                self.logger.info(
                    f"Successfully fetched nodes ({len(db_nodes)}) and connections ({len(db_connections)}) separately."
                )
            except Exception as e_fallback:
                self.logger.error(
                    f"Fallback query also failed ({e_fallback}). Cannot load workflow."
                )
                self.graph.clear_session()

        return db_nodes, db_connections

    def _load_workflow_nodes(self, db_nodes):
        """Load nodes from database records into the graph."""
        node_map = {}  # Map database node ID to graph node instance
        self.logger.info(f"Loading {len(db_nodes)} nodes...")

        for db_node in db_nodes:
            try:
                # Create the node instance using its identifier and saved position
                node_instance = self.graph.create_node(
                    db_node.node_identifier,
                    name=db_node.name,
                    pos=(db_node.pos_x, db_node.pos_y),
                )

                if node_instance:
                    # Restore node properties
                    if db_node.properties:
                        self._restore_node_properties(
                            node_instance, db_node.properties
                        )

                    # Map DB ID to graph node
                    node_map[db_node.id] = node_instance
                    self.logger.info(
                        f"  Loaded node: {node_instance.name()} (DB ID: {db_node.id}, Graph ID: {node_instance.id})"
                    )
                else:
                    self.logger.error(
                        f"  Error creating node instance for DB ID: {db_node.id} (Identifier: {db_node.node_identifier})"
                    )

            except Exception as e:
                # Catch potential errors during node creation
                self.logger.error(
                    f"  FATAL Error loading node DB ID {db_node.id} (Identifier: {db_node.node_identifier}): {e}"
                )
                import traceback

                traceback.print_exc()

        return node_map

    def _restore_node_properties(self, node_instance, properties):
        """Restore node properties from saved data."""
        self.logger.info(
            f"  Restoring properties for {node_instance.name()}: {properties}"
        )

        for prop_name, prop_value in properties.items():
            # Skip ignored properties
            if prop_name in IGNORED_NODE_PROPERTIES:
                continue

            try:
                # Handle dynamic input ports
                if prop_name == "_dynamic_inputs":
                    self._restore_dynamic_ports(
                        node_instance, prop_value, "input"
                    )

                # Handle dynamic output ports
                elif prop_name == "_dynamic_outputs":
                    self._restore_dynamic_ports(
                        node_instance, prop_value, "output"
                    )

                # Handle color property specifically
                elif prop_name == "color" and isinstance(prop_value, list):
                    node_instance.set_color(*prop_value)  # Unpack list as args
                    self.logger.info(f"    Set color: {tuple(prop_value)}")

                # Try standard setter methods
                elif hasattr(node_instance, f"set_{prop_name}"):
                    getattr(node_instance, f"set_{prop_name}")(prop_value)
                    self.logger.info(
                        f"    Set property using set_{prop_name}: {prop_value}"
                    )

                # Try direct attribute setting
                elif hasattr(node_instance, prop_name):
                    setattr(node_instance, prop_name, prop_value)
                    self.logger.info(
                        f"    Set property directly: {prop_name} = {prop_value}"
                    )

                else:
                    self.logger.warning(
                        f"    Property '{prop_name}' not handled for node instance."
                    )
            except Exception as e:
                self.logger.error(
                    f"  Error restoring property '{prop_name}' for node '{node_instance.name()}': {e}"
                )
                import traceback

                traceback.print_exc()
        self.logger.info(
            f"  Finished restoring properties for {node_instance.name()}."
        )
        self.logger.info(f"  Node properties restored successfully.")

    def load_workflow(self, workflow_id_or_name):
        """Loads a workflow from the database into the node graph."""
        self.logger.info(f"Loading workflow '{workflow_id_or_name}'...")

        # Find the workflow and fetch its data
        workflow, db_nodes, db_connections = self._find_workflow_and_data(
            workflow_id_or_name
        )
        if not workflow:
            return

        # Handle empty workflow
        if not db_nodes:
            self.logger.info(
                f"Workflow '{workflow.name}' has no nodes to load."
            )
            self.graph.clear_session()
            return

        # Clear the current graph
        self.logger.info("Clearing current graph session...")
        self.graph.clear_session()

        # Load nodes and create mapping
        node_map = self._load_workflow_nodes(db_nodes)

        # Load connections between nodes
        self._load_workflow_connections(db_connections, node_map)

        self.logger.info(f"Workflow '{workflow.name}' loaded successfully.")

    def _find_workflow_and_data(self, workflow_id_or_name):
        """Find workflow by ID/name and fetch its nodes and connections."""
        # Find the workflow
        if isinstance(workflow_id_or_name, int):
            workflow = Workflow.objects.get(pk=workflow_id_or_name)
        else:
            workflow = Workflow.objects.filter_by_first(
                name=workflow_id_or_name
            )

        if not workflow:
            self.logger.error(f"Workflow '{workflow_id_or_name}' not found.")
            return None, [], []

        # Get workflow data using eager loading first, then fallback to separate queries
        db_nodes, db_connections = self._fetch_workflow_data(workflow)
        return workflow, db_nodes, db_connections

    def _fetch_workflow_data(self, workflow):
        """Fetch workflow data using eager loading or separate queries as fallback."""
        db_nodes = []
        db_connections = []

        # Try eager loading first
        try:
            workflow_data = Workflow.objects.filter_by_first(
                id=workflow.id,
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
                self.logger.info(
                    f"Successfully fetched workflow data with eager loading for ID {workflow.id}"
                )
            else:
                raise ValueError(
                    "Eager loading failed or returned incomplete data."
                )

        except Exception as e_eager:
            self.logger.warning(
                f"Eager loading failed ({e_eager}). Falling back to separate queries."
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

                self.logger.info(
                    f"Successfully fetched nodes ({len(db_nodes)}) and connections ({len(db_connections)}) separately."
                )
            except Exception as e_fallback:
                self.logger.error(
                    f"Fallback query also failed ({e_fallback}). Cannot load workflow."
                )
                self.graph.clear_session()

        return db_nodes, db_connections

    def _load_workflow_nodes(self, db_nodes):
        """Load nodes from database records into the graph."""
        node_map = {}  # Map database node ID to graph node instance
        self.logger.info(f"Loading {len(db_nodes)} nodes...")

        for db_node in db_nodes:
            try:
                # Create the node instance using its identifier and saved position
                node_instance = self.graph.create_node(
                    db_node.node_identifier,
                    name=db_node.name,
                    pos=(db_node.pos_x, db_node.pos_y),
                )

                if node_instance:
                    # Restore node properties
                    if db_node.properties:
                        self._restore_node_properties(
                            node_instance, db_node.properties
                        )

                    # Map DB ID to graph node
                    node_map[db_node.id] = node_instance
                    self.logger.info(
                        f"  Loaded node: {node_instance.name()} (DB ID: {db_node.id}, Graph ID: {node_instance.id})"
                    )
                else:
                    self.logger.error(
                        f"  Error creating node instance for DB ID: {db_node.id} (Identifier: {db_node.node_identifier})"
                    )

            except Exception as e:
                # Catch potential errors during node creation
                self.logger.error(
                    f"  FATAL Error loading node DB ID {db_node.id} (Identifier: {db_node.node_identifier}): {e}"
                )
                import traceback

                traceback.print_exc()

        return node_map

    def _restore_node_properties(self, node_instance, properties):
        """Restore node properties from saved data."""
        self.logger.info(
            f"  Restoring properties for {node_instance.name()}: {properties}"
        )

        for prop_name, prop_value in properties.items():
            # Skip ignored properties
            if prop_name in IGNORED_NODE_PROPERTIES:
                continue

            try:
                # Handle dynamic input ports
                if prop_name == "_dynamic_inputs":
                    self._restore_dynamic_ports(
                        node_instance, prop_value, "input"
                    )

                # Handle dynamic output ports
                elif prop_name == "_dynamic_outputs":
                    self._restore_dynamic_ports(
                        node_instance, prop_value, "output"
                    )

                # Handle color property specifically
                elif prop_name == "color" and isinstance(prop_value, list):
                    node_instance.set_color(*prop_value)  # Unpack list as args
                    self.logger.info(f"    Set color: {tuple(prop_value)}")

                # Try standard setter methods
                elif hasattr(node_instance, f"set_{prop_name}"):
                    getattr(node_instance, f"set_{prop_name}")(prop_value)
                    self.logger.info(
                        f"    Set property using set_{prop_name}: {prop_value}"
                    )

                # Try direct attribute setting
                elif hasattr(node_instance, prop_name):
                    setattr(node_instance, prop_name, prop_value)
                    self.logger.info(
                        f"    Set property directly: {prop_name} = {prop_value}"
                    )
                else:
                    self.logger.warning(
                        f"    Property '{prop_name}' not handled for node instance."
                    )
            except Exception as e:
                self.logger.error(
                    f"  Error restoring property '{prop_name}' for node '{node_instance.name()}': {e}"
                )
                import traceback

                traceback.print_exc()
        self.logger.info(
            f"  Finished restoring properties for {node_instance.name()}."
        )
        self.logger.info(f"  Node properties restored successfully.")

    # --- End Database Interaction ---

    def execute_workflow(self, initial_input_data=None):
        if initial_input_data is None:
            initial_input_data = {}

        node_outputs = {}  # Store data outputs {node_id: {port_name: data}}
        execution_queue, executed_nodes, node_map = self._initialize_execution(
            initial_input_data
        )

        processed_count = 0
        max_steps = len(node_map) * 2  # Safety break for potential cycles

        while execution_queue and processed_count < max_steps:
            node_id = execution_queue.pop(0)
            current_node = node_map[node_id]
            processed_count += 1

            self.logger.info(
                f"---\nExecuting node: {current_node.name()} (ID: {node_id})"
            )

            # Prepare input data for the current node
            current_input_data = self._prepare_input_data(
                current_node, node_outputs, initial_input_data
            )

            # Execute the node
            outputs, triggered_exec_port_name = self._execute_node(
                current_node, current_input_data, node_outputs
            )

            # Queue the next nodes based on the triggered execution port
            self._queue_next_nodes(
                current_node,
                triggered_exec_port_name,
                execution_queue,
                executed_nodes,
            )

        self._finalize_execution(
            processed_count, max_steps, node_outputs, node_map
        )

    def _initialize_execution(self, initial_input_data):
        """Initialize the execution queue, executed nodes, and node map."""
        execution_queue = []
        executed_nodes = set()
        node_map = {node.id: node for node in self.graph.all_nodes()}

        # Find all StartNodes to begin execution
        for node_id, node in node_map.items():
            if isinstance(node, StartNode):
                execution_queue.append(node_id)
                executed_nodes.add(node_id)  # Mark start node as executed

        self.logger.info(
            f"Starting workflow execution from nodes: {execution_queue}"
        )
        return execution_queue, executed_nodes, node_map

    def _prepare_input_data(
        self, current_node, node_outputs, initial_input_data
    ):
        """Prepare input data for the current node."""
        current_input_data = {}
        for port_name, port in current_node.inputs().items():
            if port_name == current_node.EXEC_IN_PORT_NAME:
                continue

            connected_ports = port.connected_ports()
            if connected_ports:
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
                    self.logger.info(
                        f"  Input '{port_name}' received data from '{source_port.node().name()}.{source_port_name}'"
                    )
                else:
                    self.logger.warning(
                        f"  Input '{port_name}' missing data from source '{source_port.node().name()}.{source_port_name}'. Using None."
                    )
                    current_input_data[port_name] = None

        # Add initial data if this is a root node
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
                    self.logger.info(
                        f"  Input '{port_name}' received initial data."
                    )

        return current_input_data

    def _execute_node(self, current_node, current_input_data, node_outputs):
        """Execute the current node and return its outputs and triggered execution port."""
        outputs = {}
        triggered_exec_port_name = None

        if hasattr(current_node, "execute") and callable(
            getattr(current_node, "execute")
        ):
            try:
                outputs = current_node.execute(current_input_data) or {}
                node_outputs[current_node.id] = outputs
                self.logger.info(
                    f"  Node '{current_node.name()}' executed. Raw Output: {outputs}"
                )

                triggered_exec_port_name = outputs.pop("_exec_triggered", None)
                if triggered_exec_port_name:
                    self.logger.info(
                        f"  Execution triggered on port: {triggered_exec_port_name}"
                    )
                elif current_node.EXEC_OUT_PORT_NAME in current_node.outputs():
                    triggered_exec_port_name = current_node.EXEC_OUT_PORT_NAME
                    self.logger.info(
                        f"  Default execution triggered on port: {triggered_exec_port_name}"
                    )

            except Exception as e:
                self.logger.error(
                    f"  Error executing node {current_node.name()}: {e}"
                )
                node_outputs[current_node.id] = {}  # Mark as failed
        else:
            self.logger.info(
                f"  Node {current_node.name()} has no execute method."
            )
            node_outputs[current_node.id] = {}

        return outputs, triggered_exec_port_name

    def _queue_next_nodes(
        self,
        current_node,
        triggered_exec_port_name,
        execution_queue,
        executed_nodes,
    ):
        """Queue the next nodes based on the triggered execution port."""
        if (
            triggered_exec_port_name
            and triggered_exec_port_name in current_node.outputs()
        ):
            exec_output_port = current_node.outputs()[triggered_exec_port_name]
            connected_exec_inputs = exec_output_port.connected_ports()

            for next_port in connected_exec_inputs:
                next_node = next_port.node()
                next_node_id = next_node.id
                if next_node_id not in executed_nodes:
                    self.logger.info(
                        f"  Queueing next node: {next_node.name()} (ID: {next_node_id}) via port {next_port.name()}"
                    )
                    execution_queue.append(next_node_id)
                    executed_nodes.add(next_node_id)
                else:
                    self.logger.info(
                        f"  Skipping already executed node: {next_node.name()} (ID: {next_node_id})"
                    )
        elif triggered_exec_port_name:
            self.logger.warning(
                f"  Triggered execution port '{triggered_exec_port_name}' not found on node '{current_node.name()}'. Execution stops here."
            )
        else:
            self.logger.info(
                f"  Node '{current_node.name()}' did not trigger an execution output. Execution path ends here."
            )

    def _finalize_execution(
        self, processed_count, max_steps, node_outputs, node_map
    ):
        """Finalize the workflow execution and log results."""
        if processed_count >= max_steps:
            self.logger.info(
                "Workflow execution stopped: Maximum processing steps reached (potential cycle detected)."
            )
        else:
            self.logger.info("---\nWorkflow execution finished.")

        final_outputs = {
            node_map[nid].name(): data for nid, data in node_outputs.items()
        }
        self.logger.info("Final Node Outputs:", final_outputs)
