from typing import Tuple, Optional, List
from NodeGraphQt import NodesPaletteWidget
from PySide6.QtWidgets import (
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QSplitter,
    QDockWidget,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QMenu,
    QInputDialog,
    QComboBox,
    QListWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import Qt, Slot, QMimeData
from PySide6.QtGui import QDrag


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
    ForEachLoopNode,
    ForLoopNode,
    WhileLoopNode,
    ReverseForEachLoopNode,
    CanvasNode,
    ChatbotNode,
    LoraNode,
    EmbeddingNode,
    LLMBranchNode,
)
from airunner.gui.widgets.nodegraph.nodes.variable_getter_node import (
    VariableGetterNode,
)

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.nodegraph.add_port_dialog import AddPortDialog
from airunner.gui.widgets.nodegraph.custom_node_graph import CustomNodeGraph
from airunner.gui.widgets.nodegraph.templates.node_graph_ui import (
    Ui_node_graph_widget,
)
from airunner.gui.widgets.nodegraph.variable import Variable
from airunner.gui.widgets.nodegraph.variable_types import (
    VariableType,
    get_variable_color,
    get_variable_type_from_string,
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
    # Define a custom MIME type for dragging variables
    VARIABLE_MIME_TYPE = "application/x-airunner-variable"

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize the graph using the custom class
        self.graph = CustomNodeGraph()  # Use CustomNodeGraph
        self.graph.widget_ref = (
            self  # Give graph a reference back to the widget
        )

        # Initialize variables list
        self.variables: list[Variable] = []

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
            ForEachLoopNode,
            ForLoopNode,
            WhileLoopNode,
            ReverseForEachLoopNode,
            CanvasNode,
            ChatbotNode,
            LoraNode,
            EmbeddingNode,
            LLMBranchNode,
        ]:
            self.graph.register_node(node_cls)
        self.graph.register_node(VariableGetterNode)

        self.nodes_palette = NodesPaletteWidget(
            parent=None,
            node_graph=self.graph,
        )

        self.initialize_context_menu()

        # Get the viewer
        self.viewer = self.graph.widget

        self.ui.splitter.setSizes([200, 700, 200])
        self.ui.graph.layout().addWidget(self.viewer)
        self.ui.palette.layout().addWidget(self.nodes_palette)

        # Create and add the variables panel
        self._create_variables_panel()

    # --- Variables Panel ---

    def _create_variables_panel(self):
        variables_widget = QWidget()
        variables_layout = self.ui.variables.layout()

        self.variables_list_widget = QListWidget()
        self.variables_list_widget.setDragEnabled(True)
        self.variables_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.variables_list_widget.customContextMenuRequested.connect(
            self._show_variable_context_menu
        )
        self.variables_list_widget.itemDoubleClicked.connect(
            self._edit_variable_item
        )  # Connect double-click
        # Connect mouse move for drag start
        self.variables_list_widget.startDrag = (
            self._start_variable_drag
        )  # Custom drag start

        self.add_variable_button = QPushButton("Add Variable")
        self.add_variable_button.clicked.connect(self._add_variable)

        variables_layout.addWidget(self.variables_list_widget)
        variables_layout.addWidget(self.add_variable_button)

    def _update_variables_list(self):
        """Updates the QListWidget with the current variables."""
        self.variables_list_widget.clear()
        for var in self.variables:
            item = QListWidgetItem(f"{var.name} ({var.var_type.value})")
            item.setData(
                Qt.UserRole, var.name
            )  # Store variable name in item data
            color = get_variable_color(var.var_type)
            item.setForeground(color)  # Set text color
            # Optionally set an icon color indicator
            # icon = QIcon(...) # Create an icon with the color
            # item.setIcon(icon)
            self.variables_list_widget.addItem(item)

    def _find_variable_by_name(self, name: str) -> Variable | None:
        """Finds a variable object by its name."""
        for var in self.variables:
            if var.name == name:
                return var
        return None

    def _is_variable_name_unique(
        self, name: str, ignore_variable: Variable | None = None
    ) -> bool:
        """Checks if a variable name is unique."""
        for var in self.variables:
            if var.name.lower() == name.lower() and var is not ignore_variable:
                return False
        return True

    @Slot()
    def _add_variable(self):
        """Opens a dialog to add a new variable."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Variable")
        layout = QFormLayout(dialog)

        name_input = QLineEdit(dialog)
        type_combo = QComboBox(dialog)
        type_combo.addItems([vtype.value for vtype in VariableType])

        layout.addRow("Name:", name_input)
        layout.addRow("Type:", type_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            name = name_input.text().strip()
            type_str = type_combo.currentText()
            var_type = get_variable_type_from_string(type_str)

            if not name:
                QMessageBox.warning(
                    self, "Add Variable", "Variable name cannot be empty."
                )
                return
            if not self._is_variable_name_unique(name):
                QMessageBox.warning(
                    self,
                    "Add Variable",
                    f"Variable name '{name}' is already taken.",
                )
                return
            if not var_type:
                QMessageBox.critical(
                    self, "Add Variable", "Invalid variable type selected."
                )  # Should not happen
                return

            # Determine default value based on type (simple defaults)
            default_value = None
            if var_type == VariableType.BOOLEAN:
                default_value = False
            elif var_type in [
                VariableType.BYTE,
                VariableType.INTEGER,
                VariableType.INTEGER64,
            ]:
                default_value = 0
            elif var_type in [VariableType.FLOAT, VariableType.DOUBLE]:
                default_value = 0.0
            elif var_type in [
                VariableType.NAME,
                VariableType.STRING,
                VariableType.TEXT,
            ]:
                default_value = ""
            # Add defaults for Vector, Rotator, Transform etc. if needed

            new_var = Variable(
                name=name, var_type=var_type, default_value=default_value
            )
            self.variables.append(new_var)
            self._update_variables_list()
            self.logger.info(f"Added variable: {name} ({type_str})")

    @Slot(QListWidgetItem)
    def _edit_variable_item(self, item: QListWidgetItem):
        """Handles double-clicking a variable item (currently renames)."""
        var_name = item.data(Qt.UserRole)
        variable = self._find_variable_by_name(var_name)
        if variable:
            self._rename_variable(variable)  # Reuse rename logic for now

    @Slot("QPoint")
    def _show_variable_context_menu(self, pos):
        """Shows the context menu for the variables list."""
        item = self.variables_list_widget.itemAt(pos)
        if not item:
            return

        var_name = item.data(Qt.UserRole)
        variable = self._find_variable_by_name(var_name)
        if not variable:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        change_type_action = menu.addAction("Change Type")
        # set_default_action = menu.addAction("Set Default Value") # TODO
        delete_action = menu.addAction("Delete")

        action = menu.exec(self.variables_list_widget.mapToGlobal(pos))

        if action == rename_action:
            self._rename_variable(variable)
        elif action == change_type_action:
            self._change_variable_type(variable)
        # elif action == set_default_action:
        #     self._set_variable_default(variable) # TODO
        elif action == delete_action:
            self._delete_variable(variable)

    def _rename_variable(self, variable: Variable):
        """Handles renaming a variable."""
        old_name = variable.name
        new_name, ok = QInputDialog.getText(
            self, "Rename Variable", "New name:", QLineEdit.Normal, old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if not self._is_variable_name_unique(
                new_name, ignore_variable=variable
            ):
                QMessageBox.warning(
                    self,
                    "Rename Variable",
                    f"Variable name '{new_name}' is already taken.",
                )
                return

            # TODO: Update nodes using this variable (VariableGetterNode, VariableSetterNode)
            # This requires iterating through graph nodes and checking their variable_name property.
            # For now, just rename the variable object.
            variable.name = new_name
            self._update_variables_list()
            self.logger.info(f"Renamed variable '{old_name}' to '{new_name}'")
        elif ok and not new_name.strip():
            QMessageBox.warning(
                self, "Rename Variable", "Variable name cannot be empty."
            )

    def _change_variable_type(self, variable: Variable):
        """Handles changing the type of a variable."""
        old_type = variable.var_type
        type_names = [vtype.value for vtype in VariableType]
        current_index = (
            type_names.index(old_type.value)
            if old_type.value in type_names
            else 0
        )

        new_type_str, ok = QInputDialog.getItem(
            self,
            "Change Variable Type",
            "New type:",
            type_names,
            current_index,
            False,
        )

        if ok and new_type_str:
            new_type = get_variable_type_from_string(new_type_str)
            if new_type and new_type != old_type:
                # TODO: Add type conversion logic or warning if incompatible
                # For now, just change the type and reset default value
                variable.var_type = new_type
                # Reset default value based on new type
                default_value = None
                if new_type == VariableType.BOOLEAN:
                    default_value = False
                elif new_type in [
                    VariableType.BYTE,
                    VariableType.INTEGER,
                    VariableType.INTEGER64,
                ]:
                    default_value = 0
                elif new_type in [VariableType.FLOAT, VariableType.DOUBLE]:
                    default_value = 0.0
                elif new_type in [
                    VariableType.NAME,
                    VariableType.STRING,
                    VariableType.TEXT,
                ]:
                    default_value = ""
                variable.default_value = default_value

                self._update_variables_list()
                # TODO: Update ports on associated nodes (Getter/Setter)
                self.logger.info(
                    f"Changed type of variable '{variable.name}' from {old_type.value} to {new_type.value}"
                )

    def _delete_variable(self, variable: Variable):
        """Handles deleting a variable."""
        reply = QMessageBox.question(
            self,
            "Delete Variable",
            f"Are you sure you want to delete the variable '{variable.name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # TODO: Find and delete nodes using this variable (Getters/Setters)
            # This requires iterating through the graph.
            # nodes_to_delete = [node for node in self.graph.all_nodes()
            #                    if isinstance(node, (VariableGetterNode, VariableSetterNode)) # Assuming Setter exists
            #                    and node.get_variable_name() == variable.name]
            # for node in nodes_to_delete:
            #     self.graph.delete_node(node, push_undo=False) # Consider undo stack

            self.variables.remove(variable)
            self._update_variables_list()
            self.logger.info(f"Deleted variable: {variable.name}")

    def _start_variable_drag(self, event):
        """Initiates dragging a variable from the list."""
        item = self.variables_list_widget.currentItem()
        if not item:
            return

        var_name = item.data(Qt.UserRole)
        variable = self._find_variable_by_name(var_name)
        if not variable:
            return

        mime_data = QMimeData()
        # Encode variable name into the MIME data
        mime_data.setData(self.VARIABLE_MIME_TYPE, var_name.encode())

        drag = QDrag(self.variables_list_widget)
        drag.setMimeData(mime_data)
        drag.setHotSpot(event.pos())

        # Start the drag operation
        drag.exec(Qt.CopyAction)

    # --- End Variables Panel ---

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
        self.save_workflow(3)

    @Slot()
    def on_load_workflow(self):
        self.load_workflow(3)

    @Slot()
    def on_edit_workflow(self):
        print("TODO: EDIT WORKFLOW")

    @Slot()
    def on_delete_workflow(self):
        print("TODO: DELETE WORKFLOW")

    @Slot()
    def on_clear_workflow(self):
        """Clear the current workflow graph and variables."""
        self._clear_graph_and_variables()
        self.logger.info("Workflow graph and variables cleared.")

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
    def save_workflow(self, workflow_id: int, description: str = ""):
        """Saves the current node graph state, including variables, to the database."""  # Updated docstring
        self.logger.info(f"Saving workflow '{workflow_id}'...")
        workflow = self._find_or_create_workflow(workflow_id, description)
        if not workflow:
            self.logger.error("Failed to create or retrieve workflow.")
            return
        self._save_variables(workflow)
        nodes_map = self._save_nodes(workflow)
        self._save_connections(workflow, nodes_map)
        self.logger.info(f"Workflow '{workflow_id}' saved successfully.")

    def _find_or_create_workflow(
        self,
        workflow_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Workflow]:
        """Find an existing workflow or create a new one."""
        workflow = self._find_workflow_by_id(workflow_id)
        if workflow:
            self._clear_existing_workflow_data(workflow)
        else:
            workflow = self._create_workflow(name, description)
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
        """Clear existing nodes and connections for the workflow."""
        deleted_node_count = WorkflowNode.objects.delete_by(
            workflow_id=workflow.id
        )
        self.logger.info(
            f"Deleted {deleted_node_count} existing nodes (and their connections)."
        )

    def _save_variables(self, workflow: Workflow):
        """Saves the graph variables to the workflow's data."""
        try:
            variables_data = [var.to_dict() for var in self.variables]
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
                properties_to_save[key] = value

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

    def load_workflow(self, workflow_id):
        """Loads a workflow, including variables, from the database."""
        self.logger.info(f"Loading workflow '{workflow_id}'...")

        try:
            workflow, db_nodes, db_connections = self._find_workflow_and_data(
                workflow_id=workflow_id
            )
        except Exception as e:
            self.logger.error(e)
            return

        self._clear_graph_and_variables()
        self._load_variables(workflow)

        if db_nodes is not None:
            node_map = self._load_workflow_nodes(db_nodes)
            self._load_workflow_connections(db_connections, node_map)
            self.logger.info(
                f"Workflow '{workflow.name}' loaded successfully."
            )

    def _clear_graph_and_variables(self):
        self.logger.info("Clearing current graph session and variables...")
        self.graph.clear_session()
        self.variables.clear()
        self._update_variables_list()

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

    def _load_variables(self, workflow: Workflow):
        """Loads variables from the workflow data."""
        if hasattr(workflow, "variables") and workflow.variables:
            try:
                loaded_vars = []
                variables_data = (
                    workflow.variables
                )  # Assuming it's already parsed JSON/dict list
                if isinstance(variables_data, list):
                    for var_data in variables_data:
                        variable = Variable.from_dict(var_data)
                        if variable:
                            loaded_vars.append(variable)
                        else:
                            self.logger.warning(
                                f"Could not deserialize variable data: {var_data}"
                            )
                    self.variables = loaded_vars
                    self._update_variables_list()
                    self.logger.info(
                        f"Loaded {len(self.variables)} variables from workflow ID {workflow.id}"
                    )
                else:
                    self.logger.warning(
                        f"Workflow variables data is not a list: {type(variables_data)}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error loading variables for workflow ID {workflow.id}: {e}"
                )
        else:
            self.logger.info(
                f"Workflow ID {workflow.id} has no variables data to load."
            )

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

        # No need for separate success message here, handled per property
        # self.logger.info(f"  Finished restoring properties for {node_instance.name()}.")

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
            if node_id in executed_nodes:
                continue  # Skip if already processed (e.g., in loops)

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
        self.logger.info(f"Final Node Outputs: {final_outputs}")
