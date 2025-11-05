"""Template Browser Dialog for browsing and selecting workflow templates.

This dialog provides a UI for:
- Browsing workflow templates by category
- Searching templates by name, description, or tags
- Previewing template details
- Creating workflows from templates with custom variables
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QFormLayout,
    QWidget,
    QSplitter,
    QGroupBox,
    QMessageBox,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal

from airunner.components.nodegraph.template_manager import (
    get_template_manager,
    WorkflowTemplate,
)


class TemplateVariablesDialog(QDialog):
    """Dialog for entering variable values when creating workflow from template."""

    def __init__(
        self, template: WorkflowTemplate, parent: Optional[QWidget] = None
    ):
        """Initialize dialog.

        Args:
            template: The workflow template
            parent: Parent widget
        """
        super().__init__(parent)
        self.template = template
        self.variable_inputs: Dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Configure {self.template.name}")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Description
        desc_label = QLabel(self.template.description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Variables form
        if self.template.variables:
            form_layout = QFormLayout()

            for var_name, default_value in self.template.variables.items():
                input_field = QLineEdit(str(default_value))
                self.variable_inputs[var_name] = input_field
                form_layout.addRow(f"{var_name}:", input_field)

            layout.addLayout(form_layout)
        else:
            layout.addWidget(QLabel("No variables to configure"))

        # Workflow name
        self.name_input = QLineEdit(self.template.name)
        name_layout = QFormLayout()
        name_layout.addRow("Workflow Name:", self.name_input)
        layout.addLayout(name_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_workflow_data(self) -> Dict[str, Any]:
        """Get workflow data with user-configured values.

        Returns:
            Dictionary with workflow_name and variables
        """
        variables = {
            name: input_field.text()
            for name, input_field in self.variable_inputs.items()
        }
        return {
            "workflow_name": self.name_input.text().strip(),
            "variables": variables,
        }


class TemplateBrowserDialog(QDialog):
    """Dialog for browsing and selecting workflow templates."""

    # Signal emitted when user wants to create workflow from template
    template_selected = Signal(str, str, dict)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize template browser.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.template_manager = get_template_manager()
        self.current_template: Optional[WorkflowTemplate] = None
        self._setup_ui()
        self._load_templates()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Workflow Template Browser")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Top section: Search and filter
        top_layout = QHBoxLayout()

        # Search field
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by name, description, or tags..."
        )
        self.search_input.textChanged.connect(self._filter_templates)

        # Category filter
        category_label = QLabel("Category:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", None)
        categories = set()
        for template in self.template_manager.list_templates():
            categories.add(template.category)
        for category in sorted(categories):
            self.category_combo.addItem(category.title(), category)
        self.category_combo.currentIndexChanged.connect(self._filter_templates)

        top_layout.addWidget(search_label)
        top_layout.addWidget(self.search_input, 3)
        top_layout.addWidget(category_label)
        top_layout.addWidget(self.category_combo, 1)

        layout.addLayout(top_layout)

        # Main content: Splitter with list and preview
        splitter = QSplitter(Qt.Horizontal)

        # Left: Template list
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(
            self._on_template_selected
        )
        splitter.addWidget(self.template_list)

        # Right: Template preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Template info
        info_group = QGroupBox("Template Information")
        info_layout = QVBoxLayout(info_group)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.name_label)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(100)
        info_layout.addWidget(self.description_text)

        self.metadata_label = QLabel()
        info_layout.addWidget(self.metadata_label)

        preview_layout.addWidget(info_group)

        # Variables
        self.variables_group = QGroupBox("Variables")
        self.variables_layout = QFormLayout(self.variables_group)
        preview_layout.addWidget(self.variables_group)

        # Structure
        structure_group = QGroupBox("Workflow Structure")
        structure_layout = QVBoxLayout(structure_group)
        self.structure_label = QLabel()
        self.structure_label.setWordWrap(True)
        structure_layout.addWidget(self.structure_label)
        preview_layout.addWidget(structure_group)

        preview_layout.addStretch()

        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.create_button = QPushButton("Create Workflow")
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self._on_create_clicked)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)

        button_layout.addWidget(self.create_button)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _load_templates(self):
        """Load all templates into the list."""
        self.template_list.clear()
        templates = self.template_manager.list_templates()

        for template in templates:
            item = QListWidgetItem(template.name)
            item.setData(Qt.UserRole, template)
            self.template_list.addItem(item)

    def _filter_templates(self):
        """Filter templates based on search and category."""
        search_text = self.search_input.text().strip()
        category = self.category_combo.currentData()

        # Get filtered templates
        if search_text:
            templates = self.template_manager.search_templates(
                search_text, category
            )
        elif category:
            templates = self.template_manager.list_by_category(category)
        else:
            templates = self.template_manager.list_templates()

        # Update list
        self.template_list.clear()
        for template in templates:
            item = QListWidgetItem(template.name)
            item.setData(Qt.UserRole, template)
            self.template_list.addItem(item)

    def _on_template_selected(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ):
        """Handle template selection.

        Args:
            current: Currently selected item
            previous: Previously selected item
        """
        if current is None:
            self.current_template = None
            self.create_button.setEnabled(False)
            self._clear_preview()
            return

        template: WorkflowTemplate = current.data(Qt.UserRole)
        self.current_template = template
        self.create_button.setEnabled(True)
        self._update_preview(template)

    def _clear_preview(self):
        """Clear the preview panel."""
        self.name_label.clear()
        self.description_text.clear()
        self.metadata_label.clear()
        self.structure_label.clear()

        # Clear variables
        while self.variables_layout.count():
            child = self.variables_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _update_preview(self, template: WorkflowTemplate):
        """Update preview with template details.

        Args:
            template: The template to preview
        """
        self.name_label.setText(template.name)
        self.description_text.setText(template.description)

        # Metadata
        metadata_parts = []
        if template.author:
            metadata_parts.append(f"Author: {template.author}")
        if template.version:
            metadata_parts.append(f"Version: {template.version}")
        if template.category:
            metadata_parts.append(f"Category: {template.category.title()}")
        if template.tags:
            metadata_parts.append(f"Tags: {', '.join(template.tags)}")
        self.metadata_label.setText(" | ".join(metadata_parts))

        # Variables
        while self.variables_layout.count():
            child = self.variables_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if template.variables:
            for var_name, default_value in template.variables.items():
                label = QLabel(f"{var_name}:")
                value_label = QLabel(f"{default_value}")
                value_label.setStyleSheet("color: #666;")
                self.variables_layout.addRow(label, value_label)
        else:
            self.variables_layout.addRow(QLabel("No variables"))

        # Structure
        node_count = len(template.nodes)
        connection_count = len(template.connections)
        self.structure_label.setText(
            f"{node_count} nodes, {connection_count} connections"
        )

    def _on_create_clicked(self):
        """Handle create workflow button click."""
        if not self.current_template:
            return

        # Show variables dialog if template has variables
        if self.current_template.variables:
            dialog = TemplateVariablesDialog(self.current_template, self)
            if dialog.exec() != QDialog.Accepted:
                return

            data = dialog.get_workflow_data()
            workflow_name = data["workflow_name"]
            variables = data["variables"]
        else:
            # No variables, just ask for name
            workflow_name = self.current_template.name
            variables = {}

        if not workflow_name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Please provide a workflow name.",
            )
            return

        # Emit signal with template name, workflow name, and variables
        self.template_selected.emit(
            self.current_template.name, workflow_name, variables
        )
        self.accept()

    def get_selected_template_data(self) -> Optional[Dict[str, Any]]:
        """Get data for creating workflow from selected template.

        Returns:
            Dictionary with template_name, workflow_name, and variables,
            or None if dialog was cancelled
        """
        if self.result() == QDialog.Accepted and self.current_template:
            # This would be populated by the _on_create_clicked handler
            # For now, return basic data
            return {
                "template_name": self.current_template.name,
                "workflow_name": self.current_template.name,
                "variables": self.current_template.variables or {},
            }
        return None
