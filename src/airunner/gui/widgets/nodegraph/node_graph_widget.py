from typing import Dict, Tuple, Optional, List
from NodeGraphQt import NodesPaletteWidget
from PySide6.QtWidgets import (
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Slot


from airunner.enums import SignalCode
from airunner.gui.widgets.nodegraph.nodes import (
    AgentActionNode,
    BaseWorkflowNode,
    ImageGenerationNode,
    PromptNode,
    TextboxNode,
    RandomNumberNode,
    LLMRequestNode,
    ImageRequestNode,
    RunLLMNode,
    ImageDisplayNode,
    StartNode,
    ForEachLoopNode,
    ForLoopNode,
    WhileLoopNode,
    ReverseForEachLoopNode,
    CanvasNode,
    ChatbotNode,
    LoraNode,
    EmbeddingNode,
    LLMBranchNode,
    SetNode,
)

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.nodegraph.add_port_dialog import AddPortDialog
from airunner.gui.widgets.nodegraph.custom_node_graph import CustomNodeGraph
from airunner.gui.widgets.nodegraph.templates.node_graph_ui import (
    Ui_node_graph_widget,
)

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
    "type_",
    "id",
    "icon",
    "name",
    "color",
    "layout_direction",
    "port_deletion_allowed",
    "subgraph_session",
    "outputs",
    "inputs",
    "custom",
}


