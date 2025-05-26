"""
Unit tests for workflow save logic to ensure no DetachedInstanceError occurs.
These tests are headless and do not launch the GUI.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.gui.widgets.nodegraph.node_graph_widget import NodeGraphWidget


class DummyVar:
    def to_dict(self):
        return {"foo": "bar"}


@pytest.fixture
def widget():
    w = NodeGraphWidget.__new__(NodeGraphWidget)  # Do not call __init__
    w.ui = MagicMock()
    w.ui.variables.variables = [DummyVar()]
    # Patch the logger property for this instance only
    patcher = patch.object(
        NodeGraphWidget, "logger", new_callable=PropertyMock
    )
    mock_logger = patcher.start()
    w._logger_patcher = patcher  # Store to stop later
    mock_logger.return_value = MagicMock()
    return w


def test_save_variables_uses_id_and_not_orm(widget):
    """Test _save_variables only uses workflow.id and never accesses ORM attributes after session closure."""

    # Simulate a detached ORM object: accessing any attribute except 'id' raises
    class DetachedWorkflow:
        id = 42

        def __getattribute__(self, name):
            if name == "id":
                return 42
            raise Exception("DetachedInstanceError: ORM object is detached")

    workflow = DetachedWorkflow()
    with patch(
        "airunner.gui.widgets.nodegraph.node_graph_widget.Workflow"
    ) as MockWorkflow:
        MockWorkflow.objects.update.return_value = True
        widget._save_variables(workflow)
        MockWorkflow.objects.update.assert_called_once_with(
            42, variables=[{"foo": "bar"}]
        )
        # No exception should be raised


def test_save_connections_uses_id_and_not_orm(widget):
    """Test _save_connections only uses workflow.id and never accesses ORM attributes after session closure."""

    class DetachedWorkflow:
        id = 99

        def __getattribute__(self, name):
            if name == "id":
                return 99
            raise Exception("DetachedInstanceError: ORM object is detached")

    workflow = DetachedWorkflow()
    widget.graph = MagicMock()
    widget.graph.all_nodes.return_value = []
    with patch(
        "airunner.gui.widgets.nodegraph.node_graph_widget.WorkflowConnection"
    ) as MockConn:
        MockConn.objects.filter_by.return_value = []
        widget.logger = MagicMock()
        widget._save_connections(workflow, {})
        MockConn.objects.filter_by.assert_called_once_with(workflow_id=99)
        # No exception should be raised


@pytest.fixture(autouse=True)
def cleanup_logger_patch(widget):
    yield
    if hasattr(widget, "_logger_patcher"):
        widget._logger_patcher.stop()
