"""Message handling mixin for NodeGraphWorker.

Handles async node completion messages and workflow resumption.
"""

from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class MessageHandlingMixin:
    """Mixin for handling async node execution completion messages."""

    def handle_message(self, data: Dict) -> None:
        """Handle node execution completion message.

        Args:
            data: Message data containing:
                - node_id: ID of completed node
                - result: Execution result/port name
                - output_data: Output data from the node
        """
        node_id = data.get("node_id")
        result = data.get("result")
        output_data = data.get("output_data")

        if not node_id or not result:
            self.logger.warning(
                "Received incomplete node execution completed signal"
            )
            return

        self.logger.info(
            f"Received execution completed signal from node {node_id}, result: {result}"
        )

        # Find the node in our graph
        node = self._find_node_in_graph(node_id)
        if not node:
            return

        # Store the output data received from the signal
        self._store_node_output(node_id, output_data)

        # Remove from pending nodes and mark as executed
        if node_id in self._pending_nodes:
            self._handle_async_completion(node_id, node, result)
        else:
            self.logger.warning(
                f"Received completion signal for node {node_id} which was not marked as pending."
            )

    def _find_node_in_graph(self, node_id: str):
        """Find a node by ID in the graph.

        Args:
            node_id: Node identifier

        Returns:
            Node object or None if not found
        """
        node = None
        node_map = getattr(self, "_node_map", None)
        if node_map:
            node = node_map.get(node_id)

        if not node:
            # If we don't have a valid graph, we can't resolve the node
            if not getattr(self, "graph", None):
                self.logger.warning(
                    f"NodeGraphWorker.handle_message: graph/_node_map not initialized; cannot resolve node {node_id}"
                )
                return None

            try:
                for n in self.graph.all_nodes():
                    if n.id == node_id:
                        node = n
                        break
            except Exception as e:
                self.logger.warning(
                    f"Error iterating graph nodes while resolving node {node_id}: {e}"
                )

            if not node:
                self.logger.warning(f"Could not find node with ID {node_id}")
                return None

        return node

    def _store_node_output(self, node_id: str, output_data: Dict) -> None:
        """Store output data from a completed node.

        Args:
            node_id: Node identifier
            output_data: Output data dictionary
        """
        if output_data:
            self._node_outputs[node_id] = output_data
            self.logger.info(
                f"Stored async output for node {node_id}: {list(output_data.keys())}"
            )
        elif node_id not in self._node_outputs:
            # Ensure the node is marked as having output, even if empty
            self._node_outputs[node_id] = {}

    def _handle_async_completion(
        self, node_id: str, node, result: str
    ) -> None:
        """Handle completion of an async node.

        Args:
            node_id: Node identifier
            node: Node object
            result: Execution result/port name
        """
        self.logger.info(
            f"Resuming workflow execution after async completion of node {node.name()}"
        )
        self._pending_nodes.remove(node_id)
        self._executed_nodes.add(node_id)

        # Resume workflow from this node's output ports
        execution_queue = self._build_continuation_queue(node, result)

        # Resume execution with any new nodes to execute
        if execution_queue:
            # Add to the front of the existing queue
            self._execution_queue = execution_queue + self._execution_queue
            self._resume_workflow_from_queue(self._execution_queue)
        elif not self._pending_nodes and not self._execution_queue:
            # Only finalize if no more nodes to process and no pending nodes
            self.logger.info(
                "No more nodes to execute and no pending nodes, finalizing workflow"
            )
            self._finalize_execution(
                len(self._executed_nodes),
                len(self._node_map) * 10,
                self._node_outputs,
                self._node_map,
            )
        else:
            # There are still nodes in the queue or other pending nodes
            self.logger.info(
                "Continuing workflow execution with existing queue"
            )
            self._resume_workflow_from_queue(self._execution_queue)

    def _build_continuation_queue(self, node, result: str) -> list:
        """Build queue of next nodes to execute after async completion.

        Args:
            node: Completed node object
            result: Execution result/port name

        Returns:
            List of node IDs to execute
        """
        execution_queue = []
        if result in node.outputs():
            output_port = node.outputs()[result]
            for connected_port in output_port.connected_ports():
                next_node = connected_port.node()
                next_node_id = next_node.id
                # Only queue if not already executed, pending, or in the queue
                if (
                    next_node_id not in self._executed_nodes
                    and next_node_id not in self._pending_nodes
                    and next_node_id not in self._execution_queue
                ):
                    execution_queue.append(next_node_id)
                    self.logger.info(
                        f"Queuing node {next_node.name()} for continued execution"
                    )
        return execution_queue
