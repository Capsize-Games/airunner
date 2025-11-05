"""Tests for workflow template manager."""

import pytest
import tempfile
from pathlib import Path

from airunner.components.nodegraph.template_manager import (
    TemplateManager,
    WorkflowTemplate,
    get_template_manager,
)


class TestWorkflowTemplate:
    """Test WorkflowTemplate class."""

    def test_create_template(self):
        """Test creating template from dictionary."""
        data = {
            "name": "Test Template",
            "description": "A test template",
            "category": "test",
            "tags": ["test", "demo"],
            "author": "Tester",
            "version": "1.0",
            "variables": {"var1": "value1"},
            "nodes": [{"node_identifier": "test.Node", "name": "n1"}],
            "connections": [],
        }

        template = WorkflowTemplate(data)

        assert template.name == "Test Template"
        assert template.description == "A test template"
        assert template.category == "test"
        assert template.tags == ["test", "demo"]
        assert template.author == "Tester"
        assert template.version == "1.0"
        assert template.variables == {"var1": "value1"}
        assert len(template.nodes) == 1
        assert len(template.connections) == 0

    def test_template_defaults(self):
        """Test template with missing fields uses defaults."""
        data = {"nodes": [], "connections": []}

        template = WorkflowTemplate(data)

        assert template.name == "Untitled Template"
        assert template.description == ""
        assert template.category == "general"
        assert template.tags == []
        assert template.author == "Unknown"
        assert template.version == "1.0"

    def test_to_dict(self):
        """Test converting template to dictionary."""
        data = {
            "name": "Test",
            "description": "Test template",
            "category": "test",
            "tags": ["test"],
            "author": "Tester",
            "version": "1.0",
            "variables": {},
            "nodes": [],
            "connections": [],
        }

        template = WorkflowTemplate(data)
        result = template.to_dict()

        assert result["name"] == "Test"
        assert result["description"] == "Test template"
        assert result["category"] == "test"


