import os
import json
import logging
from typing import Dict, Tuple, Optional, List

from networkx.classes import nodes

from airunner.components.nodegraph.gui.widgets.nodes.core.variable_getter_node import (
    VariableGetterNode,
)
from airunner.components.nodegraph.gui.widgets.nodes.io.print import PrintNode
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.vendor.nodegraphqt import NodesPaletteWidget
from PySide6.QtWidgets import (
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Slot
from PySide6 import QtCore

from airunner.enums import SignalCode
from airunner.components.nodegraph.gui.widgets.nodes import (
    AgentActionNode,
    BaseWorkflowNode,
    TextboxNode,
    RandomNumberNode,
    MaxRND,
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
from airunner.vendor.nodegraphqt.widgets.debounced_viewer import (
    DebouncedNodeViewer,
)

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.nodegraph.gui.widgets.add_port_dialog import (
    AddPortDialog,
)
from airunner.components.nodegraph.gui.widgets.custom_node_graph import (
    CustomNodeGraph,
)
from airunner.components.nodegraph.gui.widgets.templates.node_graph_ui import (
    Ui_node_graph_widget,
)

from airunner.components.nodegraph.data.workflow import Workflow
from airunner.components.nodegraph.data.workflow_node import WorkflowNode
from airunner.components.nodegraph.data.workflow_connection import (
    WorkflowConnection,
)
from airunner.utils.settings import get_qsettings

from airunner.components.nodegraph.workers.node_graph_worker import (
    NodeGraphWorker,
)
from airunner.utils.application.create_worker import create_worker

IGNORED_NODE_PROPERTIES = {}


class NodeGraphWidget(BaseWidget):
    widget_class_ = Ui_node_graph_widget
    # Define a custom MIME type for dragging variables
    VARIABLE_MIME_TYPE = "application/x-airunner-variable"

    def __init__(self, parent=None, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL: self._on_node_execution_completed,
            SignalCode.NODEGRAPH_ZOOM: self._on_nodegraph_zoom_changed,
            SignalCode.NODEGRAPH_PAN: self._on_nodegraph_pan_changed,
            SignalCode.WORKFLOW_EXECUTION_COMPLETED_SIGNAL: self._on_workflow_execution_completed,
        }
        self.initialized = False
        self.splitters = ["nodegraph_splitter"]
        super().__init__(*args, **kwargs)
        self.q_settings = get_qsettings()
        self.graph = CustomNodeGraph()
        self.graph.widget_ref = self

        # Replace the default viewer with our debounced viewer
        debounced_viewer = DebouncedNodeViewer(
            undo_stack=self.graph._undo_stack
        )
        # Copy over necessary properties from the original viewer
        original_viewer = self.graph._viewer
        debounced_viewer.set_zoom(
            int(self.application_settings.nodegraph_zoom)
        )
        debounced_viewer.set_pipe_layout(original_viewer.get_pipe_layout())
        debounced_viewer.set_layout_direction(
            original_viewer.get_layout_direction()
        )
        # Replace the viewer in the graph
        self.graph._viewer = debounced_viewer
        # Reconnect all signals from the new viewer to the NodeGraph instance
        self.graph._wire_signals()
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
        else:
            # If no workflow is loaded, start a new workflow with a StartNode
            self._add_start_node()

        # Check if framepack is available
        here = os.path.dirname(__file__)
        if os.path.exists(os.path.join(here, "../../FramePack")):
            from airunner.components.framepack.workers.framepack_worker import (
                FramePackWorker,
            )

            self.framepack_worker = create_worker(FramePackWorker)

        self.stop_progress_bar()

    @property
    def logger(self):
        if not hasattr(self, "_logger") or self._logger is None:
            self._logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value

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
        if not self.api or not hasattr(self.api, "nodegraph"):
            self.logger.warning(
                "NodeGraphWidget: self.api or self.api.nodegraph is missing. Cannot run workflow."
            )
            return
        self.api.nodegraph.run_workflow(self.graph)

    def pause_workflow(self):
        if not self.api or not hasattr(self.api, "nodegraph"):
            self.logger.warning(
                "NodeGraphWidget: self.api or self.api.nodegraph is missing. Cannot pause workflow."
            )
            return
        self.api.nodegraph.pause_workflow(self.graph)

    def stop_workflow(self):
        self.stop_progress_bar()
        if not self.api or not hasattr(self.api, "nodegraph"):
            self.logger.warning(
                "NodeGraphWidget: self.api or self.api.nodegraph is missing. Cannot stop workflow."
            )
            return
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
                        QMessageBox.StandardButton.Yes
                        | QMessageBox.StandardButton.No
                        | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Cancel,
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
            QDialogButtonBox.StandardButton.Open
            | QDialogButtonBox.StandardButton.Cancel,
            dialog,
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
        self._nodes_palette.layout().setContentsMargins(0, 0, 0, 0)
        for node_cls in [
            AgentActionNode,
            TextboxNode,
            RandomNumberNode,
            MaxRND,
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
            PrintNode,
            VariableGetterNode,
        ]:
            self.graph.register_node(node_cls)

    def _register_graph(self):
        if not self.api or not hasattr(self.api, "nodegraph"):
            self.logger.warning(
                "NodeGraphWidget: self.api or self.api.nodegraph is missing. Cannot register graph."
            )
            return
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
        self.ui.nodegraph_splitter.setSizes([200, 700, 200])
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
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            dialog,
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
        # Use get_orm to get a session-bound ORM object for mutation
        workflow = Workflow.objects.get(
            workflow_id, eager_load=["nodes", "connections"]
        )
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

        # Update workflow metadata using the manager's update method
        try:
            Workflow.objects.update(
                workflow_id, name=name, description=description
            )
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
        self._save_connections(workflow_id, nodes_map)

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

    def _save_variables(self, workflow):
        """Saves the graph variables to the workflow's data."""
        try:
            workflow_id = getattr(workflow, "id", None)
            if workflow_id is None:
                self.logger.error(
                    "Workflow object missing 'id' attribute or is detached."
                )
                return
            variables_data = [
                var.to_dict() for var in self.ui.variables.variables
            ]
            self.logger.info(
                f"Data being saved to workflow.variables: {variables_data}"
            )
            Workflow.objects.update(workflow_id, variables=variables_data)
            self.logger.info(
                f"Saved {len(variables_data)} variables to workflow ID {workflow_id}"
            )
        except Exception as e:
            self.logger.error(f"Error saving variables for workflow: {e}")

    def _save_nodes(self, workflow_id: int) -> dict:
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

        # Get all existing nodes for this workflow (returns detached instances)
        try:
            existing_nodes = (
                WorkflowNode.objects.filter_by(workflow_id=workflow_id) or []
            )
            existing_node_map = {}
            for db_node in existing_nodes:
                key = f"{db_node.node_identifier}_{db_node.pos_x}_{db_node.pos_y}"
                existing_node_map[key] = db_node.id  # Only store the id!
            self.logger.info(
                f"Found {len(existing_node_map)} existing nodes in the database"
            )
        except Exception as e:
            self.logger.error(
                f"Error retrieving existing nodes: {e}", exc_info=True
            )
            existing_node_map = {}

        used_db_node_ids = set()

        for node in all_graph_nodes:
            properties_to_save = self._extract_node_properties(node)
            node_key = f"{node.type_}_{node.pos()[0]}_{node.pos()[1]}"
            db_node_id = existing_node_map.get(node_key)

            if db_node_id:
                # Update using the manager method
                try:
                    WorkflowNode.objects.update(
                        db_node_id,
                        name=node.name(),
                        pos_x=node.pos()[0],
                        pos_y=node.pos()[1],
                        properties=properties_to_save,
                    )
                    nodes_map[node.id] = db_node_id
                    used_db_node_ids.add(db_node_id)
                    self.logger.info(
                        f"Updated node: {node.name()} (Graph ID: {node.id}, DB ID: {db_node_id})"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error updating node {node.name()}: {e}",
                        exc_info=True,
                    )
            else:
                # Create new node and use the returned dataclass
                try:
                    db_node = WorkflowNode.objects.create(
                        workflow_id=workflow_id,
                        node_identifier=node.type_,
                        name=node.name(),
                        pos_x=node.pos()[0],
                        pos_y=node.pos()[1],
                        properties=properties_to_save,
                    )
                    if db_node and hasattr(db_node, "id"):
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
                    WorkflowNode.objects.delete(node_id)
                self.logger.info(
                    f"Deleted {len(nodes_to_delete)} obsolete nodes from the database"
                )
            except Exception as e:
                self.logger.error(
                    f"Error deleting obsolete nodes: {e}", exc_info=True
                )

        return nodes_map

    def _extract_node_properties(self, node):
        """Extract and filter properties of a node for saving."""
        properties_to_save = {}

        # Debug: Check model._custom_prop directly FIRST
        if hasattr(node, "model") and hasattr(node.model, "_custom_prop"):
            custom_prop_dict = node.model._custom_prop
            self.logger.info(
                f"[DEBUG] Node {node.name()} model._custom_prop has {len(custom_prop_dict)} properties"
            )
            if custom_prop_dict and node.type_ == "Art.ImageRequestNode":
                # Show first few properties for ImageRequestNode
                sample_keys = list(custom_prop_dict.keys())[:5]
                self.logger.info(
                    f"[DEBUG] Sample custom property keys: {sample_keys}"
                )
                if "clip_skip" in custom_prop_dict:
                    self.logger.info(
                        f"[DEBUG] clip_skip value in model: {custom_prop_dict['clip_skip']}"
                    )

        raw_properties = node.properties()

        # Debug logging
        self.logger.info(
            f"[DEBUG] Extracting properties for node {node.name()} (type: {node.type_})"
        )
        self.logger.info(
            f"[DEBUG] Raw properties keys: {list(raw_properties.keys())}"
        )
        if "custom" in raw_properties:
            custom_dict = raw_properties["custom"]
            self.logger.info(
                f"[DEBUG] Custom properties dict has {len(custom_dict)} items"
            )
            if (
                node.type_ == "Art.ImageRequestNode"
                and "clip_skip" in custom_dict
            ):
                self.logger.info(
                    f"[DEBUG] clip_skip in raw_properties['custom']: {custom_dict['clip_skip']}"
                )
        else:
            self.logger.info(
                f"[DEBUG] NO 'custom' key found in raw properties!"
            )

        for key, value in raw_properties.items():
            if key not in IGNORED_NODE_PROPERTIES:
                # Skip internal properties that reference the node itself or other non-serializable objects
                if key == "_graph_item" or key.startswith("__"):
                    self.logger.info(
                        f"  Skipping non-serializable property: {key}"
                    )
                    continue

                # Special handling for 'custom' dict - convert enums to their values
                if key == "custom" and isinstance(value, dict):
                    serializable_custom = {}
                    for custom_key, custom_value in value.items():
                        # Convert enums to their values
                        if hasattr(custom_value, "value"):
                            serializable_custom[custom_key] = (
                                custom_value.value
                            )
                        elif hasattr(custom_value, "name"):
                            serializable_custom[custom_key] = custom_value.name
                        else:
                            serializable_custom[custom_key] = custom_value

                    try:
                        json.dumps(serializable_custom)
                        properties_to_save[key] = serializable_custom
                        self.logger.info(
                            f"  [CUSTOM] Saved {len(serializable_custom)} custom properties with enum conversion"
                        )
                    except (TypeError, OverflowError) as e:
                        self.logger.warning(
                            f"  Custom properties still not serializable after enum conversion: {e}"
                        )
                    continue

                # Try to filter out other non-serializable values
                try:
                    # Quick test for JSON serializability
                    json.dumps(value)
                    properties_to_save[key] = value
                except (TypeError, OverflowError):
                    self.logger.info(
                        f"  Skipping non-serializable property: {key} with type {type(value).__name__}"
                    )
                    continue

        # CRITICAL FIX: Ensure custom properties are explicitly included
        # If the raw_properties dict doesn't have 'custom' but the model does have _custom_prop,
        # manually add it to properties_to_save
        if (
            "custom" not in properties_to_save
            and hasattr(node, "model")
            and hasattr(node.model, "_custom_prop")
        ):
            custom_props = node.model._custom_prop
            if custom_props:
                # Convert enums to their values before serialization
                serializable_custom = {}
                for custom_key, custom_value in custom_props.items():
                    if hasattr(custom_value, "value"):
                        serializable_custom[custom_key] = custom_value.value
                    elif hasattr(custom_value, "name"):
                        serializable_custom[custom_key] = custom_value.name
                    else:
                        serializable_custom[custom_key] = custom_value

                try:
                    # Verify it's JSON serializable
                    json.dumps(serializable_custom)
                    properties_to_save["custom"] = serializable_custom
                    self.logger.info(
                        f"  [FIX] Manually added {len(serializable_custom)} custom properties (fallback)"
                    )
                except (TypeError, OverflowError) as e:
                    self.logger.warning(
                        f"  Custom properties not JSON serializable even after conversion: {e}"
                    )

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

    def _save_connections(self, workflow_id: int, nodes_map: dict):
        """
        Save connections in the graph to the database using CRUD operations.
        Updates existing connections, creates new ones, and removes obsolete ones.
        Accepts either a workflow object (with .id) or an int workflow_id.
        """
        if not workflow_id:
            raise ValueError(
                "Workflow ID must be provided to save connections."
            )
        self.logger.info(f"[DEBUG] nodes_map at connection save: {nodes_map}")
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
        # DEBUG: Log all connections being saved
        self.logger.info(
            f"[DEBUG] Connections to be saved: {json.dumps(current_connections, indent=2)}"
        )

        self.logger.info(
            f"Processing {len(current_connections)} connections for saving..."
        )

        # Always extract workflow_id at the start to avoid DetachedInstanceError
        if workflow_id is None:
            self.logger.error(
                "Workflow object missing 'id' attribute or is detached."
            )
            return

        # Get all existing connections for this workflow from the database
        try:
            existing_connections = WorkflowConnection.objects.filter_by(
                workflow_id=workflow_id
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
                            workflow_id=workflow_id,
                            output_node_id=output_node_db_id,
                            output_port_name=conn["out_port_name"],
                            input_node_id=input_node_db_id,
                            input_port_name=conn["in_port_name"],
                        )
                        self.logger.info(
                            f"[DEBUG] Created connection in DB: output_node_id={output_node_db_id}, output_port_name={conn['out_port_name']}, input_node_id={input_node_db_id}, input_port_name={conn['in_port_name']}, db_conn={db_conn}"
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
                    f"[DEBUG] Skipping connection due to missing node DB ID mapping: out_node_id={conn['out_node_id']} in_node_id={conn['in_node_id']} out_port={conn['out_port_name']} in_port={conn['in_port_name']}"
                )

        # Delete connections that are no longer in the graph
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
            workflow=workflow,  # Ensure workflow is included for downstream use
        )
        if not self.api or not hasattr(self.api, "nodegraph"):
            self.logger.warning(
                "NodeGraphWidget: self.api or self.api.nodegraph is missing. Cannot load workflow."
            )
            self._finalize_load_workflow(data)
            return
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
            if not node_map:
                self.logger.warning(
                    "No nodes were loaded for this workflow. The node_map is empty."
                )
            else:
                # Center the view on the loaded nodes and reset zoom
                self._center_view_on_nodes(list(node_map.values()))
                self._reset_zoom_level()
            self.logger.info(
                f"Workflow '{workflow.name if workflow else ''}' loaded successfully."
            )
        else:
            self.logger.warning("No db_nodes found in workflow data.")
        self._restore_nodegraph_state()

    def _clear_graph(self, add_start_node: bool = True):
        self.logger.info("Clearing current graph session and variables...")
        if not self.api or not hasattr(self.api, "nodegraph"):
            self.logger.warning(
                "NodeGraphWidget: self.api or self.api.nodegraph is missing. Cannot clear workflow."
            )
            self._finalize_clear_graph(add_start_node)
            return
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
        self.logger.info(
            f"[DEBUG] Connections loaded from DB: {[{'output_node_id': c.output_node_id, 'output_port_name': c.output_port_name, 'input_node_id': c.input_node_id, 'input_port_name': c.input_port_name} for c in db_connections]}"
        )
        connections_loaded = 0
        for db_conn in db_connections:
            try:
                output_node = node_map.get(db_conn.output_node_id)
                input_node = node_map.get(db_conn.input_node_id)

                self.logger.info(
                    f"[DEBUG] Attempting to connect: {getattr(output_node, 'name', lambda: '?')()} ({db_conn.output_node_id}).{db_conn.output_port_name} -> {getattr(input_node, 'name', lambda: '?')()} ({db_conn.input_node_id}).{db_conn.input_port_name}"
                )

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
                            f"  Skipping connection: Port not found. Output: '{db_conn.output_port_name}' on {output_node.name() if output_node else '?'}; Input: '{db_conn.input_port_name}' on {input_node.name() if input_node else '?'}"
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
                # Restore widget_type enums in properties before restoring them
                properties = self._restore_widget_type_enums(
                    db_node.properties or {}
                )
                # Create the node instance using its identifier and saved position
                node_instance = self.graph.create_node(
                    db_node.node_identifier,
                    name=db_node.name,
                    pos=(db_node.pos_x, db_node.pos_y),
                    push_undo=False,
                )
                if node_instance:
                    node_map[db_node.id] = node_instance
                    # Restore properties (for any additional/late properties)
                    self._restore_node_properties(node_instance, properties)
                else:
                    self.logger.warning(
                        f"Failed to create node for identifier {db_node.node_identifier}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error loading node {getattr(db_node, 'name', '?')}: {e}",
                    exc_info=True,
                )

        self.graph.undo_stack().clear()  # Clear undo stack after loading
        self.logger.info(
            f"Finished loading nodes. Total loaded: {len(node_map)}/{len(db_nodes)}"
        )
        return node_map

    def _center_view_on_nodes(self, node_instances):
        """Center the nodegraph view on the loaded nodes."""
        if not node_instances:
            return
        positions = [
            node.pos() for node in node_instances if hasattr(node, "pos")
        ]
        if not positions:
            return
        min_x = min(pos[0] for pos in positions)
        max_x = max(pos[0] for pos in positions)
        min_y = min(pos[1] for pos in positions)
        max_y = max(pos[1] for pos in positions)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        if hasattr(self.viewer, "centerOn"):
            self.viewer.centerOn(center_x, center_y)
        elif hasattr(self.viewer, "setSceneRect"):
            # Fallback: set scene rect to fit all nodes
            self.viewer.setSceneRect(
                min_x, min_y, max_x - min_x + 1, max_y - min_y + 1
            )

    def _reset_zoom_level(self):
        """Reset the nodegraph view zoom to default (100%)."""
        if hasattr(self.viewer, "set_zoom"):
            self.viewer.set_zoom(1.0)
        elif hasattr(self.viewer, "resetTransform"):
            self.viewer.resetTransform()

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
        # Handle widget_type Enum restoration
        if prop_name == "widget_type" and isinstance(prop_value, int):
            try:
                from airunner.vendor.nodegraphqt.constants import (
                    NodePropWidgetEnum,
                )

                prop_value = NodePropWidgetEnum(prop_value)
            except Exception as e:
                self.logger.warning(
                    f"Failed to restore NodePropWidgetEnum for value {prop_value}: {e}"
                )

        # Skip ignored properties and dynamic port lists (handled in _load_workflow_nodes)
        if prop_name in IGNORED_NODE_PROPERTIES or prop_name in [
            "id",
        ]:
            self.logger.debug(f"    Skipping property: {prop_name}")
            return

        # Handle color conversion from list back to tuple if needed by airunner.vendor.nodegraphqt
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
            # Use airunner.vendor.nodegraphqt's property system primarily
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

    def _restore_widget_type_enums(self, properties):
        """Recursively convert all 'widget_type' int values to NodePropWidgetEnum in a dict or list."""
        from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum

        if isinstance(properties, dict):
            for k, v in properties.items():
                if k == "widget_type" and isinstance(v, int):
                    properties[k] = NodePropWidgetEnum(v)
                else:
                    properties[k] = self._restore_widget_type_enums(v)
            return properties
        elif isinstance(properties, list):
            return [
                self._restore_widget_type_enums(item) for item in properties
            ]
        else:
            return properties

    # --- End Database Interaction ---

    def _on_node_execution_completed(self, data: Dict):
        self.node_graph_worker.add_to_queue(data)
        self.stop_progress_bar()

    def _on_nodegraph_zoom_changed(self, data: Dict):
        """Signal handler for NODEGRAPH_ZOOM signal."""
        # zoom = data.get("zoom_level", 0)
        # # Get the center directly from the signal data if available, or use current viewer center
        # if "center_x" in data and "center_y" in data:
        #     try:
        #         center_x = int(data.get("center_x", 0) or 0)
        #         center_y = int(data.get("center_y", 0) or 0)
        #     except (TypeError, ValueError):
        #         center_x = 0
        #         center_y = 0
        # else:
        #     # If no center data in signal, don't update center values
        #     settings = self.application_settings
        #     try:
        #         center_x = int(getattr(settings, "nodegraph_center_x", 0) or 0)
        #         center_y = int(getattr(settings, "nodegraph_center_y", 0) or 0)
        #     except (TypeError, ValueError):
        #         center_x = 0
        #         center_y = 0

        self._save_state()

    def _on_workflow_execution_completed(self, data: Dict):
        """Signal handler for WORKFLOW_EXECUTION_COMPLETED signal."""
        self.node_graph_worker.add_to_queue(data)
        self.stop_progress_bar()

    def _on_nodegraph_pan_changed(self, data: Dict):
        """Signal handler for NODEGRAPH_PAN signal."""
        try:
            center_x = int(data.get("center_x", 0) or 0)
            center_y = int(data.get("center_y", 0) or 0)
        except (TypeError, ValueError):
            center_x = 0
            center_y = 0

        # Get current zoom since we're only updating center
        try:
            zoom = int(self.application_settings.nodegraph_zoom)
        except (TypeError, ValueError):
            zoom = 0

        self._save_state()

    def closeEvent(self, event):
        self._save_state()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.initialized:
            self.initialized = True
            # Delay restore_state to ensure UI is fully constructed and visible
            QtCore.QTimer.singleShot(0, self.restore_state)

    def _save_state(self):
        viewer = getattr(self.graph, "_viewer", None)
        # Save the actual scale (visual zoom) using get_zoom()
        zoom_scale = viewer.get_zoom() if viewer else 1.0
        canvas_offset = viewer.pan if viewer else (0, 0)
        center_x = canvas_offset[0]
        center_y = canvas_offset[1]
        application_settings = self.application_settings
        ApplicationSettings.objects.update(
            pk=application_settings.id,
            nodegraph_zoom=zoom_scale,
            nodegraph_center_x=center_x,
            nodegraph_center_y=center_y,
        )

    def _restore_nodegraph_state(self):
        if self.initialized:
            return
        self.initialized = True
        """Restore nodegraph zoom and pan (center) from workflow or ApplicationSettings after workflow load."""
        zoom = None
        center_x = None
        center_y = None
        workflow = None
        try:
            if self.current_workflow_id is not None:
                workflow = self._find_workflow_by_id(
                    int(self.current_workflow_id)
                )
                if hasattr(workflow, "nodegraph_zoom"):
                    zoom = getattr(workflow, "nodegraph_zoom", None)
                if hasattr(workflow, "nodegraph_center_x"):
                    center_x = getattr(workflow, "nodegraph_center_x", None)
                if hasattr(workflow, "nodegraph_center_y"):
                    center_y = getattr(workflow, "nodegraph_center_y", None)
        except Exception as e:
            self.logger.warning(
                f"Could not fetch nodegraph zoom/center from workflow: {e}"
            )
        # Fallback to ApplicationSettings if not found in workflow
        if zoom is None:
            zoom = getattr(self.application_settings, "nodegraph_zoom", None)
        if center_x is None:
            center_x = getattr(
                self.application_settings, "nodegraph_center_x", None
            )
        if center_y is None:
            center_y = getattr(
                self.application_settings, "nodegraph_center_y", None
            )
        viewer = getattr(self.graph, "_viewer", None)
        if viewer:
            try:
                # Always reset zoom to identity before applying saved zoom
                if hasattr(viewer, "reset_zoom"):
                    viewer.reset_zoom()
                # Set zoom and center immediately
                if zoom is not None and hasattr(viewer, "set_zoom_absolute"):
                    viewer.set_zoom_absolute(float(zoom))
                if (
                    center_x is not None
                    and center_y is not None
                    and hasattr(viewer, "centerOn")
                ):
                    viewer.centerOn(float(center_x), float(center_y))

                # Schedule a delayed re-application to override late events
                def force_zoom_final():
                    try:
                        if zoom is not None and hasattr(
                            viewer, "set_zoom_absolute"
                        ):
                            viewer.set_zoom_absolute(float(zoom))
                        if (
                            center_x is not None
                            and center_y is not None
                            and hasattr(viewer, "centerOn")
                        ):
                            viewer.centerOn(float(center_x), float(center_y))
                    except Exception as e:
                        self.logger.warning(
                            f"Delayed restore of nodegraph zoom/center failed: {e}"
                        )

                if zoom is not None or (
                    center_x is not None and center_y is not None
                ):
                    QtCore.QTimer.singleShot(1000, force_zoom_final)
            except Exception as e:
                self.logger.warning(
                    f"Failed to restore nodegraph zoom/center: {e}"
                )
