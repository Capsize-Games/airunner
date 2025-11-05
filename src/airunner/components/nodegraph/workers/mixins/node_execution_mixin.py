"""Node execution mixin for NodeGraphWorker.

Handles input data preparation and node execution logic.
"""

from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class NodeExecutionMixin:
    """Mixin for node input preparation and execution."""

    def _prepare_input_data(
        self, current_node, node_outputs: Dict, initial_input_data: Dict
    ) -> Optional[Dict]:
        """Prepare input data for a node by gathering data from connected inputs.

        Args:
            current_node: Node to prepare inputs for
            node_outputs: Dictionary of outputs from executed nodes
            initial_input_data: Initial workflow input data

        Returns:
            Dictionary of input data, or None if dependencies are pending
        """
        current_input_data = {}
        current_node_id = current_node.id

        # Check for recursion - if this node is already being processed, break the recursion
        if current_node_id in self._nodes_in_processing:
            self.logger.warning(
                f"Recursion detected for node '{current_node.name()}'. Breaking recursive loop."
            )
            return {}

        # Add this node to the processing set
        self._nodes_in_processing.add(current_node_id)

        try:
            # Process connected inputs
            for port_name, port in current_node.inputs().items():
                if port_name == current_node.EXEC_IN_PORT_NAME:
                    continue

                connected_ports = port.connected_ports()
                if connected_ports:
                    value = self._get_connected_input_value(
                        port_name,
                        connected_ports,
                        node_outputs,
                        initial_input_data,
                    )
                    if (
                        value is None
                        and current_node_id in self._nodes_in_processing
                    ):
                        # Dependency is pending
                        return None
                    current_input_data[port_name] = value

            # Fill in initial input data for unconnected ports
            for port_name in current_node.inputs():
                if (
                    port_name != current_node.EXEC_IN_PORT_NAME
                    and port_name not in current_input_data
                    and port_name in initial_input_data
                ):
                    current_input_data[port_name] = initial_input_data[
                        port_name
                    ]
                    self.logger.info(
                        f"  Input '{port_name}' received initial data."
                    )
        finally:
            # Remove this node from the processing set
            self._nodes_in_processing.remove(current_node_id)

        return current_input_data

    def _get_connected_input_value(
        self,
        port_name: str,
        connected_ports: list,
        node_outputs: Dict,
        initial_input_data: Dict,
    ):
        """Get value from a connected input port.

        Args:
            port_name: Name of the input port
            connected_ports: List of connected ports
            node_outputs: Dictionary of node outputs
            initial_input_data: Initial workflow input data

        Returns:
            Input value or None if pending
        """
        source_port = connected_ports[0]
        source_node = source_port.node()
        source_node_id = source_node.id
        source_port_name = source_port.name()

        # If the source node hasn't been executed, do it now
        if source_node_id not in node_outputs:
            self.logger.warning(
                f"  Source node '{source_node.name()}' for input '{port_name}' not executed yet. Attempting to execute it recursively."
            )
            source_input_data = self._prepare_input_data(
                source_node, node_outputs, initial_input_data
            )
            triggered_port_name, source_output_data = self._execute_node(
                source_node, source_input_data, node_outputs
            )

            # Check if the source node returned None (indicating async execution)
            if triggered_port_name is None and source_output_data is None:
                self.logger.info(
                    f"  Source node '{source_node.name()}' execution is pending. Cannot continue preparing input data."
                )
                # Exit early as we cannot continue until this source node completes
                return None

            if source_output_data:
                node_outputs[source_node_id] = source_output_data
            else:
                self.logger.error(
                    f"  Recursive execution of source node '{source_node.name()}' failed or produced no output."
                )

        # Now get the value
        if (
            source_node_id in node_outputs
            and source_port_name in node_outputs[source_node_id]
        ):
            value = node_outputs[source_node_id][source_port_name]
            self.logger.info(
                f"  Input '{port_name}' received data from '{source_node.name()}.{source_port_name}'"
            )
            return value
        else:
            self.logger.warning(
                f"  Input '{port_name}' missing data from source '{source_node.name()}.{source_port_name}'. Using None."
            )
            return None

    def _execute_node(
        self, current_node, current_input_data: Dict, node_outputs: Dict
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """Execute the current node and return its outputs and triggered execution port.

        Args:
            current_node: Node to execute
            current_input_data: Input data for the node
            node_outputs: Dictionary to store node outputs

        Returns:
            Tuple of (triggered_exec_port_name, output_data)
            Returns (None, None) if execution is pending
        """
        output_data = {}
        triggered_exec_port_name = None

        if hasattr(current_node, "execute") and callable(
            getattr(current_node, "execute")
        ):
            try:
                # Execute the node and get its output
                outputs = current_node.execute(current_input_data)
                # Check if the node returned None, which indicates pending execution
                if outputs is None:
                    self.logger.info(
                        f"  Node '{current_node.name()}' execution is pending. Will retry later."
                    )
                    # Return None for both values to indicate pending execution
                    return None, None

                # Make a copy of outputs to avoid modifying the original during pop operations
                output_data = {k: v for k, v in outputs.items()}

                # Check if the node triggered an execution output
                if "_exec_triggered" in outputs:
                    triggered_exec_port_name = outputs["_exec_triggered"]
                    # Don't store the execution trigger in the node's outputs
                    output_data.pop("_exec_triggered", None)
                elif current_node.EXEC_OUT_PORT_NAME in current_node.outputs():
                    # Default to standard execution output if available
                    triggered_exec_port_name = current_node.EXEC_OUT_PORT_NAME

                # Store outputs for use by downstream nodes
                node_outputs[current_node.id] = output_data
                self.logger.info(
                    f"  Node '{current_node.name()}' executed. Output: {list(output_data.keys())}"
                )

                if triggered_exec_port_name:
                    self.logger.info(
                        f"  Execution will flow through port: {triggered_exec_port_name}"
                    )
                else:
                    self.logger.info(
                        f"  No execution port triggered, execution path ends here"
                    )

            except Exception as e:
                self.logger.error(
                    f"  Error executing node {current_node.name()}: {e}",
                    exc_info=True,
                )
                # Mark as failed but don't halt workflow
                node_outputs[current_node.id] = {}
        else:
            self.logger.info(
                f"  Node {current_node.name()} has no execute method."
            )
            node_outputs[current_node.id] = {}

        return triggered_exec_port_name, output_data

    def _queue_next_nodes(
        self,
        current_node,
        triggered_exec_port_name: str,
        execution_queue: list,
        executed_nodes: set,
        pending_nodes: set,
    ) -> None:
        """Queue the next nodes based on the triggered execution port.

        Args:
            current_node: Current node that was executed
            triggered_exec_port_name: Name of triggered execution port
            execution_queue: Queue to add next nodes to
            executed_nodes: Set of already executed node IDs
            pending_nodes: Set of pending node IDs
        """
        if (
            triggered_exec_port_name
            and triggered_exec_port_name in current_node.outputs()
        ):
            exec_output_port = current_node.outputs()[triggered_exec_port_name]
            connected_exec_inputs = exec_output_port.connected_ports()

            for next_port in connected_exec_inputs:
                next_node = next_port.node()
                next_node_id = next_node.id
                # Check for executed, pending, and already in queue
                if (
                    next_node_id not in execution_queue
                    and next_node_id not in executed_nodes
                    and next_node_id not in pending_nodes
                ):
                    self.logger.info(
                        f"  Queueing next node: {next_node.name()} (ID: {next_node_id}) via port {next_port.name()}"
                    )
                    execution_queue.append(next_node_id)
                else:
                    reason = (
                        "already executed"
                        if next_node_id in executed_nodes
                        else (
                            "pending"
                            if next_node_id in pending_nodes
                            else "already in queue"
                        )
                    )
                    self.logger.info(
                        f"  Node not queued: {next_node.name()} (ID: {next_node_id}) - {reason}"
                    )
        elif triggered_exec_port_name:
            self.logger.warning(
                f"  Triggered execution port '{triggered_exec_port_name}' not found on node '{current_node.name()}'. Execution stops here."
            )
        else:
            self.logger.info(
                f"  Node '{current_node.name()}' did not trigger an execution output. Execution path ends here."
            )
