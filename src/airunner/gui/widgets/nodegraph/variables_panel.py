from typing import Dict
from PySide6.QtWidgets import (
    QLineEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QMenu,
    QInputDialog,
    QComboBox,
    QListWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import Qt, Slot

from airunner.enums import SignalCode
from airunner.gui.widgets.nodegraph.nodes.core.variable_getter_node import (
    VariableGetterNode,
)

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.nodegraph.variable import Variable
from airunner.gui.widgets.nodegraph.nodes.core.variable_types import (
    VariableType,
    get_variable_color,
    get_variable_type_from_string,
)

from airunner.gui.widgets.nodegraph.templates.variables_panel_ui import (
    Ui_variables_panel,
)


class VariablesPanelWidget(BaseWidget):
    widget_class_ = Ui_variables_panel

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.CLEAR_WORKFLOW_SIGNAL: self.on_clear_workflow,
            SignalCode.WORKFLOW_LOAD_SIGNAL: self._load_variables,
            SignalCode.REGISTER_GRAPH_SIGNAL: self._register_graph,
        }
        super().__init__(*args, **kwargs)
        self.graph = None
        self.variables: list[Variable] = []
        self._registered_variable_node_classes = {}
        self.ui.variables_list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.ui.variables_list_widget.customContextMenuRequested.connect(
            self._show_variable_context_menu
        )
        self.ui.variables_list_widget.itemDoubleClicked.connect(
            self._edit_variable_item
        )
        self.ui.variables_list_widget.startDrag = self._start_variable_drag

    @Slot()
    def on_add_variable_button_clicked(self):
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

            # Register the variable node for dragging from node palette
            self._register_variable_node(new_var)

            self._update_variables_list()
            self.logger.info(f"Added variable: {name} ({type_str})")

    @Slot("QPoint")
    def _show_variable_context_menu(self, pos):
        """Shows the context menu for the variables list."""
        item = self.ui.variables_list_widget.itemAt(pos)
        if not item:
            return

        var_name = item.data(Qt.UserRole)
        variable = self._find_variable_by_name(var_name)
        if not variable:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        change_type_action = menu.addAction("Change Type")
        set_value_action = menu.addAction(
            "Set Value"
        )  # Add Set Value menu item
        delete_action = menu.addAction("Delete")

        action = menu.exec(self.ui.variables_list_widget.mapToGlobal(pos))

        if action == rename_action:
            self._rename_variable(variable)
        elif action == change_type_action:
            self._change_variable_type(variable)
        elif action == set_value_action:
            self._set_variable_value(variable)  # Call new method to set value
        elif action == delete_action:
            self._delete_variable(variable)

    @Slot(QListWidgetItem)
    def _edit_variable_item(self, item: QListWidgetItem):
        """Handles double-clicking a variable item (currently renames)."""
        var_name = item.data(Qt.UserRole)
        variable = self._find_variable_by_name(var_name)
        if variable:
            self._rename_variable(variable)  # Reuse rename logic for now

    def on_clear_workflow(self, data: Dict):
        self.logger.info("Clearing current variables...")
        callback = data.get("callback")
        self._unregister_all_variable_nodes()
        # Clear the local variable list
        self.variables.clear()
        self._update_variables_list()
        callback()

    def _start_variable_drag(self, event):
        """
        This method is now simplified because we're using the standard node palette
        drag-and-drop system instead of a custom implementation.

        Variables are registered as node classes in the graph, so they can be
        dragged from the node palette just like any other node.
        """

    def _update_variables_list(self):
        """Updates the QListWidget with the current variables."""
        self.ui.variables_list_widget.clear()
        for var in self.variables:
            item = QListWidgetItem(f"{var.name} ({var.var_type.value})")
            item.setData(
                Qt.UserRole, var.name
            )  # Store variable name in item data
            color = get_variable_color(var.var_type)
            item.setForeground(color)
            self.ui.variables_list_widget.addItem(item)

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

            # Unregister the old variable node class
            self._unregister_variable_node(old_name)

            # Update variable name
            variable.name = new_name

            # Register the new variable node class
            self._register_variable_node(variable)

            # Update existing variable getter nodes in the graph
            for node in self.graph.all_nodes():
                if (
                    isinstance(node, VariableGetterNode)
                    and node.variable_name == old_name
                ):
                    node.set_variable(new_name, variable.var_type)

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
                # Unregister the old variable node class
                self._unregister_variable_node(variable.name)

                # Update variable type
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

                # Register the updated variable node class
                self._register_variable_node(variable)

                # Update existing variable getter nodes in the graph
                for node in self.graph.all_nodes():
                    if (
                        isinstance(node, VariableGetterNode)
                        and node.variable_name == variable.name
                    ):
                        node.set_variable(variable.name, new_type)

                self._update_variables_list()
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
            # Find and delete nodes using this variable (VariableGetterNodes)
            nodes_to_delete = []
            for node in self.graph.all_nodes():
                if (
                    isinstance(node, VariableGetterNode)
                    and node.variable_name == variable.name
                ):
                    nodes_to_delete.append(node)

            # Delete matching nodes from the graph
            for node in nodes_to_delete:
                self.graph.delete_node(node, push_undo=True)

            # Unregister the variable node class
            self._unregister_variable_node(variable.name)

            # Remove the variable from our list
            self.variables.remove(variable)
            self._update_variables_list()
            self.logger.info(f"Deleted variable: {variable.name}")

    def _register_variable_node(self, variable: Variable):
        """
        Dynamically register a VariableGetterNode class for a specific variable.
        This makes the variable available in the node palette for drag and drop.

        Args:
            variable: The variable to create a node class for
        """
        from airunner.gui.widgets.nodegraph.nodes.core.variable_getter_node import (
            create_variable_getter_node_class,
        )

        # Create a custom VariableGetterNode class for this variable
        var_node_class = create_variable_getter_node_class(
            variable.name, variable.var_type
        )

        # Get the identifier for the node class
        identifier = var_node_class.__identifier__

        # Always remove from node factory registry before registering, even if not in registered_variable_node_classes
        if hasattr(self.graph, "_node_factory") and hasattr(
            self.graph._node_factory, "_nodes"
        ):
            if identifier in self.graph._node_factory._nodes:
                del self.graph._node_factory._nodes[identifier]
                self.logger.info(
                    f"Removed existing node class '{identifier}' from factory registry before registering."
                )

        # Skip if already registered in our tracking dict
        if variable.name in self._registered_variable_node_classes:
            self.logger.info(
                f"Variable node for '{variable.name}' already in tracking dict. Updating."
            )
            # We still need to update our tracking dict
            self._registered_variable_node_classes[variable.name] = (
                var_node_class
            )

        # Register the node class with the graph
        self.graph.register_node(var_node_class)

        # Store the class for later unregistering
        self._registered_variable_node_classes[variable.name] = var_node_class

        # Update the node palette to include the new variable node
        self.nodes_palette.update()

        self.logger.info(
            f"Registered variable node class for '{variable.name}'"
        )

    def _unregister_variable_node(self, variable_name: str):
        """
        Unregister a variable node class from the graph and palette.

        Args:
            variable_name: The name of the variable whose node class should be unregistered
        """
        if variable_name not in self._registered_variable_node_classes:
            self.logger.info(
                f"No registered variable node found for '{variable_name}'"
            )
            return

        # Get the node class
        var_node_class = self._registered_variable_node_classes[variable_name]

        # Unregister the node class - handle different NodeGraph implementations
        # Some versions might have unregister_node, others might not
        if hasattr(self.graph, "unregister_node") and callable(
            getattr(self.graph, "unregister_node")
        ):
            self.graph.unregister_node(var_node_class)
        else:
            # Fallback approach: if we can't unregister directly, we can still remove from the node palette
            # and update our internal registry
            self.logger.info(
                f"Graph does not have unregister_node method, using fallback approach"
            )

            # If the graph's node factory has a node registry we can clear from there
            if hasattr(self.graph, "_node_factory") and hasattr(
                self.graph._node_factory, "_nodes"
            ):
                # Find and remove the class from the node factory registry
                identifier = var_node_class.__identifier__
                if identifier in self.graph._node_factory._nodes:
                    del self.graph._node_factory._nodes[identifier]
                    self.logger.info(
                        f"Removed node class '{identifier}' from factory registry"
                    )

        # Remove from our registry
        del self._registered_variable_node_classes[variable_name]

        # Update the palette to remove the node
        self.nodes_palette.update()

        self.logger.info(
            f"Unregistered variable node class for '{variable_name}'"
        )

    def _set_variable_value(self, variable: Variable):
        """Handles setting a variable's value via a dialog."""
        from PySide6.QtWidgets import (
            QDialog,
            QFormLayout,
            QDialogButtonBox,
            QLineEdit,
            QSpinBox,
            QDoubleSpinBox,
            QCheckBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set Value for '{variable.name}'")
        layout = QFormLayout(dialog)

        # Create appropriate input widget based on variable type
        if variable.var_type == VariableType.BOOLEAN:
            value_input = QCheckBox(dialog)
            value_input.setChecked(bool(variable.get_value()))
            get_value = lambda: value_input.isChecked()
        elif variable.var_type in [
            VariableType.BYTE,
            VariableType.INTEGER,
            VariableType.INTEGER64,
        ]:
            value_input = QSpinBox(dialog)
            value_input.setRange(-1000000, 1000000)  # Set a reasonable range
            current_val = variable.get_value()
            value_input.setValue(
                int(current_val) if current_val is not None else 0
            )
            get_value = lambda: value_input.value()
        elif variable.var_type in [VariableType.FLOAT, VariableType.DOUBLE]:
            value_input = QDoubleSpinBox(dialog)
            value_input.setRange(-1000000, 1000000)  # Set a reasonable range
            value_input.setDecimals(6)  # Allow for precision
            current_val = variable.get_value()
            value_input.setValue(
                float(current_val) if current_val is not None else 0.0
            )
            get_value = lambda: value_input.value()
        else:  # Default to string input for other types
            value_input = QLineEdit(dialog)
            current_val = variable.get_value()
            value_input.setText(
                str(current_val) if current_val is not None else ""
            )
            get_value = lambda: value_input.text()

        layout.addRow(f"Value ({variable.var_type.value}):", value_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec():
            # Get the value from the input widget
            new_value = get_value()

            # Set the variable value
            variable.set_value(new_value)

            # Update all VariableGetterNodes using this variable
            for node in self.graph.all_nodes():
                if (
                    isinstance(node, VariableGetterNode)
                    and node.variable_name == variable.name
                ):
                    node.set_property(node.value_property_name, new_value)
                    node.update()  # Force visual update

            # Ensure the variable in self.variables is updated
            for v in self.variables:
                if v.name == variable.name:
                    v.set_value(new_value)

            self.logger.info(
                f"Set value of variable '{variable.name}' to: {new_value}"
            )
            return True

        return False

    def _load_variables(self, data: Dict):
        """Loads variables from the workflow data."""
        workflow = data.get("workflow")
        callback = data.get("callback")
        # First unregister any existing variable nodes
        self._unregister_all_variable_nodes()

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

                    # Register node classes for all loaded variables
                    self._register_all_variable_nodes()

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
        callback()

    def _register_graph(self, data: Dict):
        """Handles graph registration."""
        self.nodes_palette = data.get("nodes_palette")
        self.graph = data.get("graph")
        self.graph.widget_ref = self
        callback = data.get("callback")
        callback()

    def _register_all_variable_nodes(self):
        """
        Register node classes for all variables in the variables list.
        Call this after loading variables from a workflow.
        """
        for variable in self.variables:
            self._register_variable_node(variable)

    def _unregister_all_variable_nodes(self):
        """
        Unregister all variable node classes.
        Call this before clearing the variables list.
        """
        for variable_name in list(
            self._registered_variable_node_classes.keys()
        ):
            self._unregister_variable_node(variable_name)
