"""Tests for Template Browser Dialog."""

import pytest
import tempfile
import shutil
from pathlib import Path

# Qt imports must come before airunner imports
try:
    from PySide6.QtWidgets import QApplication, QDialog
    import sys

    # Create QApplication if it doesn't exist
    if not QApplication.instance():
        app = QApplication(sys.argv)
except ImportError:
    pytest.skip("PySide6 not available", allow_module_level=True)

from airunner.components.nodegraph.gui.widgets.template_browser_dialog import (
    TemplateBrowserDialog,
    TemplateVariablesDialog,
)
from airunner.components.nodegraph.template_manager import (
    get_template_manager,
    WorkflowTemplate,
)


@pytest.fixture
def temp_template_dir():
    """Create temporary directory for templates."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_template():
    """Create a mock workflow template."""
    return WorkflowTemplate(
        {
            "name": "Test Template",
            "description": "A test template",
            "category": "test",
            "tags": ["test", "mock"],
            "author": "Test Author",
            "version": "1.0",
            "variables": {"var1": "value1", "var2": 42},
            "nodes": [
                {
                    "node_identifier": "test.Node",
                    "name": "test_node",
                    "pos_x": 100,
                    "pos_y": 200,
                    "properties": {"prop": "{{var1}}"},
                }
            ],
            "connections": [],
        }
    )


class TestTemplateVariablesDialog:
    """Test cases for TemplateVariablesDialog."""

    def test_create_dialog(self, mock_template):
        """Test creating variables dialog."""
        dialog = TemplateVariablesDialog(mock_template)
        assert dialog.template == mock_template
        assert "var1" in dialog.variable_inputs
        assert "var2" in dialog.variable_inputs
        assert dialog.variable_inputs["var1"].text() == "value1"
        assert dialog.variable_inputs["var2"].text() == "42"

    def test_dialog_with_no_variables(self):
        """Test dialog with template that has no variables."""
        template = WorkflowTemplate(
            {
                "name": "No Vars",
                "description": "Template without variables",
                "category": "test",
                "nodes": [],
                "connections": [],
            }
        )
        dialog = TemplateVariablesDialog(template)
        assert len(dialog.variable_inputs) == 0

    def test_get_workflow_data(self, mock_template):
        """Test getting workflow data from dialog."""
        dialog = TemplateVariablesDialog(mock_template)
        dialog.variable_inputs["var1"].setText("new_value")
        dialog.variable_inputs["var2"].setText("100")
        dialog.name_input.setText("Custom Workflow")

        data = dialog.get_workflow_data()
        assert data["workflow_name"] == "Custom Workflow"
        assert data["variables"]["var1"] == "new_value"
        assert data["variables"]["var2"] == "100"

    def test_default_workflow_name(self, mock_template):
        """Test that default workflow name is template name."""
        dialog = TemplateVariablesDialog(mock_template)
        assert dialog.name_input.text() == mock_template.name


class TestTemplateBrowserDialog:
    """Test cases for TemplateBrowserDialog."""

    def test_create_dialog(self, temp_template_dir):
        """Test creating template browser dialog."""
        # Override template manager directory
        manager = get_template_manager()
        original_dir = manager.template_dir
        manager.template_dir = Path(temp_template_dir)

        try:
            dialog = TemplateBrowserDialog()
            assert dialog.template_manager is not None
            assert dialog.current_template is None
            assert not dialog.create_button.isEnabled()
        finally:
            manager.template_dir = original_dir

    def test_load_templates(self, temp_template_dir):
        """Test loading templates into list."""
        # Create test template file
        template_data = {
            "name": "Test Template",
            "description": "Test",
            "category": "test",
            "nodes": [],
            "connections": [],
        }

        import json

        template_file = Path(temp_template_dir) / "test.json"
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        # Override template manager directory
        manager = get_template_manager()
        original_dir = manager.template_dir
        manager.template_dir = Path(temp_template_dir)
        manager.reload()

        try:
            dialog = TemplateBrowserDialog()
            assert dialog.template_list.count() == 1
            item = dialog.template_list.item(0)
            assert item.text() == "Test Template"
        finally:
            manager.template_dir = original_dir
            manager.reload()

    def test_filter_by_category(self, temp_template_dir):
        """Test filtering templates by category."""
        # Create templates in different categories
        templates = [
            {
                "name": "Template 1",
                "description": "Test",
                "category": "knowledge",
                "nodes": [],
                "connections": [],
            },
            {
                "name": "Template 2",
                "description": "Test",
                "category": "agent",
                "nodes": [],
                "connections": [],
            },
        ]

        import json

        for i, template_data in enumerate(templates):
            template_file = Path(temp_template_dir) / f"template{i}.json"
            with open(template_file, "w") as f:
                json.dump(template_data, f)

        # Override template manager directory
        manager = get_template_manager()
        original_dir = manager.template_dir
        manager.template_dir = Path(temp_template_dir)
        manager.reload()

        try:
            dialog = TemplateBrowserDialog()
            assert dialog.template_list.count() == 2

            # Filter by knowledge category
            for i in range(dialog.category_combo.count()):
                if dialog.category_combo.itemData(i) == "knowledge":
                    dialog.category_combo.setCurrentIndex(i)
                    break

            dialog._filter_templates()
            assert dialog.template_list.count() == 1
            assert dialog.template_list.item(0).text() == "Template 1"
        finally:
            manager.template_dir = original_dir
            manager.reload()

    def test_search_templates(self, temp_template_dir):
        """Test searching templates."""
        # Create templates
        templates = [
            {
                "name": "RAG Workflow",
                "description": "Search and retrieve",
                "category": "knowledge",
                "tags": ["rag", "search"],
                "nodes": [],
                "connections": [],
            },
            {
                "name": "Agent Loop",
                "description": "Autonomous agent",
                "category": "agent",
                "tags": ["agent"],
                "nodes": [],
                "connections": [],
            },
        ]

        import json

        for i, template_data in enumerate(templates):
            template_file = Path(temp_template_dir) / f"template{i}.json"
            with open(template_file, "w") as f:
                json.dump(template_data, f)

        # Override template manager directory
        manager = get_template_manager()
        original_dir = manager.template_dir
        manager.template_dir = Path(temp_template_dir)
        manager.reload()

        try:
            dialog = TemplateBrowserDialog()

            # Search for "rag"
            dialog.search_input.setText("rag")
            dialog._filter_templates()
            assert dialog.template_list.count() == 1
            assert "RAG" in dialog.template_list.item(0).text()

            # Search for "agent"
            dialog.search_input.setText("agent")
            dialog._filter_templates()
            assert dialog.template_list.count() == 1
            assert "Agent" in dialog.template_list.item(0).text()
        finally:
            manager.template_dir = original_dir
            manager.reload()

    def test_template_selection(self, temp_template_dir):
        """Test selecting a template updates preview."""
        # Create test template
        template_data = {
            "name": "Test Template",
            "description": "A test template",
            "category": "test",
            "tags": ["test"],
            "author": "Test Author",
            "version": "1.0",
            "variables": {"var1": "value1"},
            "nodes": [{"name": "node1"}],
            "connections": [],
        }

        import json

        template_file = Path(temp_template_dir) / "test.json"
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        # Override template manager directory
        manager = get_template_manager()
        original_dir = manager.template_dir
        manager.template_dir = Path(temp_template_dir)
        manager.reload()

        try:
            dialog = TemplateBrowserDialog()

            # Select template
            dialog.template_list.setCurrentRow(0)

            assert dialog.current_template is not None
            assert dialog.current_template.name == "Test Template"
            assert dialog.create_button.isEnabled()
            assert "Test Template" in dialog.name_label.text()
            assert "test template" in dialog.description_text.toPlainText()
        finally:
            manager.template_dir = original_dir
            manager.reload()

    def test_template_selected_signal(self, temp_template_dir, mock_template):
        """Test that template_selected signal is emitted."""
        # Create test template file
        import json

        template_data = mock_template.to_dict()
        template_file = Path(temp_template_dir) / "test.json"
        with open(template_file, "w") as f:
            json.dump(template_data, f)

        # Override template manager directory
        manager = get_template_manager()
        original_dir = manager.template_dir
        manager.template_dir = Path(temp_template_dir)
        manager.reload()

        try:
            dialog = TemplateBrowserDialog()

            # Connect signal
            signal_received = []

            def on_template_selected(template_name, workflow_name, variables):
                signal_received.append(
                    {
                        "template_name": template_name,
                        "workflow_name": workflow_name,
                        "variables": variables,
                    }
                )

            dialog.template_selected.connect(on_template_selected)

            # Select template and click create
            dialog.template_list.setCurrentRow(0)

            # Mock the variables dialog to just accept
            original_exec = TemplateVariablesDialog.exec

            def mock_exec(self):
                return QDialog.Accepted

            TemplateVariablesDialog.exec = mock_exec

            try:
                dialog._on_create_clicked()

                # Signal should be emitted
                assert len(signal_received) == 1
                assert signal_received[0]["template_name"] == "Test Template"
            finally:
                TemplateVariablesDialog.exec = original_exec
        finally:
            manager.template_dir = original_dir
            manager.reload()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
