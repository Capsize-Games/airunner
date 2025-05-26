"""
Unit tests for workflow save logic in NodeGraphWidget.
Covers DetachedInstanceError prevention and correct workflow_id usage.
"""
import pytest
from unittest.mock import MagicMock, patch
from airunner.gui.widgets.nodegraph.node_graph_widget import NodeGraphWidget

class DummyWorkflow:
    def __init__(self, id):
        self.id = id

@pytest.fixture
def widget():
    # Patch all side-effectful methods so no GUI or DB is touched
    with patch.object(NodeGraphWidget, "__init__", lambda self: None):
        w = NodeGraphWidget()
        w.logger = MagicMock()
        w.ui = MagicMock()
        w.ui.variables.variables = []
        w.graph = MagicMock()
        return w

def test_save_variables_uses_id_and_never_accesses_orm(widget):
    """
    _save_variables should only use workflow.id and never access ORM attributes after session closure.
    """
    dummy_workflow = DummyWorkflow(id=42)
    with patch("airunner.gui.widgets.nodegraph.node_graph_widget.Workflow") as MockWorkflow:
        MockWorkflow.objects.update = MagicMock()
        widget._save_variables(dummy_workflow)
        MockWorkflow.objects.update.assert_called_once_with(42, variables=[])

    # Simulate detached instance (no id attribute)
    class DetachedWorkflow:
        pass
    with patch("airunner.gui.widgets.nodegraph.node_graph_widget.Workflow") as MockWorkflow:
        MockWorkflow.objects.update = MagicMock()
        widget._save_variables(DetachedWorkflow())
        # Should log an error, not raise
        assert widget.logger.error.called

def test_save_connections_uses_id_and_never_accesses_orm(widget):
    """
    _save_connections should only use workflow.id and never access ORM attributes after session closure.
    """
    dummy_workflow = DummyWorkflow(id=99)
    nodes_map = {}
    with patch("airunner.gui.widgets.nodegraph.node_graph_widget.WorkflowConnection") as MockConn:
        MockConn.objects.filter_by = MagicMock(return_value=[])
        MockConn.objects.create = MagicMock()
        MockConn.objects.delete_by = MagicMock()
        widget.graph = MagicMock()
        widget.graph.all_nodes.return_value = []
        widget._save_connections(dummy_workflow, nodes_map)
        MockConn.objects.filter_by.assert_called_once_with(workflow_id=99)

    # Simulate detached instance (no id attribute)
    class DetachedWorkflow:
        pass
    with patch("airunner.gui.widgets.nodegraph.node_graph_widget.WorkflowConnection") as MockConn:
        MockConn.objects.filter_by = MagicMock(return_value=[])
        widget._save_connections(DetachedWorkflow(), nodes_map)
        # Should log an error, not raise
        assert widget.logger.error.called
