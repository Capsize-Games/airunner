from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode
from airunner.components.nodegraph.data.workflow import Workflow
from airunner.components.nodegraph.gui.widgets.custom_node_graph import (
    CustomNodeGraph,
)


class NodegraphAPIService(APIServiceBase):
    def node_executed(self, node_id, result, data=None):
        self.emit_signal(
            SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
            {"node_id": node_id, "result": result, "output_data": data or {}},
        )

    def zoom_changed(self, zoom_level):
        self.emit_signal(SignalCode.NODEGRAPH_ZOOM, {"zoom_level": zoom_level})

    def pan_changed(self, center_x, center_y):
        self.emit_signal(
            SignalCode.NODEGRAPH_PAN,
            {"center_x": center_x, "center_y": center_y},
        )

    def run_workflow(self, graph: CustomNodeGraph):
        self.emit_signal(SignalCode.RUN_WORKFLOW_SIGNAL, {"graph": graph})

    def pause_workflow(self, graph: CustomNodeGraph):
        self.emit_signal(SignalCode.PAUSE_WORKFLOW_SIGNAL, {"graph": graph})

    def stop_workflow(self, graph: CustomNodeGraph):
        self.emit_signal(SignalCode.STOP_WORKFLOW_SIGNAL, {"graph": graph})

    def register_graph(self, graph, nodes_palette, finalize):
        self.emit_signal(
            SignalCode.REGISTER_GRAPH_SIGNAL,
            {
                "graph": graph,
                "nodes_palette": nodes_palette,
                "callback": finalize,
            },
        )

    def load_workflow(self, workflow: Workflow, callback):
        self.emit_signal(
            SignalCode.WORKFLOW_LOAD_SIGNAL,
            {"workflow": workflow, "callback": callback},
        )

    def new_document(self):
        self.clear_workflow(None)

    def clear_workflow(self, callback):
        self.emit_signal(
            SignalCode.CLEAR_WORKFLOW_SIGNAL,
            {"callback": callback},
        )