class TestTemplateManager:
    """Test TemplateManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create template manager with temp directory."""
        return TemplateManager(str(temp_dir))

    def test_manager_initialization(self, temp_dir):
        """Test manager initialization creates directory."""
        assert temp_dir.exists()

        manager = TemplateManager(str(temp_dir))
        assert manager.template_dir == temp_dir
        assert len(manager.templates) == 0
        assert len(manager.categories) == 0

    def test_save_and_load_template(self, manager, temp_dir):
        """Test saving and loading templates."""
        data = {
            "name": "Test Template",
            "description": "A test",
            "category": "test",
            "tags": [],
            "author": "Test",
            "version": "1.0",
            "variables": {},
            "nodes": [],
            "connections": [],
        }

        template = WorkflowTemplate(data)
        success = manager.save_template(template)

        assert success is True
        assert "Test Template" in manager.templates

        # Check file was created
        files = list(temp_dir.glob("*.json"))
        assert len(files) == 1

        # Reload and check
        manager.reload()
        loaded = manager.get_template("Test Template")
        assert loaded is not None
        assert loaded.name == "Test Template"

    def test_list_templates(self, manager):
        """Test listing templates."""
        # Create multiple templates
        for i in range(3):
            data = {
                "name": f"Template {i}",
                "description": "Test",
                "category": "test",
                "nodes": [],
                "connections": [],
            }
            template = WorkflowTemplate(data)
            manager.save_template(template)

        templates = manager.list_templates()
        assert len(templates) == 3

    def test_list_by_category(self, manager):
        """Test listing templates by category."""
        # Create templates in different categories
        categories = ["cat1", "cat2", "cat1"]
        for i, cat in enumerate(categories):
            data = {
                "name": f"Template {i}",
                "description": "Test",
                "category": cat,
                "nodes": [],
                "connections": [],
            }
            template = WorkflowTemplate(data)
            manager.save_template(template)

        cat1_templates = manager.list_by_category("cat1")
        cat2_templates = manager.list_by_category("cat2")

        assert len(cat1_templates) == 2
        assert len(cat2_templates) == 1

    def test_list_categories(self, manager):
        """Test listing all categories."""
        # Create templates in different categories
        for cat in ["cat1", "cat2", "cat3"]:
            data = {
                "name": f"Template {cat}",
                "description": "Test",
                "category": cat,
                "nodes": [],
                "connections": [],
            }
            template = WorkflowTemplate(data)
            manager.save_template(template)

        categories = manager.list_categories()
        assert len(categories) == 3
        assert "cat1" in categories
        assert "cat2" in categories
        assert "cat3" in categories

    def test_search_templates_by_name(self, manager):
        """Test searching templates by name."""
        names = ["RAG Workflow", "Agent Loop", "Tool Chain"]
        for name in names:
            data = {
                "name": name,
                "description": "Test",
                "category": "test",
                "nodes": [],
                "connections": [],
            }
            template = WorkflowTemplate(data)
            manager.save_template(template)

        results = manager.search_templates("RAG")
        assert len(results) == 1
        assert results[0].name == "RAG Workflow"

    def test_search_templates_by_description(self, manager):
        """Test searching templates by description."""
        data = {
            "name": "Test",
            "description": "This is a special workflow template",
            "category": "test",
            "nodes": [],
            "connections": [],
        }
        template = WorkflowTemplate(data)
        manager.save_template(template)

        results = manager.search_templates("special")
        assert len(results) == 1

    def test_search_templates_by_tag(self, manager):
        """Test searching templates by tags."""
        data = {
            "name": "Test",
            "description": "Test",
            "category": "test",
            "tags": ["rag", "knowledge", "search"],
            "nodes": [],
            "connections": [],
        }
        template = WorkflowTemplate(data)
        manager.save_template(template)

        results = manager.search_templates("knowledge")
        assert len(results) == 1

    def test_search_with_category_filter(self, manager):
        """Test searching with category filter."""
        # Create templates in different categories
        data1 = {
            "name": "RAG Workflow",
            "description": "Test",
            "category": "knowledge",
            "nodes": [],
            "connections": [],
        }
        data2 = {
            "name": "RAG Agent",
            "description": "Test",
            "category": "agent",
            "nodes": [],
            "connections": [],
        }

        manager.save_template(WorkflowTemplate(data1))
        manager.save_template(WorkflowTemplate(data2))

        # Search for "RAG" in knowledge category only
        results = manager.search_templates("RAG", category="knowledge")
        assert len(results) == 1
        assert results[0].category == "knowledge"

    def test_delete_template(self, manager, temp_dir):
        """Test deleting template."""
        data = {
            "name": "To Delete",
            "description": "Test",
            "category": "test",
            "nodes": [],
            "connections": [],
        }
        template = WorkflowTemplate(data)
        manager.save_template(template)

        # Verify it exists
        assert manager.get_template("To Delete") is not None

        # Delete it
        success = manager.delete_template("To Delete")
        assert success is True

        # Verify it's gone
        assert manager.get_template("To Delete") is None

        # Verify file is deleted
        files = list(temp_dir.glob("*.json"))
        assert len(files) == 0

    def test_create_from_template_basic(self, manager):
        """Test creating workflow from template."""
        data = {
            "name": "Test Template",
            "description": "Test",
            "category": "test",
            "variables": {"var1": "default1"},
            "nodes": [
                {
                    "node_identifier": "test.Node",
                    "name": "node1",
                    "properties": {"value": "{{var1}}"},
                }
            ],
            "connections": [],
        }
        template = WorkflowTemplate(data)
        manager.save_template(template)

        workflow = manager.create_from_template("Test Template", "My Workflow")

        assert workflow is not None
        assert workflow["name"] == "My Workflow"
        assert workflow["variables"]["var1"] == "default1"
        assert workflow["nodes"][0]["properties"]["value"] == "default1"

    def test_create_from_template_with_variable_override(self, manager):
        """Test creating workflow with variable overrides."""
        data = {
            "name": "Test Template",
            "description": "Test",
            "category": "test",
            "variables": {"var1": "default1", "var2": "default2"},
            "nodes": [
                {
                    "node_identifier": "test.Node",
                    "name": "node1",
                    "properties": {
                        "value1": "{{var1}}",
                        "value2": "{{var2}}",
                    },
                }
            ],
            "connections": [],
        }
        template = WorkflowTemplate(data)
        manager.save_template(template)

        workflow = manager.create_from_template(
            "Test Template",
            "My Workflow",
            variables={"var1": "override1"},
        )

        assert workflow is not None
        assert workflow["variables"]["var1"] == "override1"
        assert workflow["variables"]["var2"] == "default2"
        assert workflow["nodes"][0]["properties"]["value1"] == "override1"
        assert workflow["nodes"][0]["properties"]["value2"] == "default2"

    def test_create_from_nonexistent_template(self, manager):
        """Test creating from non-existent template returns None."""
        workflow = manager.create_from_template("Nonexistent", "My Workflow")
        assert workflow is None

    def test_load_invalid_json(self, temp_dir):
        """Test loading invalid JSON file."""
        # Create invalid JSON file
        invalid_file = temp_dir / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        manager = TemplateManager(str(temp_dir))

        # Should not crash, just log error and skip file
        assert len(manager.templates) == 0

    def test_get_template_manager_singleton(self):
        """Test get_template_manager returns singleton."""
        manager1 = get_template_manager()
        manager2 = get_template_manager()

        assert manager1 is manager2