class NodeGraphWidget(BaseWidget):
    widget_class_ = Ui_node_graph_widget
    # Define a custom MIME type for dragging variables
    VARIABLE_MIME_TYPE = "application/x-airunner-variable"

    def __init__(self, parent=None, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL: self._on_node_execution_completed,
        }
        super().__init__(*args, **kwargs)
        self.graph = CustomNodeGraph()
        self.viewer = self.graph.widget
        self._node_outputs = {}
        self._pending_nodes = {}
        self._nodes_palette: Optional[NodesPaletteWidget] = None
        self._register_nodes()
        self._initialize_context_menu()
        self._register_graph()

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
        """Shows a dialog to save the workflow, allowing creation of a new one or overwriting an existing one."""
        workflows = Workflow.objects.all()
        workflow_map = {
            wf.name: wf for wf in workflows
        }  # Map name to workflow object

        dialog = QDialog(self)
        dialog.setWindowTitle("Save Workflow")
        layout = QFormLayout(dialog)

        # Combo box to choose action
        action_combo = QComboBox(dialog)
        action_combo.addItem("Create New Workflow", "new")
        action_combo.addItem("Overwrite Existing Workflow", "existing")

        # Workflow Name input (enabled only for new)
        name_input = QLineEdit(dialog)
        name_input.setPlaceholderText(
            "Enter a unique name for the new workflow"
        )

        # Workflow Description input
        description_input = QLineEdit(dialog)
        description_input.setPlaceholderText(
            "(Optional) Describe the workflow"
        )

        # Combo box for existing workflows (enabled only for overwrite)
        existing_combo = QComboBox(dialog)
        existing_combo.addItem("-- Select Workflow --", -1)  # Placeholder
        for wf in workflows:
            existing_combo.addItem(f"{wf.name} (ID: {wf.id})", wf.id)

        # Add widgets to layout
        layout.addRow("Action:", action_combo)
        layout.addRow("Name:", name_input)
        layout.addRow("Existing Workflow:", existing_combo)
        layout.addRow("Description:", description_input)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        # Initial state and signal connection
        def update_dialog_state():
            action = action_combo.currentData()
            is_new = action == "new"
            name_input.setEnabled(is_new)
            existing_combo.setEnabled(not is_new)
            if not is_new and existing_combo.currentIndex() > 0:
                selected_id = existing_combo.currentData()
                selected_wf = next(
                    (wf for wf in workflows if wf.id == selected_id), None
                )
                if selected_wf:
                    name_input.setText(
                        selected_wf.name
                    )  # Show name but disable editing
                    description_input.setText(selected_wf.description or "")
                else:
                    name_input.clear()
                    description_input.clear()
            elif is_new:
                name_input.clear()  # Clear name for new entry
                description_input.clear()

        action_combo.currentIndexChanged.connect(update_dialog_state)
        existing_combo.currentIndexChanged.connect(
            update_dialog_state
        )  # Update description on selection change
        update_dialog_state()  # Set initial state

        if dialog.exec():
            action = action_combo.currentData()
            name = name_input.text().strip()
            description = description_input.text().strip()

            if action == "new":
                if not name:
                    QMessageBox.warning(
                        self,
                        "Save Workflow",
                        "Workflow name cannot be empty for a new workflow.",
                    )
                    return

                # Check if name already exists
                if name in workflow_map:
                    reply = QMessageBox.question(
                        self,
                        "Workflow Exists",
                        f"A workflow named '{name}' already exists (ID: {workflow_map[name].id}). Do you want to overwrite it?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.Cancel,
                    )
                    if reply == QMessageBox.Yes:
                        # Overwrite existing
                        self._perform_save(
                            workflow_map[name].id, name, description
                        )
                    elif reply == QMessageBox.Cancel:
                        return  # User cancelled
                    else:
                        QMessageBox.information(
                            self,
                            "Save Workflow",
                            "Save cancelled. Please choose a different name.",
                        )
                        return
                else:
                    # Create and save new
                    self._create_and_save_workflow(name, description)

            elif action == "existing":
                selected_id = existing_combo.currentData()
                if selected_id == -1:
                    QMessageBox.warning(
                        self,
                        "Save Workflow",
                        "Please select an existing workflow to overwrite.",
                    )
                    return
                # Save to existing (name is taken from the selected workflow, description is updated)
                selected_wf = next(
                    (wf for wf in workflows if wf.id == selected_id), None
                )
                if selected_wf:
                    self._perform_save(
                        selected_id, selected_wf.name, description
                    )
                else:
                    QMessageBox.critical(
                        self, "Save Workflow", "Selected workflow not found."
                    )

    @Slot()
    def on_load_workflow(self):
        """Shows a dialog to select and load an existing workflow."""
        try:
            workflows = Workflow.objects.all()
            if not workflows:
                QMessageBox.information(
                    self, "Load Workflow", "No saved workflows found."
                )
                return
        except Exception as e:
            self.logger.error(f"Error fetching workflows: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Load Workflow", f"Error fetching workflows: {e}"
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Load Workflow")
        layout = QFormLayout(dialog)

        combo = QComboBox(dialog)
        combo.addItem("-- Select Workflow --", -1)  # Placeholder item
        for wf in workflows:
            combo.addItem(
                f"{wf.name} (ID: {wf.id})", wf.id
            )  # Display name and ID, store ID

        layout.addRow("Workflow:", combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Open | QDialogButtonBox.Cancel, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            selected_id = combo.currentData()
            if selected_id != -1:
                try:
                    self._perform_load(selected_id)
                except Exception as e:
                    self.logger.error(
                        f"Error loading workflow ID {selected_id}: {e}",
                        exc_info=True,
                    )
                    QMessageBox.critical(
                        self, "Load Workflow", f"Failed to load workflow: {e}"
                    )
            else:
                QMessageBox.warning(
                    self, "Load Workflow", "No workflow selected."
                )

    @Slot()
    def on_edit_workflow(self):
        print("TODO: EDIT WORKFLOW")

    @Slot()
    def on_delete_workflow(self):
        print("TODO: DELETE WORKFLOW")

    @Slot()
    def on_clear_workflow(self):
        """Clear the current workflow graph and variables."""
        self._clear_graph()
        self.logger.info("Workflow graph and variables cleared.")

    def _register_nodes(self):
        self._nodes_palette = NodesPaletteWidget(
            parent=None,
            node_graph=self.graph,
        )
        for node_cls in [
            AgentActionNode,
            BaseWorkflowNode,
            ImageGenerationNode,
            PromptNode,
            TextboxNode,
            RandomNumberNode,
            LLMRequestNode,
            ImageRequestNode,
            RunLLMNode,
            ImageDisplayNode,
            StartNode,
            ForEachLoopNode,
            ForLoopNode,
            WhileLoopNode,
            ReverseForEachLoopNode,
            CanvasNode,
            ChatbotNode,
            LoraNode,
            EmbeddingNode,
            LLMBranchNode,
            SetNode,
        ]:
            self.graph.register_node(node_cls)

    def _register_graph(self):
        """
        Emit a register graph signal so that other widgets can
        interact with the node graph.
        """
        self.emit_signal(
            SignalCode.REGISTER_GRAPH_SIGNAL,
            {
                "graph": self.graph,
                "nodes_palette": self._nodes_palette,
                "callback": lambda: self._finalize_register_graph(),
            },
        )

    def _finalize_register_graph(self):
        """
        Finalize the registration of the graph by connecting signals
        and setting up the UI.
        """
        self._initialize_ui()

    def _initialize_ui(self):
        self.ui.splitter.setSizes([200, 700, 200])
        self.ui.graph.layout().addWidget(self.viewer)
        self.ui.palette.layout().addWidget(self._nodes_palette)

    def _initialize_context_menu(self):
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
        self.graph.delete_node(node)  # Use graph's delete method

    # --- Database Interaction ---
    def _perform_save(
        self, workflow_id: int, name: str, description: str = ""
    ):
        """Saves the current node graph state, including variables, to the specified workflow ID."""
        self.logger.info(f"Saving workflow '{name}' (ID: {workflow_id})...")
        workflow = self._find_workflow_by_id(workflow_id)
        if not workflow:
            self.logger.error(
                f"Workflow with ID {workflow_id} not found for saving."
            )
            QMessageBox.critical(
                self, "Save Error", f"Workflow ID {workflow_id} not found."
            )
            return

        # Update name and description before clearing data
        workflow.name = name
        workflow.description = description
        try:
            workflow.save()
            self.logger.info(
                f"Updated metadata for workflow '{name}' (ID: {workflow_id})."
            )
        except Exception as e:
            self.logger.error(
                f"Error updating workflow metadata for ID {workflow_id}: {e}",
                exc_info=True,
            )
            QMessageBox.critical(
                self, "Save Error", f"Could not update workflow metadata: {e}"
            )
            return  # Stop if we can't even save the metadata

        # Now clear existing data and save new state
        self._clear_existing_workflow_data(workflow)
        self._save_variables(workflow)
        nodes_map = self._save_nodes(workflow)
        self._save_connections(workflow, nodes_map)
        self.logger.info(
            f"Workflow '{name}' (ID: {workflow_id}) saved successfully."
        )
        QMessageBox.information(
            self, "Save Workflow", f"Workflow '{name}' saved successfully."
        )

    def _create_and_save_workflow(self, name: str, description: str):
        """Creates a new workflow record and then saves the current graph to it."""
        self.logger.info(
            f"Attempting to create and save new workflow: '{name}'"
        )
        try:
            # Ensure name uniqueness again just before creation (though dialog should handle it)
            existing = Workflow.objects.filter_by_first(name=name)
            if existing:
                self.logger.warning(
                    f"Workflow '{name}' already exists (ID: {existing.id}). Aborting creation."
                )
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Workflow '{name}' already exists. Save aborted.",
                )
                return

            workflow = self._create_workflow(name, description)
            if workflow:
                self.logger.info(
                    f"Created new workflow '{name}' with ID {workflow.id}"
                )
                # Now save the graph data to this new workflow
                self._perform_save(workflow.id, name, description)
            else:
                # _create_workflow already logs error
                QMessageBox.critical(
                    self,
                    "Save Error",
                    "Failed to create the new workflow record in the database.",
                )
        except Exception as e:
            self.logger.error(
                f"Error during creation/saving of new workflow '{name}': {e}",
                exc_info=True,
            )
            QMessageBox.critical(
                self, "Save Error", f"An unexpected error occurred: {e}"
            )

    def _find_or_create_workflow(
        self,
        workflow_id: int,
        name: Optional[str] = None,  # Name is now primarily handled by dialogs
        description: Optional[str] = None,
    ) -> Optional[Workflow]:
        """Find an existing workflow. Creation is handled by _create_and_save_workflow."""
        workflow = self._find_workflow_by_id(workflow_id)
        return workflow

    def _find_workflow_by_id(self, workflow_id: int) -> Optional[Workflow]:
        """Find a workflow by its ID."""
        return Workflow.objects.get(
            pk=workflow_id,
            eager_load=["nodes", "connections"],
        )

    def _create_workflow(self, name: str, description: str) -> Workflow:
        """Create a new workflow in the database."""
        self.logger.info(f"Creating new workflow")
        workflow = Workflow.objects.create(name=name, description=description)
        if not workflow:
            self.logger.error("Error: Failed to create workflow.")
            return None
        return workflow

    def _clear_existing_workflow_data(self, workflow):
        """Clear existing connections and nodes for the workflow."""
        # Explicitly delete connections first to avoid foreign key issues if cascade isn't reliable
        deleted_connection_count = WorkflowConnection.objects.delete_by(
            workflow_id=workflow.id
        )
        self.logger.info(
            f"Deleted {deleted_connection_count} existing connections."
        )
        # Then delete nodes
        deleted_node_count = WorkflowNode.objects.delete_by(
            workflow_id=workflow.id
        )
        self.logger.info(f"Deleted {deleted_node_count} existing nodes.")

    def _save_variables(self, workflow: Workflow):
        """Saves the graph variables to the workflow's data."""
        try:
            variables_data = [
                var.to_dict() for var in self.ui.variables.variables
            ]
            # --- Add logging here ---
            self.logger.info(
                f"Data being saved to workflow.variables: {variables_data}"
            )
            # --- End logging ---
            workflow.variables = variables_data
            workflow.save()  # Ensure the ORM actually persists the change
            self.logger.info(
                f"Saved {len(variables_data)} variables to workflow ID {workflow.id}"
            )
        except Exception as e:
            self.logger.error(
                f"Error saving variables for workflow ID {workflow.id}: {e}"
            )

    def _save_nodes(self, workflow):
        """Save all nodes in the graph to the database."""
        nodes_map = {}
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
                # Skip internal properties that reference the node itself or other non-serializable objects
                if key == "_graph_item" or key.startswith("__"):
                    self.logger.info(
                        f"  Skipping non-serializable property: {key}"
                    )
                    continue

                # Try to filter out other non-serializable values
                try:
                    # Quick test for JSON serializability
                    import json

                    json.dumps(value)
                    properties_to_save[key] = value
                except (TypeError, OverflowError):
                    self.logger.info(
                        f"  Skipping non-serializable property: {key} with type {type(value).__name__}"
                    )
                    continue

        # Explicitly save the names of dynamically added ports
        # Check if the node is an instance of our base class that supports dynamic ports
        # and retrieve the lists of dynamic port names directly from the node instance.
        if isinstance(node, BaseWorkflowNode):
            # Assuming BaseWorkflowNode stores dynamic port names in these attributes.
            # If these attributes don't exist, BaseWorkflowNode needs modification.
            dynamic_input_names = getattr(node, "_dynamic_input_names", [])
            if dynamic_input_names:
                properties_to_save["_dynamic_input_names"] = (
                    dynamic_input_names
                )
                self.logger.info(
                    f"  Saving dynamic input names for {node.name()}: {dynamic_input_names}"
                )

            dynamic_output_names = getattr(node, "_dynamic_output_names", [])
            if dynamic_output_names:
                properties_to_save["_dynamic_output_names"] = (
                    dynamic_output_names
                )
                self.logger.info(
                    f"  Saving dynamic output names for {node.name()}: {dynamic_output_names}"
                )

        # Ensure color is saved as a list (JSON compatible)
        if "color" in properties_to_save and isinstance(
            properties_to_save["color"], tuple
        ):
            properties_to_save["color"] = list(properties_to_save["color"])

        return properties_to_save

    def _save_connections(self, workflow, nodes_map):
        """Save all connections in the graph to the database."""
        # Get connections by iterating through nodes and their ports,
        # as self.graph.all_connections() seems unavailable or problematic.
        all_connections_data = []
        all_graph_nodes = (
            self.graph.all_nodes()
        )  # Assumes self.graph.all_nodes() exists
        for node in all_graph_nodes:
            for out_port in node.outputs().values():
                for in_port in out_port.connected_ports():
                    # Store connection info in a dictionary mimicking the original structure
                    all_connections_data.append(
                        {"out_port": out_port, "in_port": in_port}
                    )

        self.logger.info(
            f"Found {len(all_connections_data)} connections by iterating through nodes."
        )

        for conn_data in all_connections_data:
            out_port = conn_data["out_port"]
            in_port = conn_data["in_port"]

            output_node_graph_id = out_port.node().id
            input_node_graph_id = in_port.node().id

            if (
                output_node_graph_id in nodes_map
                and input_node_graph_id in nodes_map
            ):
                output_node_db_id = nodes_map[output_node_graph_id]
                input_node_db_id = nodes_map[input_node_graph_id]

                WorkflowConnection.objects.create(
                    workflow_id=workflow.id,
                    output_node_id=output_node_db_id,
                    output_port_name=out_port.name(),
                    input_node_id=input_node_db_id,
                    input_port_name=in_port.name(),
                )
                self.logger.info(
                    f"Saved connection: {out_port.node().name()}.{out_port.name()} -> {in_port.node().name()}.{in_port.name()}"
                )
            else:
                self.logger.warning(
                    f"Skipping connection due to missing node DB ID mapping: {out_port.node().name()}.{out_port.name()} -> {in_port.node().name()}.{in_port.name()}"
                )

    def _perform_load(self, workflow_id):
        """Loads a workflow, including variables, from the database."""
        self.logger.info(f"Loading workflow ID '{workflow_id}'...")

        try:
            workflow, db_nodes, db_connections = self._find_workflow_and_data(
                workflow_id=workflow_id
            )
            if (
                not workflow
            ):  # Should be caught by _find_workflow_and_data assertion, but double check
                raise ValueError(f"Workflow ID {workflow_id} not found.")

        except Exception as e:
            self.logger.error(
                f"Failed to find or fetch data for workflow ID {workflow_id}: {e}",
                exc_info=True,
            )
            # Raise the exception to be caught by the caller (on_load_workflow) for user message
            raise  # Re-raise the exception

        # Proceed with loading if data fetch was successful
        self._clear_graph()
        data = dict(
            workflow=workflow,
            db_nodes=db_nodes,
            db_connections=db_connections,
        )
        self.emit_signal(
            SignalCode.WORKFLOW_LOAD_SIGNAL,
            {
                "workflow": workflow,
                "callback": lambda _data=data: self._finalize_load_workflow(
                    _data
                ),
            },
        )

    def load_workflow(self, workflow_id):
        """Loads a workflow from the database."""
        self.logger.info(f"Loading workflow '{workflow_id}'...")

        try:
            workflow, db_nodes, db_connections = self._find_workflow_and_data(
                workflow_id=workflow_id
            )
        except Exception as e:
            self.logger.error(e)
            return

        self._clear_graph()
        data = dict(
            workflow_id=workflow_id,
            db_nodes=db_nodes,
            db_connections=db_connections,
        )
        self.emit_signal(
            SignalCode.WORKFLOW_LOAD_SIGNAL,
            {
                "workflow": workflow,
                "callback": lambda _data=data: self._finalize_load_workflow(
                    _data
                ),
            },
        )

    def _finalize_load_workflow(self, data: Dict):
        db_nodes = data.get("db_nodes")
        db_connections = data.get("db_connections")
        workflow = data.get("workflow")
        if db_nodes is not None:
            node_map = self._load_workflow_nodes(db_nodes)
            self._load_workflow_connections(db_connections, node_map)
            self.logger.info(
                f"Workflow '{workflow.name}' loaded successfully."
            )

    def _clear_graph(self):
        self.logger.info("Clearing current graph session and variables...")
        self.emit_signal(
            SignalCode.CLEAR_WORKFLOW_SIGNAL,
            {"callback": self._finalize_clear_graph},
        )

    def _finalize_clear_graph(self):

        # Clear the graph session
        self.graph.clear_session()

        # Explicitly try to clear the node factory registry as well
        if hasattr(self.graph, "_node_factory") and hasattr(
            self.graph._node_factory, "_nodes"
        ):
            # Keep only the base nodes, remove dynamically registered ones (like variable getters)
            # This assumes base nodes don't follow the VariableGetter naming pattern
            # A safer approach might involve checking the class inheritance if possible
            original_node_types = {
                identifier: cls
                for identifier, cls in self.graph._node_factory._nodes.items()
                if not identifier.startswith(
                    "airunner.variables."
                )  # Adjust prefix if needed
            }
            self.graph._node_factory._nodes = original_node_types
            self.logger.info(
                f"Explicitly cleared dynamic nodes from factory. Remaining: {list(original_node_types.keys())}"
            )
        else:
            self.logger.warning(
                "Could not explicitly clear node factory registry."
            )

    def _load_workflow_connections(self, db_connections, node_map):
        """Load connections from database records into the graph."""
        self.logger.info(f"Loading {len(db_connections)} connections...")
        connections_loaded = 0
        for db_conn in db_connections:
            try:
                output_node = node_map.get(db_conn.output_node_id)
                input_node = node_map.get(db_conn.input_node_id)

                if output_node and input_node:
                    # Find the port objects on the nodes
                    output_port = output_node.outputs().get(
                        db_conn.output_port_name
                    )
                    input_port = input_node.inputs().get(
                        db_conn.input_port_name
                    )

                    if output_port and input_port:
                        # Use the connect_to method on the output port
                        output_port.connect_to(input_port)
                        connections_loaded += 1
                        self.logger.info(
                            f"  Connected: {output_node.name()}.{output_port.name()} -> {input_node.name()}.{input_port.name()}"
                        )
                    else:
                        self.logger.warning(
                            f"  Skipping connection: Port not found. Output: '{db_conn.output_port_name}' on {output_node.name()}, Input: '{db_conn.input_port_name}' on {input_node.name()}"
                        )
                else:
                    self.logger.warning(
                        f"  Skipping connection: Node not found in map. Output DB ID: {db_conn.output_node_id}, Input DB ID: {db_conn.input_node_id}"
                    )

            except Exception as e:
                # Log the specific exception and traceback for better debugging
                self.logger.error(
                    f"  FATAL Error loading connection DB ID {db_conn.id}: {e}",
                    exc_info=True,
                )
        self.logger.info(
            f"  Finished loading connections. Total loaded: {connections_loaded}/{len(db_connections)}"
        )

    def _find_workflow_and_data(
        self, workflow_id: int
    ) -> Tuple[Optional[Workflow], Optional[List], Optional[List]]:
        """Find workflow by ID/name and fetch its nodes and connections."""
        workflow = self._find_workflow_by_id(workflow_id)
        assert workflow is not None, f"Workflow '{workflow_id}' not found."
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
                    push_undo=False,  # Avoid polluting undo stack during load
                )

                if not node_instance:
                    self.logger.error(
                        f"  Failed to create node instance for identifier: {db_node.node_identifier}, name: {db_node.name}"
                    )
                    continue

                # Restore dynamic ports BEFORE restoring other properties
                if (
                    isinstance(node_instance, BaseWorkflowNode)
                    and db_node.properties
                ):
                    # Retrieve saved dynamic port names
                    dynamic_input_names = db_node.properties.get(
                        "_dynamic_input_names", []
                    )
                    for name in dynamic_input_names:
                        # Ensure the add_dynamic_input method also updates the node's internal list (_dynamic_input_names)
                        node_instance.add_dynamic_input(name)
                        self.logger.info(
                            f"  Restored dynamic input '{name}' for node {node_instance.name()}"
                        )

                    dynamic_output_names = db_node.properties.get(
                        "_dynamic_output_names", []
                    )
                    for name in dynamic_output_names:
                        # Ensure the add_dynamic_output method also updates the node's internal list (_dynamic_output_names)
                        node_instance.add_dynamic_output(name)
                        self.logger.info(
                            f"  Restored dynamic output '{name}' for node {node_instance.name()}"
                        )

                # Restore other properties
                if db_node.properties:
                    self._restore_node_properties(
                        node_instance, db_node.properties
                    )

                node_map[db_node.id] = node_instance
                self.logger.info(
                    f"  Loaded node: {node_instance.name()} (DB ID: {db_node.id}, Graph ID: {node_instance.id})"
                )

            except Exception as e:
                self.logger.error(
                    f"  FATAL Error loading node DB ID {db_node.id} ({db_node.name}): {e}",
                    exc_info=True,  # Log traceback for debugging
                )

        self.graph.undo_stack().clear()  # Clear undo stack after loading
        self.logger.info(
            f"Finished loading nodes. Total loaded: {len(node_map)}/{len(db_nodes)}"
        )
        return node_map

    def _restore_node_properties(self, node_instance, properties):
        """Restore node properties from saved data."""
        self.logger.info(
            f"  Restoring properties for {node_instance.name()}: {list(properties.keys())}"  # Log only keys for brevity
        )

        for prop_name, prop_value in properties.items():
            # Skip ignored properties and dynamic port lists (handled in _load_workflow_nodes)
            if prop_name in IGNORED_NODE_PROPERTIES or prop_name in [
                "_dynamic_input_names",
                "_dynamic_output_names",
            ]:
                self.logger.debug(f"    Skipping property: {prop_name}")
                continue

            # Handle color conversion from list back to tuple if needed by NodeGraphQt
            if prop_name == "color" and isinstance(prop_value, list):
                prop_value = tuple(prop_value)

            try:
                # Use NodeGraphQt's property system primarily
                if node_instance.has_property(prop_name):
                    node_instance.set_property(prop_name, prop_value)
                    self.logger.info(
                        f"    Set property {prop_name} = {prop_value}"
                    )
                # Fallback for direct attributes ONLY if necessary and NOT callable (methods)
                elif hasattr(node_instance, prop_name) and not callable(
                    getattr(node_instance, prop_name)
                ):
                    setattr(node_instance, prop_value)
                    self.logger.warning(
                        f"    Set attribute directly (use with caution): {prop_name} = {prop_value}"
                    )
                else:
                    self.logger.warning(
                        f"    Property '{prop_name}' not found or settable on node {node_instance.name()}. Skipping."
                    )

            except Exception as e:
                self.logger.error(
                    f"    Error restoring property '{prop_name}' for node {node_instance.name()}: {e}"
                )

    # --- End Database Interaction ---

    def execute_workflow(self, initial_input_data=None):
        if initial_input_data is None:
            initial_input_data = {}

        node_outputs = {}  # Store data outputs {node_id: {port_name: data}}
        execution_queue, executed_nodes, node_map = self._initialize_execution(
            initial_input_data
        )

        processed_count = 0
        max_steps = len(node_map) * 10

        while execution_queue and processed_count < max_steps:
            node_id = execution_queue.pop(0)

            # Skip if already fully executed (important: don't skip nodes that might be pending)
            if node_id in executed_nodes:
                continue

            current_node = node_map.get(node_id)
            if not current_node:
                self.logger.warning(
                    f"Node ID {node_id} not found in map during execution. Skipping."
                )
                continue

            self.logger.info(
                f"Executing node: {current_node.name()} (ID: {node_id})"
            )

            # Prepare input data for the current node
            current_input_data = self._prepare_input_data(
                current_node, node_outputs, initial_input_data
            )

            # Execute the node's logic
            triggered_exec_port_name, output_data = self._execute_node(
                current_node, current_input_data, node_outputs
            )

            # Check if the node execution is pending
            if triggered_exec_port_name is None and output_data is None:
                # Node execution is pending, add it back to the end of the queue for retry
                self.logger.info(
                    f"  Node '{current_node.name()}' is pending execution. Adding back to queue."
                )
                execution_queue.append(node_id)
                # Don't mark as executed yet, don't increment processed_count beyond the retry count
                continue

            # Store the output data
            if output_data:
                node_outputs[node_id] = output_data
                self.logger.info(
                    f"  Node {current_node.name()} produced output: {list(output_data.keys())}"
                )

            # Mark as executed
            executed_nodes.add(node_id)
            processed_count += 1

            # Queue next nodes based on the triggered execution port
            if triggered_exec_port_name:
                self._queue_next_nodes(
                    current_node,
                    triggered_exec_port_name,
                    execution_queue,
                    executed_nodes,
                )
            else:
                self.logger.info(
                    f"  Node {current_node.name()} did not trigger an execution output."
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
        start_node_ids = []
        for node_id, node in node_map.items():
            if isinstance(node, StartNode):
                start_node_ids.append(node_id)

        # Add start nodes to the front of the queue
        execution_queue.extend(start_node_ids)

        self.logger.info(
            f"Starting workflow execution. Initial queue: {start_node_ids}"
        )
        return execution_queue, executed_nodes, node_map

    def _prepare_input_data(
        self, current_node, node_outputs, initial_input_data
    ):
        current_input_data = {}
        for port_name, port in current_node.inputs().items():
            if port_name == current_node.EXEC_IN_PORT_NAME:
                continue
            connected_ports = port.connected_ports()
            if connected_ports:
                source_port = connected_ports[0]
                source_node = source_port.node()
                source_node_id = source_node.id
                source_port_name = source_port.name()
                # If the source node hasn't been executed, do it now
                if source_node_id not in node_outputs:
                    self.logger.warning(
                        f"  Source node '{source_node.name()}' for input '{port_name}' not executed yet. Attempting to execute it recursively."
                    )
                    source_input_data = self._prepare_input_data(
                        source_node, node_outputs, initial_input_data
                    )
                    _, source_output_data = self._execute_node(
                        source_node, source_input_data, node_outputs
                    )
                    if source_output_data:
                        node_outputs[source_node_id] = source_output_data
                    else:
                        self.logger.error(
                            f"  Recursive execution of source node '{source_node.name()}' failed or produced no output."
                        )

                # Now get the value
                if (
                    source_node_id in node_outputs
                    and source_port_name in node_outputs[source_node_id]
                ):
                    current_input_data[port_name] = node_outputs[
                        source_node_id
                    ][source_port_name]
                    self.logger.info(
                        f"  Input '{port_name}' received data from '{source_node.name()}.{source_port_name}'"
                    )
                else:
                    current_input_data[port_name] = None
                    self.logger.warning(
                        f"  Input '{port_name}' missing data from source '{source_node.name()}.{source_port_name}'. Using None."
                    )
                    current_input_data[port_name] = None
        for port_name in current_node.inputs():
            if (
                port_name != current_node.EXEC_IN_PORT_NAME
                and port_name not in current_input_data
                and port_name in initial_input_data
            ):
                current_input_data[port_name] = initial_input_data[port_name]
                self.logger.info(
                    f"  Input '{port_name}' received initial data."
                )
        return current_input_data

    def _execute_node(self, current_node, current_input_data, node_outputs):
        """Execute the current node and return its outputs and triggered execution port."""
        output_data = {}
        triggered_exec_port_name = None

        if hasattr(current_node, "execute") and callable(
            getattr(current_node, "execute")
        ):
            try:
                # Execute the node and get its output
                outputs = current_node.execute(current_input_data)

                # Check if the node returned None, which indicates pending execution
                if outputs is None:
                    self.logger.info(
                        f"  Node '{current_node.name()}' execution is pending. Will retry later."
                    )
                    # Return None for both values to indicate pending execution
                    return None, None

                # Make a copy of outputs to avoid modifying the original during pop operations
                output_data = {k: v for k, v in outputs.items()}

                # Check if the node triggered an execution output
                if "_exec_triggered" in outputs:
                    triggered_exec_port_name = outputs["_exec_triggered"]
                    # Don't store the execution trigger in the node's outputs
                    output_data.pop("_exec_triggered", None)
                elif current_node.EXEC_OUT_PORT_NAME in current_node.outputs():
                    # Default to standard execution output if available
                    triggered_exec_port_name = current_node.EXEC_OUT_PORT_NAME

                # Store outputs for use by downstream nodes
                node_outputs[current_node.id] = output_data
                self.logger.info(
                    f"  Node '{current_node.name()}' executed. Output: {list(output_data.keys())}"
                )

                if triggered_exec_port_name:
                    self.logger.info(
                        f"  Execution will flow through port: {triggered_exec_port_name}"
                    )
                else:
                    self.logger.info(
                        f"  No execution port triggered, execution path ends here"
                    )

            except Exception as e:
                self.logger.error(
                    f"  Error executing node {current_node.name()}: {e}",
                    exc_info=True,
                )
                # Mark as failed but don't halt workflow
                node_outputs[current_node.id] = {}
        else:
            self.logger.info(
                f"  Node {current_node.name()} has no execute method."
            )
            node_outputs[current_node.id] = {}

        return triggered_exec_port_name, output_data

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
                if next_node_id not in execution_queue:
                    self.logger.info(
                        f"  Queueing next node: {next_node.name()} (ID: {next_node_id}) via port {next_port.name()}"
                    )
                    execution_queue.append(next_node_id)
                else:
                    self.logger.info(
                        f"  Node already in queue: {next_node.name()} (ID: {next_node_id})"
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
        self.logger.info(f"Final Node Outputs: {final_outputs}")

    def _on_node_execution_completed(self, data: dict):
        """
        Handle the NODE_EXECUTION_COMPLETED_SIGNAL emitted by nodes that complete asynchronous operations.
        This allows us to continue workflow execution after an async node like LLMBranchNode completes.

        Args:
            data: Dictionary containing the node_id and result (execution port to trigger)
        """
        node_id = data.get("node_id")
        result = data.get("result")

        if not node_id or not result:
            self.logger.warning(
                "Received incomplete node execution completed signal"
            )
            return

        self.logger.info(
            f"Received execution completed signal from node {node_id}, result: {result}"
        )

        # Find the node in our graph
        node = None
        for n in self.graph.all_nodes():
            if n.id == node_id:
                node = n
                break

        if not node:
            self.logger.warning(f"Could not find node with ID {node_id}")
            return

        self.logger.info(
            f"Continuing workflow execution from node {node.name()}"
        )

        # Create a new execution queue starting from this node's output ports
        execution_queue = []
        executed_nodes = set()  # Start fresh
        node_map = {n.id: n for n in self.graph.all_nodes()}

        # Queue the next nodes manually based on the result port
        if result in node.outputs():
            output_port = node.outputs()[result]
            for connected_port in output_port.connected_ports():
                next_node = connected_port.node()
                execution_queue.append(next_node.id)
                self.logger.info(
                    f"Queuing node {next_node.name()} for continued execution"
                )

        # Continue workflow execution from these nodes
        if execution_queue:
            # Start a new execution with the current node outputs
            self.execute_workflow_from_queue(execution_queue, executed_nodes)
        else:
            self.logger.info("No nodes to execute after async completion")

    def execute_workflow_from_queue(
        self, execution_queue, executed_nodes=None, initial_input_data=None
    ):
        """
        Execute a workflow starting from a specific execution queue.
        Used for continuing workflow execution after async operations.
        """
        if executed_nodes is None:
            executed_nodes = set()

        if initial_input_data is None:
            initial_input_data = {}

        node_outputs = {}  # Store data outputs {node_id: {port_name: data}}
        node_map = {node.id: node for node in self.graph.all_nodes()}

        processed_count = 0
        max_steps = len(node_map) * 10  # Increased safety limit

        self.logger.info(
            f"Continuing workflow execution with queue: {execution_queue}"
        )

        while execution_queue and processed_count < max_steps:
            node_id = execution_queue.pop(0)

            # Skip if already executed
            if node_id in executed_nodes:
                continue

            current_node = node_map.get(node_id)
            if not current_node:
                self.logger.warning(
                    f"Node ID {node_id} not found in map during execution. Skipping."
                )
                continue

            self.logger.info(
                f"Executing node: {current_node.name()} (ID: {node_id})"
            )

            # Prepare input data for the current node
            current_input_data = self._prepare_input_data(
                current_node, node_outputs, initial_input_data
            )

            # Execute the node's logic
            triggered_exec_port_name, output_data = self._execute_node(
                current_node, current_input_data, node_outputs
            )

            # Check if the node execution is pending
            if triggered_exec_port_name is None and output_data is None:
                # Node execution is pending, add it back for retry
                self.logger.info(
                    f"  Node '{current_node.name()}' is pending execution. Adding back to queue."
                )
                execution_queue.append(node_id)
                # Don't mark as executed yet
                continue

            # Store the output data
            if output_data:
                node_outputs[node_id] = output_data
                self.logger.info(
                    f"  Node {current_node.name()} produced output: {list(output_data.keys())}"
                )

            # Mark as executed
            executed_nodes.add(node_id)
            processed_count += 1

            # Queue next nodes based on the triggered execution port
            if triggered_exec_port_name:
                self._queue_next_nodes(
                    current_node,
                    triggered_exec_port_name,
                    execution_queue,
                    executed_nodes,
                )
            else:
                self.logger.info(
                    f"  Node {current_node.name()} did not trigger an execution output."
                )

        self._finalize_execution(
            processed_count, max_steps, node_outputs, node_map
        )
