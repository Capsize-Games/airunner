"""NodeGraphWorker for executing workflow graphs.

Handles workflow execution including node processing, async operations,
and execution flow control.
"""


from airunner.components.application.workers.worker import Worker
from airunner.components.nodegraph.workers.mixins import (
    WorkflowControlMixin,
    MessageHandlingMixin,
    QueueProcessingMixin,
    NodeExecutionMixin,
)
from airunner.enums import SignalCode


class NodeGraphWorker(
    WorkflowControlMixin,
    MessageHandlingMixin,
    QueueProcessingMixin,
    NodeExecutionMixin,
    Worker,
):
    """Worker for executing node graph workflows.

    Coordinates workflow execution through multiple mixins:
    - WorkflowControlMixin: Start/stop/pause control
    - MessageHandlingMixin: Async node completion handling
    - QueueProcessingMixin: Execution queue processing
    - NodeExecutionMixin: Node input preparation and execution

    Attributes:
        graph: The workflow graph to execute
        _initial_input_data: Initial input data for the workflow
        _node_map: Map of node IDs to node objects
        _executed_nodes: Set of executed node IDs
        _node_outputs: Dictionary of node outputs
        _execution_queue: Queue of nodes to execute
        _nodes_in_processing: Set of nodes currently being processed
        _pending_nodes: Set of nodes waiting for async operations
        _is_paused: Whether workflow execution is paused
    """

    def __init__(self, *args, **kwargs):
        """Initialize the NodeGraphWorker."""
        super().__init__(*args, **kwargs)
        self._initial_input_data = None
        self._node_map = None
        self._executed_nodes = None
        self._node_outputs = None
        self._execution_queue = None
        self.graph = None
        self.register(SignalCode.RUN_WORKFLOW_SIGNAL, self.on_run_workflow)
        self.register(SignalCode.STOP_WORKFLOW_SIGNAL, self.on_stop_workflow)
        self.register(SignalCode.PAUSE_WORKFLOW_SIGNAL, self.on_pause_workflow)
        # Track nodes being processed to prevent infinite recursion
        self._nodes_in_processing = set()
        # Track nodes waiting for async operations
        self._pending_nodes = set()
        # Workflow state
        self._is_paused = False
