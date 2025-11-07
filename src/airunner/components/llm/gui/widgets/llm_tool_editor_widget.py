"""
LLM Tool Editor Widget

Dialog for creating and editing LLM tools.
Provides form fields for tool properties and code editor with validation.
"""

from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtGui import QFont

from airunner.components.llm.gui.widgets.templates.llm_tool_editor_ui import (
    Ui_llm_tool_editor,
)
from airunner.components.llm.data.llm_tool import LLMTool
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.components.data.session_manager import session_scope


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LLMToolEditorWidget(QDialog, MediatorMixin):
    """
    Dialog for creating/editing LLM tools.
    Provides form with validation and code editor.
    """

    def __init__(self, tool: Optional[LLMTool] = None, parent=None):
        super().__init__(parent)
        self.settings = get_qsettings()
        self.tool = tool
        self.ui = Ui_llm_tool_editor()
        self.ui.setupUi(self)

        self._setup_ui()
        self._connect_signals()

        if tool:
            self._load_tool_data()

    def _setup_ui(self):
        """Setup UI elements"""
        # Set monospace font for code editor
        font = QFont("Courier New", 10)
        self.ui.code_editor.setFont(font)
        self.ui.code_editor.setPlaceholderText(
            "# Write your tool function here\n"
            "# Example:\n"
            "def my_tool(param1: str) -> str:\n"
            '    """Tool description"""\n'
            "    return f'Result: {param1}'"
        )

        # Update title based on mode
        if self.tool:
            self.ui.title_label.setText(
                f"Edit Tool: {self.tool.display_name or self.tool.name}"
            )
        else:
            self.ui.title_label.setText("Create New Tool")

    def _connect_signals(self):
        """Connect button signals"""
        self.ui.validate_button.clicked.connect(self.on_validate_clicked)
        self.ui.button_box.accepted.connect(self.on_save_clicked)
        self.ui.button_box.rejected.connect(self.reject)

    def _load_tool_data(self):
        """Load tool data into form"""
        if not self.tool:
            return

        self.ui.name_input.setText(self.tool.name)
        self.ui.display_name_input.setText(self.tool.display_name or "")
        self.ui.description_input.setPlainText(self.tool.description or "")
        self.ui.code_editor.setPlainText(self.tool.code)
        self.ui.enabled_checkbox.setChecked(self.tool.enabled)

    @Slot()
    def on_validate_clicked(self):
        """Validate tool code for safety"""
        code = self.ui.code_editor.toPlainText()

        if not code.strip():
            QMessageBox.warning(
                self, "Validation Error", "Code cannot be empty."
            )
            return

        # Validate code safety
        is_safe, errors = LLMTool.validate_code_safety(code)

        if is_safe:
            QMessageBox.information(
                self,
                "Validation Success",
                "Code passed safety validation!",
            )
        else:
            error_msg = "Code failed safety validation:\n\n" + "\n".join(
                errors
            )
            QMessageBox.critical(self, "Validation Failed", error_msg)

    @Slot()
    def on_save_clicked(self):
        """Save tool to database"""
        # Validate required fields
        name = self.ui.name_input.text().strip()
        code = self.ui.code_editor.toPlainText().strip()

        if not name:
            QMessageBox.warning(
                self, "Validation Error", "Tool name is required."
            )
            return

        if not code:
            QMessageBox.warning(
                self, "Validation Error", "Tool code is required."
            )
            return

        # Validate code safety before saving
        is_safe, errors = LLMTool.validate_code_safety(code)
        if not is_safe:
            error_msg = "Code failed safety validation:\n\n" + "\n".join(
                errors
            )
            reply = QMessageBox.question(
                self,
                "Safety Validation Failed",
                f"{error_msg}\n\nDo you want to save anyway? (Not recommended)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Save to database
        try:
            with session_scope() as session:
                if self.tool:
                    # Update existing tool
                    db_tool = (
                        session.query(LLMTool)
                        .filter_by(id=self.tool.id)
                        .first()
                    )
                    if db_tool:
                        db_tool.name = name
                        db_tool.display_name = (
                            self.ui.display_name_input.text().strip() or None
                        )
                        db_tool.description = (
                            self.ui.description_input.toPlainText().strip()
                            or None
                        )
                        db_tool.code = code
                        db_tool.enabled = self.ui.enabled_checkbox.isChecked()
                        db_tool.safety_validated = is_safe
                        db_tool.version += 1
                        logger.info(
                            f"Updated tool: {db_tool.name} (v{db_tool.version})"
                        )
                        self.emit_signal(
                            SignalCode.LLM_TOOL_UPDATED, {"tool": db_tool}
                        )
                else:
                    # Create new tool
                    new_tool = LLMTool(
                        name=name,
                        display_name=self.ui.display_name_input.text().strip()
                        or None,
                        description=self.ui.description_input.toPlainText().strip()
                        or None,
                        code=code,
                        enabled=self.ui.enabled_checkbox.isChecked(),
                        safety_validated=is_safe,
                        created_by="user",
                        version=1,
                    )
                    session.add(new_tool)
                    logger.info(f"Created tool: {new_tool.name}")
                    self.emit_signal(
                        SignalCode.LLM_TOOL_CREATED, {"tool": new_tool}
                    )

            self.accept()

        except Exception as e:
            logger.error(f"Failed to save tool: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save tool:\n{str(e)}",
            )
