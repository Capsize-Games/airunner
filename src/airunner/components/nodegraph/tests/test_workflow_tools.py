"""Tests for nodegraph workflow tools."""

import pytest
from unittest.mock import Mock

from airunner.components.nodegraph.tools.workflow_tools import (
    create_workflow,
    list_workflows,
    get_workflow,
    delete_workflow,
    modify_workflow,
    execute_workflow,
    switch_mode,
)
from airunner.components.nodegraph.data.workflow import Workflow
from airunner.components.nodegraph.data.workflow_node import WorkflowNode
from airunner.components.nodegraph.data.workflow_connection import (
    WorkflowConnection,
)


class TestWorkflowTools:
    """Test workflow management tools."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        # Clear database before each test
        for workflow in Workflow.objects.all():
            Workflow.objects.delete(workflow.id)

    def test_create_workflow_basic(self):
        """Test creating a basic workflow."""
        nodes = [
            {
                "node_identifier": "ai_runner.nodes.InputNode",
                "name": "input",
                "properties": {"label": "User Input"},
            },
            {
                "node_identifier": "ai_runner.nodes.OutputNode",
                "name": "output",
                "properties": {"label": "Result"},
            },
        ]

        connections = [
            {
                "output_node_name": "input",
                "output_port": "output",
                "input_node_name": "output",
                "input_port": "input",
            }
        ]

        result = create_workflow(
            name="test_workflow",
            description="A test workflow",
            nodes=nodes,
            connections=connections,
        )

        assert "Successfully created workflow 'test_workflow'" in result
        assert "2 nodes and 1 connections" in result

        # Verify workflow was created
        workflow = Workflow.objects.filter_by_first(name="test_workflow")
        assert workflow is not None
        assert workflow.description == "A test workflow"

        # Verify nodes and connections (query separately since dataclass doesn't have relationships)
        nodes = WorkflowNode.objects.filter_by(workflow_id=workflow.id)
        connections = WorkflowConnection.objects.filter_by(
            workflow_id=workflow.id
        )
        assert len(nodes) == 2
        assert len(connections) == 1

    def test_create_workflow_with_variables(self):
        """Test creating workflow with variables."""
        nodes = [
            {
                "node_identifier": "ai_runner.nodes.AgentNode",
                "name": "agent",
                "properties": {},
            }
        ]

        variables = {"api_key": "test_key", "temperature": 0.7}

        result = create_workflow(
            name="workflow_with_vars",
            description="Workflow with variables",
            nodes=nodes,
            connections=[],
            variables=variables,
        )

        assert "Successfully created" in result

        workflows = Workflow.objects.filter_by(name="workflow_with_vars")
        assert workflows and len(workflows) > 0
        workflow = workflows[0]
        assert workflow.variables == variables

    def test_create_workflow_duplicate_name(self):
        """Test creating workflow with duplicate name fails."""
        nodes = [{"node_identifier": "test.Node", "name": "node1"}]

        # Create first workflow
        create_workflow(
            name="duplicate_test",
            description="First",
            nodes=nodes,
            connections=[],
        )

        # Try to create duplicate
        result = create_workflow(
            name="duplicate_test",
            description="Second",
            nodes=nodes,
            connections=[],
        )

        assert "Error: Workflow 'duplicate_test' already exists" in result

    def test_list_workflows_empty(self):
        """Test listing workflows when none exist."""
        result = list_workflows()

        assert "No workflows found" in result
        assert "create_workflow tool" in result

    def test_list_workflows(self):
        """Test listing workflows."""
        # Create test workflows
        create_workflow(
            name="workflow1",
            description="First workflow",
            nodes=[{"node_identifier": "test.Node", "name": "n1"}],
            connections=[],
        )

        create_workflow(
            name="workflow2",
            description="Second workflow",
            nodes=[
                {"node_identifier": "test.Node1", "name": "n1"},
                {"node_identifier": "test.Node2", "name": "n2"},
            ],
            connections=[],
        )

        result = list_workflows()

        assert "Available Workflows" in result
        assert "workflow1" in result
        assert "First workflow" in result
        assert "workflow2" in result
        assert "Second workflow" in result
        assert "Nodes: 1" in result
        assert "Nodes: 2" in result

    def test_get_workflow(self):
        """Test getting workflow details."""
        nodes = [
            {
                "node_identifier": "ai_runner.nodes.InputNode",
                "name": "input",
                "properties": {"label": "Input"},
            },
            {
                "node_identifier": "ai_runner.nodes.AgentNode",
                "name": "agent",
                "properties": {"agent_name": "test_agent"},
            },
        ]

        connections = [
            {
                "output_node_name": "input",
                "output_port": "output",
                "input_node_name": "agent",
                "input_port": "input",
            }
        ]

        create_workflow(
            name="detail_test",
            description="Test details",
            nodes=nodes,
            connections=connections,
        )

        workflow = Workflow.objects.filter_by_first(name="detail_test")
        result = get_workflow(workflow.id)

        assert "Workflow: detail_test" in result
        assert "Test details" in result
        assert "Nodes:" in result
        assert "input (ai_runner.nodes.InputNode)" in result
        assert "agent (ai_runner.nodes.AgentNode)" in result
        assert "Connections:" in result
        assert "input.output -> agent.input" in result

    def test_get_workflow_not_found(self):
        """Test getting non-existent workflow."""
        result = get_workflow(99999)

        assert "Error: Workflow with ID 99999 not found" in result

    def test_delete_workflow(self):
        """Test deleting a workflow."""
        create_workflow(
            name="to_delete",
            description="Will be deleted",
            nodes=[{"node_identifier": "test.Node", "name": "n1"}],
            connections=[],
        )

        workflow = Workflow.objects.filter_by_first(name="to_delete")
        workflow_id = workflow.id

        result = delete_workflow(workflow_id)

        assert "Successfully deleted workflow 'to_delete'" in result

        # Verify deletion
        deleted = Workflow.objects.get(workflow_id)
        assert deleted is None

    def test_delete_workflow_not_found(self):
        """Test deleting non-existent workflow."""
        result = delete_workflow(99999)

        assert "Error: Workflow with ID 99999 not found" in result

    def test_modify_workflow_description(self):
        """Test modifying workflow description."""
        create_workflow(
            name="modify_test",
            description="Original description",
            nodes=[{"node_identifier": "test.Node", "name": "n1"}],
            connections=[],
        )

        workflow = Workflow.objects.filter_by_first(name="modify_test")

        result = modify_workflow(
            workflow_id=workflow.id,
            update_description="Updated description",
        )

        assert "Successfully modified workflow 'modify_test'" in result
        assert "updated description" in result

        # Verify update
        updated = Workflow.objects.get(workflow.id)
        assert updated.description == "Updated description"

    def test_modify_workflow_add_nodes(self):
        """Test adding nodes to workflow."""
        create_workflow(
            name="add_nodes_test",
            description="Test",
            nodes=[{"node_identifier": "test.Node1", "name": "n1"}],
            connections=[],
        )

        workflow = Workflow.objects.filter_by_first(name="add_nodes_test")
        initial_nodes = WorkflowNode.objects.filter_by(workflow_id=workflow.id)
        initial_count = len(initial_nodes)

        new_nodes = [
            {
                "node_identifier": "test.Node2",
                "name": "n2",
                "properties": {},
            },
            {
                "node_identifier": "test.Node3",
                "name": "n3",
                "properties": {},
            },
        ]

        result = modify_workflow(workflow_id=workflow.id, add_nodes=new_nodes)

        assert "added 2 node(s)" in result

        # Verify nodes added
        updated_nodes = WorkflowNode.objects.filter_by(workflow_id=workflow.id)
        assert len(updated_nodes) == initial_count + 2

    def test_modify_workflow_remove_nodes(self):
        """Test removing nodes from workflow."""
        create_workflow(
            name="remove_nodes_test",
            description="Test",
            nodes=[
                {"node_identifier": "test.Node1", "name": "n1"},
                {"node_identifier": "test.Node2", "name": "n2"},
                {"node_identifier": "test.Node3", "name": "n3"},
            ],
            connections=[],
        )

        workflow = Workflow.objects.filter_by_first(name="remove_nodes_test")

        result = modify_workflow(
            workflow_id=workflow.id, remove_node_names=["n2", "n3"]
        )

        assert "removed 2 node(s)" in result

        # Verify nodes removed
        updated_nodes = WorkflowNode.objects.filter_by(workflow_id=workflow.id)
        assert len(updated_nodes) == 1
        assert updated_nodes[0].name == "n1"

    def test_modify_workflow_add_connections(self):
        """Test adding connections to workflow."""
        create_workflow(
            name="add_connections_test",
            description="Test",
            nodes=[
                {"node_identifier": "test.Node1", "name": "n1"},
                {"node_identifier": "test.Node2", "name": "n2"},
            ],
            connections=[],
        )

        workflows = Workflow.objects.filter_by(name="add_connections_test")
        workflow = workflows[0] if workflows else None

        new_connections = [
            {
                "output_node_name": "n1",
                "output_port": "output",
                "input_node_name": "n2",
                "input_port": "input",
            }
        ]

        result = modify_workflow(
            workflow_id=workflow.id, add_connections=new_connections
        )

        assert "added 1 connection(s)" in result

        # Verify connection added
        updated_connections = WorkflowConnection.objects.filter_by(
            workflow_id=workflow.id
        )
        assert len(updated_connections) == 1

    def test_modify_workflow_no_changes(self):
        """Test modifying workflow with no changes."""
        create_workflow(
            name="no_changes_test",
            description="Test",
            nodes=[{"node_identifier": "test.Node", "name": "n1"}],
            connections=[],
        )

        workflow = Workflow.objects.filter_by_first(name="no_changes_test")

        result = modify_workflow(workflow_id=workflow.id)

        assert "No changes made to workflow" in result

    def test_execute_workflow(self):
        """Test workflow execution."""
        create_workflow(
            name="execute_test",
            description="Test execution",
            nodes=[{"node_identifier": "test.Node", "name": "n1"}],
            connections=[],
        )

        workflow = Workflow.objects.filter_by_first(name="execute_test")

        # Mock API
        mock_api = Mock()
        mock_api.nodegraph = Mock()
        mock_api.nodegraph.load_workflow = Mock()

        result = execute_workflow(
            workflow_id=workflow.id,
            input_data={"message": "test"},
            api=mock_api,
        )

        assert "execution started" in result
        mock_api.nodegraph.load_workflow.assert_called_once()

    def test_execute_workflow_not_found(self):
        """Test executing non-existent workflow."""
        mock_api = Mock()

        result = execute_workflow(
            workflow_id=99999, input_data={}, api=mock_api
        )

        assert "Error: Workflow with ID 99999 not found" in result

    def test_switch_mode_airunner(self):
        """Test switching to AI Runner mode."""
        mock_api = Mock()

        result = switch_mode(mode="airunner", api=mock_api)

        assert "Switching to airunner mode" in result

    def test_switch_mode_langgraph(self):
        """Test switching to LangGraph mode."""
        mock_api = Mock()

        result = switch_mode(mode="langgraph", api=mock_api)

        assert "Switching to langgraph mode" in result

    def test_switch_mode_invalid(self):
        """Test switching to invalid mode."""
        mock_api = Mock()

        result = switch_mode(mode="invalid", api=mock_api)

        assert "Error: Mode must be 'airunner' or 'langgraph'" in result
