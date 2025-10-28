"""Agent configuration widget for creating and managing custom agents."""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QListWidget,
    QPushButton,
    QLabel,
    QMessageBox,
    QSplitter,
)
from PySide6.QtCore import Signal, Qt
from airunner.components.agents.data.agent_config import AgentConfig
from airunner.components.agents.templates import (
    list_templates,
    get_template,
)
from airunner.components.data.session_manager import session_scope


class AgentConfigWidget(QWidget):
    """Widget for configuring custom agents."""

    agent_created = Signal(int)  # Emits agent_id
    agent_updated = Signal(int)  # Emits agent_id
    agent_deleted = Signal(int)  # Emits agent_id

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize agent configuration widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_agent_id: Optional[int] = None
        self.setup_ui()
        self.load_agents()
        self.load_templates()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Create splitter for agent list and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Agent list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        list_label = QLabel("Agents:")
        left_layout.addWidget(list_label)

        self.agent_list = QListWidget()
        self.agent_list.currentRowChanged.connect(self.on_agent_selected)
        left_layout.addWidget(self.agent_list)

        # Agent list buttons
        list_buttons = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.new_button.clicked.connect(self.on_new_agent)
        list_buttons.addWidget(self.new_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.on_delete_agent)
        self.delete_button.setEnabled(False)
        list_buttons.addWidget(self.delete_button)

        left_layout.addLayout(list_buttons)

        # Right panel - Agent editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Template selector
        template_layout = QHBoxLayout()
        template_label = QLabel("Template:")
        template_layout.addWidget(template_label)

        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(
            self.on_template_changed
        )
        template_layout.addWidget(self.template_combo)
        right_layout.addLayout(template_layout)

        # Agent form
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter agent name...")
        form.addRow("Name:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter agent description...")
        self.description_edit.setMaximumHeight(80)
        form.addRow("Description:", self.description_edit)

        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setPlaceholderText(
            "Enter system prompt for the agent..."
        )
        form.addRow("System Prompt:", self.system_prompt_edit)

        self.tools_edit = QTextEdit()
        self.tools_edit.setPlaceholderText(
            "Enter comma-separated tool names..."
        )
        self.tools_edit.setMaximumHeight(100)
        form.addRow("Tools:", self.tools_edit)

        right_layout.addLayout(form)

        # Save/Test buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.test_button = QPushButton("Test Agent")
        self.test_button.clicked.connect(self.on_test_agent)
        self.test_button.setEnabled(False)
        button_layout.addWidget(self.test_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.on_save_agent)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_button)

        right_layout.addLayout(button_layout)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def load_agents(self) -> None:
        """Load agents from database into list."""
        self.agent_list.clear()

        with session_scope() as session:
            agents = (
                session.query(AgentConfig)
                .filter(AgentConfig.is_active == 1)
                .order_by(AgentConfig.created_at.desc())
                .all()
            )

            for agent in agents:
                item_text = f"{agent.name} ({agent.template})"
                self.agent_list.addItem(item_text)
                # Store agent ID in item data
                item = self.agent_list.item(self.agent_list.count() - 1)
                item.setData(Qt.ItemDataRole.UserRole, agent.id)

    def load_templates(self) -> None:
        """Load template options into combo box."""
        self.template_combo.clear()
        templates = list_templates()

        for template in templates:
            self.template_combo.addItem(
                f"{template.name} - {template.description}", template.name
            )

    def on_agent_selected(self, row: int) -> None:
        """Handle agent selection from list.

        Args:
            row: Selected row index
        """
        if row < 0:
            self.clear_form()
            self.delete_button.setEnabled(False)
            self.test_button.setEnabled(False)
            return

        item = self.agent_list.item(row)
        agent_id = item.data(Qt.ItemDataRole.UserRole)

        with session_scope() as session:
            agent = (
                session.query(AgentConfig)
                .filter(AgentConfig.id == agent_id)
                .first()
            )

            if agent:
                self.current_agent_id = agent.id
                self.name_edit.setText(agent.name)
                self.description_edit.setPlainText(agent.description or "")
                self.system_prompt_edit.setPlainText(agent.system_prompt)
                self.tools_edit.setPlainText(",".join(agent.tool_list))

                # Set template
                index = self.template_combo.findData(agent.template)
                if index >= 0:
                    self.template_combo.setCurrentIndex(index)

                self.delete_button.setEnabled(True)
                self.test_button.setEnabled(True)

    def on_new_agent(self) -> None:
        """Handle new agent button click."""
        self.current_agent_id = None
        self.clear_form()
        self.delete_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.agent_list.setCurrentRow(-1)

    def on_template_changed(self, text: str) -> None:
        """Handle template selection change.

        Args:
            text: Selected template text
        """
        if not text:
            return

        template_name = self.template_combo.currentData()
        if not template_name:
            return

        # Don't override if editing existing agent
        if self.current_agent_id is not None:
            return

        try:
            template = get_template(template_name)

            # Pre-fill with template values
            if not self.description_edit.toPlainText():
                self.description_edit.setPlainText(template.description)

            if not self.system_prompt_edit.toPlainText():
                self.system_prompt_edit.setPlainText(template.system_prompt)

            if not self.tools_edit.toPlainText():
                self.tools_edit.setPlainText(",".join(template.tools))

        except KeyError:
            pass

    def on_save_agent(self) -> None:
        """Handle save button click."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Invalid Input", "Agent name is required."
            )
            return

        system_prompt = self.system_prompt_edit.toPlainText().strip()
        if not system_prompt:
            QMessageBox.warning(
                self, "Invalid Input", "System prompt is required."
            )
            return

        description = self.description_edit.toPlainText().strip()
        tools_text = self.tools_edit.toPlainText().strip()
        tools = [t.strip() for t in tools_text.split(",") if t.strip()]
        template = self.template_combo.currentData()

        try:
            with session_scope() as session:
                if self.current_agent_id:
                    # Update existing agent
                    agent = (
                        session.query(AgentConfig)
                        .filter(AgentConfig.id == self.current_agent_id)
                        .first()
                    )
                    if agent:
                        agent.name = name
                        agent.description = description
                        agent.system_prompt = system_prompt
                        agent.tool_list = tools
                        agent.template = template
                        session.flush()
                        self.agent_updated.emit(agent.id)
                        QMessageBox.information(
                            self,
                            "Success",
                            f"Agent '{name}' updated successfully",
                        )
                else:
                    # Create new agent
                    # Check for duplicate name
                    existing = (
                        session.query(AgentConfig)
                        .filter(AgentConfig.name == name)
                        .first()
                    )
                    if existing:
                        QMessageBox.warning(
                            self,
                            "Duplicate Name",
                            f"Agent with name '{name}' already exists",
                        )
                        return

                    agent = AgentConfig(
                        name=name,
                        description=description,
                        system_prompt=system_prompt,
                        template=template,
                    )
                    agent.tool_list = tools
                    session.add(agent)
                    session.flush()
                    self.agent_created.emit(agent.id)
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Agent '{name}' created successfully",
                    )

            self.load_agents()
            self.clear_form()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save agent: {str(e)}"
            )

    def on_delete_agent(self) -> None:
        """Handle delete button click."""
        if not self.current_agent_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this agent?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with session_scope() as session:
                    agent = (
                        session.query(AgentConfig)
                        .filter(AgentConfig.id == self.current_agent_id)
                        .first()
                    )
                    if agent:
                        agent_name = agent.name
                        session.delete(agent)
                        session.flush()
                        self.agent_deleted.emit(self.current_agent_id)
                        QMessageBox.information(
                            self,
                            "Success",
                            f"Agent '{agent_name}' deleted successfully",
                        )

                self.load_agents()
                self.clear_form()
                self.current_agent_id = None

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to delete agent: {str(e)}"
                )

    def on_cancel(self) -> None:
        """Handle cancel button click."""
        self.clear_form()
        self.current_agent_id = None
        self.agent_list.setCurrentRow(-1)

    def on_test_agent(self) -> None:
        """Handle test agent button click."""
        # TODO: Implement test interface
        # This would send a test prompt to the agent and display results
        QMessageBox.information(
            self,
            "Test Agent",
            "Agent testing functionality coming soon!\n\n"
            "This will allow you to send test prompts to the agent "
            "and see how it responds with the configured tools.",
        )

    def clear_form(self) -> None:
        """Clear all form fields."""
        self.name_edit.clear()
        self.description_edit.clear()
        self.system_prompt_edit.clear()
        self.tools_edit.clear()
        self.template_combo.setCurrentIndex(0)
        self.delete_button.setEnabled(False)
        self.test_button.setEnabled(False)
