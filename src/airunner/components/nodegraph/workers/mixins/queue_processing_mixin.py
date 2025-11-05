"""Queue processing mixin for NodeGraphWorker.

Handles workflow execution queue processing and node execution flow.
"""

from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class QueueProcessingMixin:
    """Mixin for processing workflow execution queue."""

    def execute_workflow(self, initial_input_data: Dict = None) -> None:
        """Execute the workflow starting from Start nodes.

        Args:
            initial_input_data: Optional initial input data for workflow
        """
        if initial_input_data is None:
            initial_input_data = {}
        self._node_outputs = (
            {}
        )  # Store data outputs {node_id: {port_name: data}}
        execution_queue, executed_nodes, node_map = self._initialize_execution(
            initial_input_data
        )
        self._execution_queue = execution_queue
        self._executed_nodes = executed_nodes
        self._node_map = node_map
        self._initial_input_data = initial_input_data
        self._process_queue()

    def _resume_workflow_from_queue(self, execution_queue: list) -> None:
        """Continue workflow from a given queue after async completion.

        Args:
            execution_queue: Queue of node IDs to execute
        """
        self._execution_queue = execution_queue
        self._process_queue()

    def _process_queue(self) -> None:
        """Process the execution queue until empty or paused."""
        processed_count = 0
        max_steps = len(self._node_map) * 10

        # Check if any node is currently pending before starting
        if self._pending_nodes:
            self.logger.info(
                f"Workflow paused, waiting for pending nodes: {self._pending_nodes}"
            )
            return  # Don't process if waiting

        while self._execution_queue and processed_count < max_steps:
            # Check again inside the loop in case a node becomes pending
            if self._pending_nodes:
                self.logger.info(
                    f"Workflow paused during processing, waiting for pending nodes: {self._pending_nodes}"
                )
                return  # Stop processing if a node became pending

            node_id = self._execution_queue.pop(0)

            # Skip if already executed or pending
            if (
                node_id in self._executed_nodes
                or node_id in self._pending_nodes
            ):
                continue

            current_node = self._node_map.get(node_id)
            if not current_node:
                self.logger.warning(
                    f"Node ID {node_id} not found in map during execution. Skipping."
                )
                continue

            # Process the node
            should_continue = self._process_single_node(
                node_id, current_node, processed_count
            )
            if not should_continue:
                return  # Workflow paused due to pending dependency

            processed_count += 1

        # Only finalize if queue is empty AND no nodes are pending
        if not self._execution_queue and not self._pending_nodes:
            self._finalize_execution(
                processed_count, max_steps, self._node_outputs, self._node_map
            )
        elif processed_count >= max_steps:
            self.logger.warning(
                "Workflow execution stopped: Maximum processing steps reached (potential cycle detected)."
            )

    def _process_single_node(
        self, node_id: str, current_node, processed_count: int
    ) -> bool:
        """Process a single node in the execution queue.

        Args:
            node_id: Node identifier
            current_node: Node object
            processed_count: Number of nodes processed so far

        Returns:
            True if workflow should continue, False if paused
        """
        self.logger.info(
            f"Executing node: {current_node.name()} (ID: {node_id})"
        )
        current_input_data = self._prepare_input_data(
            current_node, self._node_outputs, self._initial_input_data
        )

        # If _prepare_input_data returns None, it means a dependency is pending async execution
        if current_input_data is None:
            self.logger.info(
                f"  Node '{current_node.name()}' has pending dependencies. Adding back to queue."
            )
            # Put this node back in the execution queue to try again later
            self._execution_queue.insert(0, node_id)
            return False  # Pause workflow execution

        triggered_exec_port_name, output_data = self._execute_node(
            current_node, current_input_data, self._node_outputs
        )

        # Check if the node itself became pending (returned None, None)
        if triggered_exec_port_name is None and output_data is None:
            self.logger.info(
                f"  Node '{current_node.name()}' is pending execution. Workflow will pause until completion."
            )
            print(
                f"  Node '{current_node.name()}' is pending execution. Workflow will pause until completion."
            )
            # Add to pending nodes set
            self._pending_nodes.add(node_id)
            return False  # Pause workflow

        # Only store output and mark as executed if node didn't become pending
        if output_data is not None:
            self._node_outputs[node_id] = output_data
            self.logger.info(
                f"  Node {current_node.name()} produced output: {list(output_data.keys())}"
            )
        elif node_id not in self._node_outputs:
            # Ensure entry exists even if output is {}
            self._node_outputs[node_id] = {}

        # Mark as executed only if not pending
        self._executed_nodes.add(node_id)

        # Queue next nodes based on execution flow
        if triggered_exec_port_name:
            self._queue_next_nodes(
                current_node,
                triggered_exec_port_name,
                self._execution_queue,
                self._executed_nodes,
                self._pending_nodes,
            )
        else:
            self.logger.info(
                f"  Node {current_node.name()} did not trigger an execution output."
            )

        return True  # Continue workflow

    def _initialize_execution(self, initial_input_data: Dict) -> tuple:
        """Initialize the execution queue, executed nodes, and node map.

        Args:
            initial_input_data: Initial input data for workflow

        Returns:
            Tuple of (execution_queue, executed_nodes, node_map)
        """
        # Import at runtime to avoid circular dependencies
        from airunner.components.nodegraph.gui.widgets.nodes.core.start_node import (
            StartNode,
        )

        execution_queue = []
        executed_nodes = set()
        node_map = {node.id: node for node in self.graph.all_nodes()}

        # Find all StartNodes to begin execution
        start_node_ids = []
        for node_id, node in node_map.items():
            if isinstance(node, StartNode):
                start_node_ids.append(node_id)

        # Add start nodes to the front of the queue
        execution_queue.extend(start_node_ids)

        self.logger.info(
            f"Starting workflow execution. Initial queue: {start_node_ids}"
        )
        return execution_queue, executed_nodes, node_map

    def _finalize_execution(
        self,
        processed_count: int,
        max_steps: int,
        node_outputs: Dict,
        node_map: Dict,
    ) -> None:
        """Finalize the workflow execution and log results.

        Args:
            processed_count: Number of nodes processed
            max_steps: Maximum allowed steps
            node_outputs: Dictionary of node outputs
            node_map: Dictionary mapping node IDs to nodes
        """
        # Import at runtime to avoid circular dependencies
        from airunner.enums import SignalCode

        self.emit_signal(
            SignalCode.WORKFLOW_EXECUTION_COMPLETED_SIGNAL,
            {
                "processed_count": processed_count,
                "max_steps": max_steps,
                "node_outputs": node_outputs,
                "node_map": node_map,
            },
        )
