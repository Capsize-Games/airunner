"""
LLM Tool Manager Widget

Provides a UI for viewing, creating, editing, and managing LLM tools.
Displays all tools (built-in and custom) in a table with CRUD operations.
"""

from typing import Dict

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QTableWidgetItem,
    QMessageBox,
    QPushButton,
    QCheckBox,
)

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.gui.widgets.templates.llm_tool_manager_ui import (
    Ui_llm_tool_manager,
)
from airunner.components.llm.gui.widgets.llm_tool_editor_widget import (
    LLMToolEditorWidget,
)
from airunner.components.llm.data.llm_tool import LLMTool
from airunner.enums import SignalCode
from airunner.components.data.session_manager import session_scope




class LLMToolManagerWidget(BaseWidget):
    """
    Widget for managing LLM tools.
    Shows a table of all tools with ability to create, edit, delete, and toggle.
    """

    widget_class_ = Ui_llm_tool_manager

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LLM_TOOL_CREATED: self.on_tool_created,
            SignalCode.LLM_TOOL_UPDATED: self.on_tool_updated,
            SignalCode.LLM_TOOL_DELETED: self.on_tool_deleted,
            SignalCode.LLM_TOOLS_RELOAD_REQUESTED: self.load_tools,
        }
        super().__init__(*args, **kwargs)

    def initialize_form(self):
        """Initialize the tool manager UI"""
        self.ui.create_tool_button.clicked.connect(self.on_create_tool_clicked)
        self.ui.reload_tools_button.clicked.connect(
            self.on_reload_tools_clicked
        )
        self.ui.search_input.textChanged.connect(self.on_search_changed)
        self.ui.tools_table.setColumnCount(7)
        self.ui.tools_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Description",
                "Created By",
                "Version",
                "Success Rate",
                "Enabled",
                "Actions",
            ]
        )
        self.ui.tools_table.horizontalHeader().setStretchLastSection(False)
        self.ui.tools_table.horizontalHeader().setSectionResizeMode(
            1, self.ui.tools_table.horizontalHeader().ResizeMode.Stretch
        )
        self.load_tools()

    @Slot()
    def on_create_tool_clicked(self):
        """Open editor dialog to create a new tool"""
        editor = LLMToolEditorWidget(parent=self)
        if editor.exec():
            self.load_tools()

    @Slot()
    def on_reload_tools_clicked(self):
        """Reload tools from database"""
        self.load_tools()
        self.emit_signal(SignalCode.LLM_TOOLS_RELOAD_REQUESTED)

    @Slot(str)
    def on_search_changed(self, text: str):
        """Filter tools based on search text"""
        for row in range(self.ui.tools_table.rowCount()):
            name_item = self.ui.tools_table.item(row, 0)
            desc_item = self.ui.tools_table.item(row, 1)
            name_match = (
                text.lower() in name_item.text().lower()
                if name_item
                else False
            )
            desc_match = (
                text.lower() in desc_item.text().lower()
                if desc_item
                else False
            )
            self.ui.tools_table.setRowHidden(
                row, not (name_match or desc_match)
            )

    def load_tools(self):
        """Load and display all tools in the table"""
        self.ui.tools_table.setRowCount(0)
        session = self.session_maker()
        try:
            tools = (
                session.query(LLMTool)
                .order_by(LLMTool.created_at.desc())
                .all()
            )
            for tool in tools:
                self._add_tool_row(tool)
        finally:
            session.close()

    def _add_tool_row(self, tool: LLMTool):
        """Add a tool to the table"""
        row = self.ui.tools_table.rowCount()
        self.ui.tools_table.insertRow(row)

        # Name
        self.ui.tools_table.setItem(
            row, 0, QTableWidgetItem(tool.display_name or tool.name)
        )

        # Description
        desc = tool.description or "No description"
        self.ui.tools_table.setItem(row, 1, QTableWidgetItem(desc))

        # Created By
        self.ui.tools_table.setItem(
            row, 2, QTableWidgetItem(tool.created_by or "System")
        )

        # Version
        self.ui.tools_table.setItem(
            row, 3, QTableWidgetItem(str(tool.version))
        )

        # Success Rate
        success_rate = (
            f"{tool.success_rate:.1f}%" if tool.usage_count > 0 else "N/A"
        )
        self.ui.tools_table.setItem(row, 4, QTableWidgetItem(success_rate))

        # Enabled checkbox
        enabled_widget = QCheckBox()
        enabled_widget.setChecked(tool.enabled)
        enabled_widget.stateChanged.connect(
            lambda state, t=tool: self.on_enabled_changed(t, state)
        )
        self.ui.tools_table.setCellWidget(row, 5, enabled_widget)

        # Actions
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(
            lambda checked, t=tool: self.on_edit_tool(t)
        )
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(
            lambda checked, t=tool: self.on_delete_tool(t)
        )
        actions_widget = self._create_actions_widget(
            edit_button, delete_button
        )
        self.ui.tools_table.setCellWidget(row, 6, actions_widget)

    def _create_actions_widget(self, *buttons):
        """Create a widget with action buttons"""
        from PySide6.QtWidgets import QWidget, QHBoxLayout

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        for button in buttons:
            layout.addWidget(button)
        return widget

    @Slot(object, int)
    def on_enabled_changed(self, tool: LLMTool, state: int):
        """Toggle tool enabled status"""
        enabled = state == Qt.CheckState.Checked.value
        with session_scope() as session:
            db_tool = session.query(LLMTool).filter_by(id=tool.id).first()
            if db_tool:
                db_tool.enabled = enabled
                self.logger.info(
                    f"Tool {tool.name} {'enabled' if enabled else 'disabled'}"
                )
                self.emit_signal(
                    SignalCode.LLM_TOOL_UPDATED, {"tool": db_tool}
                )

    @Slot(object)
    def on_edit_tool(self, tool: LLMTool):
        """Open editor dialog to edit a tool"""
        editor = LLMToolEditorWidget(tool=tool, parent=self)
        if editor.exec():
            self.load_tools()

    @Slot(object)
    def on_delete_tool(self, tool: LLMTool):
        """Delete a tool after confirmation"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete tool '{tool.display_name or tool.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            with session_scope() as session:
                db_tool = session.query(LLMTool).filter_by(id=tool.id).first()
                if db_tool:
                    session.delete(db_tool)
                    self.logger.info(f"Deleted tool {tool.name}")
                    self.emit_signal(
                        SignalCode.LLM_TOOL_DELETED, {"tool_id": tool.id}
                    )
                    self.load_tools()

    def on_tool_created(self, data: Dict):
        """Handle tool created signal"""
        self.load_tools()

    def on_tool_updated(self, data: Dict):
        """Handle tool updated signal"""
        self.load_tools()

    def on_tool_deleted(self, data: Dict):
        """Handle tool deleted signal"""
        self.load_tools()

    def save_state(self):
        """Save widget state"""

    def restore_state(self):
        """Restore widget state"""
