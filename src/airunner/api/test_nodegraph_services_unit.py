"""
Unit tests for NodegraphAPIService in nodegraph_services.py.
Covers all public methods and signal emission logic.
"""

import pytest
from unittest.mock import MagicMock, call
from airunner.api.nodegraph_services import NodegraphAPIService
from airunner.enums import SignalCode


@pytest.fixture
def service():
    emit_signal = MagicMock()
    svc = NodegraphAPIService(emit_signal)
    svc.emit_signal = emit_signal  # ensure mock is used
    return svc


def test_node_executed_emits_signal(service):
    service.node_executed("node1", "ok", {"foo": 1})
    service.emit_signal.assert_called_once_with(
        SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
        {"node_id": "node1", "result": "ok", "output_data": {"foo": 1}},
    )


def test_node_executed_emits_signal_no_data(service):
    service.node_executed("node2", "fail")
    service.emit_signal.assert_called_once_with(
        SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
        {"node_id": "node2", "result": "fail", "output_data": {}},
    )


def test_zoom_changed_emits_signal(service):
    service.zoom_changed(1.5)
    service.emit_signal.assert_called_once_with(
        SignalCode.NODEGRAPH_ZOOM, {"zoom_level": 1.5}
    )


def test_pan_changed_emits_signal(service):
    service.pan_changed(10, 20)
    service.emit_signal.assert_called_once_with(
        SignalCode.NODEGRAPH_PAN, {"center_x": 10, "center_y": 20}
    )


def test_run_workflow_emits_signal(service):
    graph = MagicMock(name="CustomNodeGraph")
    service.run_workflow(graph)
    service.emit_signal.assert_called_once_with(
        SignalCode.RUN_WORKFLOW_SIGNAL, {"graph": graph}
    )


def test_pause_workflow_emits_signal(service):
    graph = MagicMock(name="CustomNodeGraph")
    service.pause_workflow(graph)
    service.emit_signal.assert_called_once_with(
        SignalCode.PAUSE_WORKFLOW_SIGNAL, {"graph": graph}
    )


def test_stop_workflow_emits_signal(service):
    graph = MagicMock(name="CustomNodeGraph")
    service.stop_workflow(graph)
    service.emit_signal.assert_called_once_with(
        SignalCode.STOP_WORKFLOW_SIGNAL, {"graph": graph}
    )


def test_register_graph_emits_signal(service):
    graph = MagicMock(name="CustomNodeGraph")
    nodes_palette = MagicMock(name="NodesPaletteWidget")
    finalize = MagicMock(name="finalize")
    service.register_graph(graph, nodes_palette, finalize)
    service.emit_signal.assert_called_once_with(
        SignalCode.REGISTER_GRAPH_SIGNAL,
        {"graph": graph, "nodes_palette": nodes_palette, "callback": finalize},
    )


def test_load_workflow_emits_signal(service):
    workflow = MagicMock(name="Workflow")
    callback = MagicMock(name="callback")
    service.load_workflow(workflow, callback)
    service.emit_signal.assert_called_once_with(
        SignalCode.WORKFLOW_LOAD_SIGNAL,
        {"workflow": workflow, "callback": callback},
    )


def test_clear_workflow_emits_signal(service):
    callback = MagicMock(name="callback")
    service.clear_workflow(callback)
    service.emit_signal.assert_called_once_with(
        SignalCode.CLEAR_WORKFLOW_SIGNAL, {"callback": callback}
    )
