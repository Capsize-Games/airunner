"""
LLM Tool Editor Widget

Dialog for creating and editing LLM tools.
Provides form fields for tool properties and code editor with validation.
"""

from typing import Any, Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtGui import QFont

from airunner.components.llm.gui.widgets.templates.llm_tool_editor_ui import (
    Ui_llm_tool_editor,
)
from airunner.daemon_client.resource_store import get_resource_store
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.settings.get_qsettings import get_qsettings


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _validate_tool_code_safety(code: str) -> tuple[bool, str]:
    dangerous_imports = [
        "os.system",
        "subprocess",
        "eval(",
        "exec(",
        "__import__",
        "open(",
        "rm ",
        "shutil",
    ]

    code_lower = code.lower()
    for dangerous in dangerous_imports:
        if dangerous.lower() in code_lower:
            return False, f"Dangerous operation detected: {dangerous}"

    if "@tool" not in code:
        return False, "Code must use @tool decorator"

    return True, "Code appears safe"


class LLMToolEditorWidget(QDialog, MediatorMixin):
    """
    Dialog for creating/editing LLM tools.
    Provides form with validation and code editor.
    """

    def __init__(self, tool: Optional[Any] = None, parent=None):
        super().__init__(parent)
        self.settings = get_qsettings()
        self.tool = tool
        self.resource_store = get_resource_store()
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

        is_safe, message = _validate_tool_code_safety(code)

        if is_safe:
            QMessageBox.information(
                self,
                "Validation Success",
                "Code passed safety validation!",
            )
        else:
            QMessageBox.critical(
                self,
                "Validation Failed",
                f"Code failed safety validation:\n\n{message}",
            )

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
        is_safe, message = _validate_tool_code_safety(code)
        if not is_safe:
            reply = QMessageBox.question(
                self,
                "Safety Validation Failed",
                f"Code failed safety validation:\n\n{message}\n\nDo you want to save anyway? (Not recommended)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        enabled_requested = self.ui.enabled_checkbox.isChecked()
        enabled = bool(enabled_requested and is_safe)

        if enabled_requested and not is_safe:
            QMessageBox.warning(
                self,
                "Tool Saved Disabled",
                "This tool failed safety validation and will be saved disabled.",
            )

        # Save to database
        try:
            values = {
                "name": name,
                "display_name": self.ui.display_name_input.text().strip()
                or None,
                "description": self.ui.description_input.toPlainText().strip()
                or None,
                "code": code,
                "enabled": enabled,
                "safety_validated": is_safe,
            }
            if self.tool:
                values["version"] = int(getattr(self.tool, "version", 0) or 0) + 1
                updated_tool = self.resource_store.update(
                    "LLMTool",
                    self.tool.id,
                    values,
                )
                if updated_tool is not None:
                    logger.info(
                        f"Updated tool: {updated_tool.name} (v{updated_tool.version})"
                    )
                    self.emit_signal(
                        SignalCode.LLM_TOOL_UPDATED, {"tool": updated_tool}
                    )
            else:
                new_tool = self.resource_store.create(
                    "LLMTool",
                    {
                        "created_by": "user",
                        "version": 1,
                        **values,
                    },
                )
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
