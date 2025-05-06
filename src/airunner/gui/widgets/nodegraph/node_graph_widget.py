import os
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
    GenerateImageNode,
    FramePackNode,
    VideoNode,
    # Gemma3Node,
    PromptBuilderNode,
    SchedulerNode,
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
from airunner.utils.settings import get_qsettings

from airunner.workers.node_graph_worker import NodeGraphWorker
from airunner.utils.application.create_worker import create_worker

IGNORED_NODE_PROPERTIES = {}


class NodeGraphWidget(BaseWidget):
    widget_class_ = Ui_node_graph_widget
    # Define a custom MIME type for dragging variables
    VARIABLE_MIME_TYPE = "application/x-airunner-variable"

    def __init__(self, parent=None, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL: self._on_node_execution_completed,
        }
        self._splitters = ["splitter"]
        super().__init__(*args, **kwargs)
        self.q_settings = get_qsettings()
        self.graph = CustomNodeGraph()
        self.viewer = self.graph.widget
        self._node_outputs = {}
        self._pending_nodes = {}
        self._nodes_palette: Optional[NodesPaletteWidget] = None
        self.node_graph_worker = create_worker(NodeGraphWorker)
        self._register_nodes()
        self._initialize_context_menu()
        self._register_graph()

        if self.current_workflow_id is not None:
            self._perform_load(self.current_workflow_id)

        # Check if framepack is available
        here = os.path.dirname(__file__)
        if os.path.exists(os.path.join(here, "../../FramePack")):
            from airunner.workers.framepack_worker import FramePackWorker

            self.framepack_worker = create_worker(FramePackWorker)

        self.stop_progress_bar()

    @property
    def current_workflow_id(self) -> Optional[int]:
        id = self.q_settings.value("current_workflow_id", None)
        return id

    @current_workflow_id.setter
    def current_workflow_id(self, value: Optional[int]):
        self.q_settings.setValue("current_workflow_id", value)
        self.q_settings.sync()

    @Slot()
    def on_new_button_clicked(self):
        self.new_workflow()

    @Slot()
    def on_play_button_clicked(self):
        self.run_workflow()

    @Slot()
    def on_pause_button_clicked(self):
        self.pause_workflow()

    @Slot()
    def on_stop_button_clicked(self):
        self.stop_workflow()

    @Slot()
    def on_save_button_clicked(self):
        self.save_workflow()

    @Slot()
    def on_load_button_clicked(self):
        self.load_workflow()

    @Slot()
    def on_delete_button_clicked(self):
        self.delete_workflow()

    @Slot()
    def on_clear_button_clicked(self):
        self.clear_graph()

    def start_progress_bar(self):
        self.ui.progressBar.setRange(0, 0)
        self.ui.progressBar.setValue(0)

    def stop_progress_bar(self):
        self.ui.progressBar.setRange(0, 1)
        self.ui.progressBar.setValue(1)
        self.ui.progressBar.reset()

    def new_workflow(self):
        """Create a new workflow, clearing the current graph and variables."""
        self.clear_graph()
        self.current_workflow_id = None
        self._register_graph()
        self.logger.info("New workflow created.")

    def run_workflow(self):
        self.start_progress_bar()
        self.api.nodegraph.run_workflow(self.graph)

    def pause_workflow(self):
        self.api.nodegraph.pause_workflow(self.graph)

    def stop_workflow(self):
        self.stop_progress_bar()
        self.api.nodegraph.stop_workflow(self.graph)

    def save_workflow(self):
        """Shows a dialog to save the workflow, allowing creation of a new one or overwriting an existing one."""
        if self.current_workflow_id is not None:
            self._perform_save(self.current_workflow_id)
            return

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

    def load_workflow(self):
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
                self._perform_load(selected_id)
            else:
                QMessageBox.warning(
                    self, "Load Workflow", "No workflow selected."
                )

    def edit_workflow(self):
        print("TODO: EDIT WORKFLOW")

    def delete_workflow(self):
        print("TODO: DELETE WORKFLOW")

    def clear_graph(self):
        """Clear the current workflow graph and variables."""
        self._clear_graph()
        self.current_workflow_id = None
        self.logger.info("Workflow graph and variables cleared.")

    def _register_nodes(self):
        self._nodes_palette = NodesPaletteWidget(
            parent=None,
            node_graph=self.graph,
        )
        for node_cls in [
            AgentActionNode,
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
            GenerateImageNode,
            FramePackNode,
            VideoNode,
            # Gemma3Node,
            PromptBuilderNode,
            SchedulerNode,
        ]:
            self.graph.register_node(node_cls)

    def _register_graph(self):
        """
        Emit a register graph signal so that other widgets can
        interact with the node graph.
        """
        self.api.nodegraph.register_graph(
            graph=self.graph,
            nodes_palette=self._nodes_palette,
            finalize=self._finalize_register_graph,
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
        """Deletes the selected node from the graph unless it's a StartNode."""
        # Prevent StartNode deletion
        if isinstance(node, StartNode):
            self.logger.warning(
                "Cannot delete StartNode as it is required for workflow execution."
            )
            QMessageBox.warning(
                self,
                "Cannot Delete Node",
                "The Start Node cannot be deleted as it is required for workflow execution.",
            )
            return

        # Delete any other type of node
        self.graph.delete_node(node)  # Use graph's delete method

    # --- Database Interaction ---
    def _perform_save(
        self,
        workflow_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Saves the current node graph state to the specified workflow using CRUD operations."""
        self.logger.info(f"Saving workflow '{name}' (ID: {workflow_id})...")
        workflow = self._find_workflow_by_id(workflow_id)
        if not workflow:
            self.logger.error(f"Workflow with ID {workflow_id} not found.")
            QMessageBox.critical(
                self, "Save Error", f"Workflow ID {workflow_id} not found."
            )
            return

        name = workflow.name if name is None else name
        description = (
            workflow.description if description is None else description
        )

        # Update workflow metadata
        workflow.name = name
        workflow.description = description
        try:
            workflow.save()
        except Exception as e:
            self.logger.error(
                f"Error updating workflow metadata: {e}", exc_info=True
            )
            QMessageBox.critical(
                self, "Save Error", f"Could not update workflow metadata: {e}"
            )
            return

        # Save graph state using CRUD operations
        self._save_variables(workflow)
        nodes_map = self._save_nodes(workflow_id)
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

    def _save_nodes(self, workflow_id: int) -> Dict:
        """
        Save nodes in the graph to the database using CRUD operations.
        Updates existing nodes, creates new ones, and removes obsolete ones.
        Ensures only one StartNode is saved.
        """
        nodes_map = {}  # Maps graph node IDs to database node IDs
        all_graph_nodes = self.graph.all_nodes()
        self.logger.info(
            f"Processing {len(all_graph_nodes)} nodes for saving..."
        )

        # Check for multiple StartNodes in the graph
        start_nodes = [
            node for node in all_graph_nodes if isinstance(node, StartNode)
        ]
        if len(start_nodes) > 1:
            self.logger.warning(
                f"Multiple StartNodes ({len(start_nodes)}) detected in graph. Will save only the first one."
            )
            # Keep only the first StartNode - remove others from processing
            kept_start_node = start_nodes[0]
            all_graph_nodes = [
                node
                for node in all_graph_nodes
                if not isinstance(node, StartNode)
                or node.id == kept_start_node.id
            ]
            self.logger.info(
                f"Keeping StartNode: {kept_start_node.name()} (ID: {kept_start_node.id}), filtering out {len(start_nodes) - 1} duplicate StartNodes."
            )

        # First, get all existing nodes for this workflow
        try:
            existing_nodes = WorkflowNode.objects.filter_by(
                workflow_id=workflow_id
            )
            existing_node_map = {}
            for db_node in existing_nodes:
                # Create a key based on node identifier and position to find matching nodes
                key = f"{db_node.node_identifier}_{db_node.pos_x}_{db_node.pos_y}"
                existing_node_map[key] = db_node
            self.logger.info(
                f"Found {len(existing_node_map)} existing nodes in the database"
            )
        except Exception as e:
            self.logger.error(
                f"Error retrieving existing nodes: {e}", exc_info=True
            )
            existing_node_map = {}

        # Track which database nodes are still in use
        used_db_node_ids = set()

        # Process all graph nodes
        for node in all_graph_nodes:
            properties_to_save = self._extract_node_properties(node)

            # Create a key to match with existing nodes
            node_key = f"{node.type_}_{node.pos()[0]}_{node.pos()[1]}"
            db_node = existing_node_map.get(node_key)

            if db_node:
                # Update existing node
                self.logger.info(
                    f"Updating existing node: {node.name()} (Graph ID: {node.id}, DB ID: {db_node.id})"
                )
                db_node.name = node.name()
                db_node.pos_x = node.pos()[0]
                db_node.pos_y = node.pos()[1]
                db_node.properties = properties_to_save
                try:
                    db_node.save()
                    nodes_map[node.id] = db_node.id
                    used_db_node_ids.add(db_node.id)
                except Exception as e:
                    self.logger.error(
                        f"Error updating node {node.name()}: {e}",
                        exc_info=True,
                    )
            else:
                # Create new node
                try:
                    db_node = WorkflowNode.objects.create(
                        workflow_id=workflow_id,
                        node_identifier=node.type_,
                        name=node.name(),
                        pos_x=node.pos()[0],
                        pos_y=node.pos()[1],
                        properties=properties_to_save,
                    )
                    if db_node:
                        nodes_map[node.id] = db_node.id
                        used_db_node_ids.add(db_node.id)
                        self.logger.info(
                            f"Created new node: {node.name()} (Graph ID: {node.id}, DB ID: {db_node.id})"
                        )
                    else:
                        self.logger.error(
                            f"Failed to create node: {node.name()}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error creating node {node.name()}: {e}",
                        exc_info=True,
                    )

        # Delete nodes that are no longer in the graph
        nodes_to_delete = [
            db_node.id
            for db_node in existing_nodes
            if db_node.id not in used_db_node_ids
        ]
        if nodes_to_delete:
            try:
                for node_id in nodes_to_delete:
                    WorkflowNode.objects.delete_by(id=node_id)
                self.logger.info(
                    f"Deleted {len(nodes_to_delete)} obsolete nodes from the database"
                )
            except Exception as e:
                self.logger.error(
                    f"Error deleting obsolete nodes: {e}", exc_info=True
                )

        # Check if we have any StartNodes at all in the database after saving
        start_node_identifiers = [
            node_type
            for node_type in self.graph.registered_nodes()
            if isinstance(node_type, type) and issubclass(node_type, StartNode)
        ]

        if start_node_identifiers:
            start_node_db_check = WorkflowNode.objects.filter_by_first(
                workflow_id=workflow_id,
                node_identifier__in=start_node_identifiers,
            )

            if not start_node_db_check:
                self.logger.warning(
                    "No StartNode found in database after saving. Adding one automatically."
                )
                # We need to update the nodes_map to include the newly created StartNode
                for node in self.graph.all_nodes():
                    if (
                        isinstance(node, StartNode)
                        and node.id not in nodes_map
                    ):
                        try:
                            db_node = WorkflowNode.objects.create(
                                workflow_id=workflow_id,
                                node_identifier=node.type_,
                                name=node.name(),
                                pos_x=node.pos()[0],
                                pos_y=node.pos()[1],
                                properties=self._extract_node_properties(node),
                            )
                            if db_node:
                                nodes_map[node.id] = db_node.id
                                self.logger.info(
                                    f"Created new StartNode: {node.name()} (Graph ID: {node.id}, DB ID: {db_node.id})"
                                )
                        except Exception as e:
                            self.logger.error(
                                f"Error creating StartNode: {e}", exc_info=True
                            )

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
        """
        Save connections in the graph to the database using CRUD operations.
        Updates existing connections, creates new ones, and removes obsolete ones.
        """
        # Collect all current connections in the graph
        current_connections = []
        all_graph_nodes = self.graph.all_nodes()
        for node in all_graph_nodes:
            for out_port in node.outputs().values():
                for in_port in out_port.connected_ports():
                    current_connections.append(
                        {
                            "out_node_id": node.id,
                            "out_port_name": out_port.name(),
                            "in_node_id": in_port.node().id,
                            "in_port_name": in_port.name(),
                        }
                    )

        self.logger.info(
            f"Processing {len(current_connections)} connections for saving..."
        )

        # Get all existing connections for this workflow from the database
        try:
            existing_connections = WorkflowConnection.objects.filter_by(
                workflow_id=workflow.id
            )
            self.logger.info(
                f"Found {len(existing_connections)} existing connections in the database"
            )
        except Exception as e:
            self.logger.error(
                f"Error retrieving existing connections: {e}", exc_info=True
            )
            existing_connections = []

        # Create a map of existing connections for easier lookup
        existing_conn_map = {}
        for db_conn in existing_connections:
            # Create a key based on the connection endpoints
            if (
                db_conn.output_node_id in nodes_map.values()
                and db_conn.input_node_id in nodes_map.values()
            ):
                # We need to look up the graph node IDs from the DB node IDs using the inverse of nodes_map
                # This is because current_connections uses graph node IDs
                inv_nodes_map = {
                    db_id: graph_id for graph_id, db_id in nodes_map.items()
                }
                key = f"{inv_nodes_map.get(db_conn.output_node_id)}:{db_conn.output_port_name}:{inv_nodes_map.get(db_conn.input_node_id)}:{db_conn.input_port_name}"
                existing_conn_map[key] = db_conn

        # Track connections to keep
        connection_keys_to_keep = set()

        # Process all current connections
        for conn in current_connections:
            # Map the graph node IDs to database node IDs
            if (
                conn["out_node_id"] in nodes_map
                and conn["in_node_id"] in nodes_map
            ):
                output_node_db_id = nodes_map[conn["out_node_id"]]
                input_node_db_id = nodes_map[conn["in_node_id"]]

                # Create a key to check if this connection already exists
                conn_key = f"{conn['out_node_id']}:{conn['out_port_name']}:{conn['in_node_id']}:{conn['in_port_name']}"

                if conn_key in existing_conn_map:
                    # Connection already exists, mark it to keep
                    self.logger.info(
                        f"Connection already exists: {conn['out_port_name']} -> {conn['in_port_name']}"
                    )
                    connection_keys_to_keep.add(conn_key)
                else:
                    # Create new connection
                    try:
                        db_conn = WorkflowConnection.objects.create(
                            workflow_id=workflow.id,
                            output_node_id=output_node_db_id,
                            output_port_name=conn["out_port_name"],
                            input_node_id=input_node_db_id,
                            input_port_name=conn["in_port_name"],
                        )
                        if db_conn:
                            self.logger.info(
                                f"Created new connection: {conn['out_port_name']} -> {conn['in_port_name']}"
                            )
                            # Add this new connection to our tracking
                            new_key = f"{conn['out_node_id']}:{conn['out_port_name']}:{conn['in_node_id']}:{conn['in_port_name']}"
                            connection_keys_to_keep.add(new_key)
                    except Exception as e:
                        self.logger.error(
                            f"Error creating connection: {e}", exc_info=True
                        )
            else:
                self.logger.warning(
                    f"Skipping connection due to missing node DB ID mapping: {conn['out_port_name']} -> {conn['in_port_name']}"
                )

        # Delete connections that are no longer in the graph
        connections_to_delete = [
            db_conn
            for key, db_conn in existing_conn_map.items()
            if key not in connection_keys_to_keep
        ]
        if connections_to_delete:
            try:
                for db_conn in connections_to_delete:
                    WorkflowConnection.objects.delete_by(id=db_conn.id)
                self.logger.info(
                    f"Deleted {len(connections_to_delete)} obsolete connections from the database"
                )
            except Exception as e:
                self.logger.error(
                    f"Error deleting obsolete connections: {e}", exc_info=True
                )

        self.logger.info(
            f"Connection saving complete. {len(current_connections)} processed, {len(connection_keys_to_keep)} kept or created."
        )

    def _perform_load(self, workflow_id: int):
        """Loads a workflow, including variables, from the database."""
        self.logger.info(f"Loading workflow ID '{workflow_id}'...")

        try:
            workflow, db_nodes, db_connections = self._find_workflow_and_data(
                workflow_id=workflow_id
            )
            self.current_workflow_id = workflow_id
        except Exception as e:
            self.logger.warning(e)
            self.current_workflow_id = None
            return

        self._clear_graph(add_start_node=False)
        self.current_workflow_id = workflow_id
        data = dict(
            workflow_id=workflow_id,
            db_nodes=db_nodes,
            db_connections=db_connections,
        )
        self.api.nodegraph.load_workflow(
            workflow=workflow,
            callback=lambda _data=data: self._finalize_load_workflow(_data),
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

    def _clear_graph(self, add_start_node: bool = True):
        self.logger.info("Clearing current graph session and variables...")
        self.api.nodegraph.clear_workflow(
            callback=lambda: self._finalize_clear_graph(add_start_node)
        )

    def _finalize_clear_graph(self, add_start_node: bool = True):
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

        # Automatically add a StartNode to the workflow
        if add_start_node:
            self._add_start_node()

    def _add_start_node(self):
        """Add a StartNode to the workflow at a default position if one doesn't already exist."""
        # Check if there's already a StartNode in the graph
        existing_start_nodes = [
            node
            for node in self.graph.all_nodes()
            if isinstance(node, StartNode)
        ]

        if existing_start_nodes:
            self.logger.info(
                f"StartNode already exists in workflow. Found {len(existing_start_nodes)} StartNode(s)."
            )
            # If multiple StartNodes exist, log a warning but don't add another one
            if len(existing_start_nodes) > 1:
                self.logger.warning(
                    f"Multiple StartNodes detected in workflow: {len(existing_start_nodes)}. Only one StartNode should exist."
                )
            return  # Don't add another StartNode

        # Create a new StartNode at a default position
        start_node = self.graph.create_node(
            "Core.StartNode",
            name="Start Workflow",
            pos=(0, 0),
        )
        if start_node:
            self.logger.info("Added default StartNode to workflow")
        else:
            self.logger.error("Failed to add default StartNode to workflow")

    def _remove_start_node(self):
        """Remove the StartNode from the workflow if it exists."""
        start_nodes = [
            node
            for node in self.graph.all_nodes()
            if isinstance(node, StartNode)
        ]
        for start_node in start_nodes:
            self.graph.delete_node(start_node)
            self.logger.info(f"Removed StartNode: {start_node.name()}")

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
        self._remove_start_node()
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
            if prop_name == "custom":
                for custom_prop_name, custom_prop_value in prop_value.items():
                    self._set_property_on_node(
                        node_instance, custom_prop_name, custom_prop_value
                    )
            else:
                self._set_property_on_node(
                    node_instance, prop_name, prop_value
                )

    def _set_property_on_node(self, node_instance, prop_name, prop_value):
        # Skip ignored properties and dynamic port lists (handled in _load_workflow_nodes)
        if prop_name in IGNORED_NODE_PROPERTIES or prop_name in [
            "id",
        ]:
            self.logger.debug(f"    Skipping property: {prop_name}")
            return

        # Handle color conversion from list back to tuple if needed by NodeGraphQt
        if prop_name == "color" and isinstance(prop_value, list):
            prop_value = tuple(prop_value)

        # Convert dicts to tuples for VECTOR2 properties
        VECTOR2_PROPERTY_NAMES = [
            "crops_coords_top_left",
            "negative_crops_coords_top_left",
            "target_size",
            "original_size",
            "negative_target_size",
            "negative_original_size",
        ]
        if prop_name in VECTOR2_PROPERTY_NAMES and isinstance(
            prop_value, dict
        ):
            # Try x/y first, then width/height for size properties
            if "x" in prop_value and "y" in prop_value:
                prop_value = (prop_value["x"], prop_value["y"])
            elif "width" in prop_value and "height" in prop_value:
                prop_value = (prop_value["width"], prop_value["height"])
            else:
                prop_value = (0, 0)

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
                setattr(node_instance, prop_name, prop_value)
                self.logger.warning(
                    f"    Set attribute directly (use with caution): {prop_name} = {prop_value}"
                )

        except Exception as e:
            self.logger.error(
                f"    Error restoring property '{prop_name}' for node {node_instance.name()}: {e}"
            )

    # --- End Database Interaction ---

    def _on_node_execution_completed(self, data: Dict):
        self.node_graph_worker.add_to_queue(data)
        self.stop_progress_bar()
