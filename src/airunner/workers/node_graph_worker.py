from PySide6.QtCore import Slot
from typing import Dict

from airunner.workers.worker import Worker
from airunner.gui.widgets.nodegraph.nodes.core.start_node import StartNode
from airunner.enums import SignalCode


class NodeGraphWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def on_run_workflow(self, data):
        self.graph = data.get("graph")

        # If workflow was paused, resume it instead of starting fresh
        if self._is_paused:
            self.logger.info("Resuming paused workflow.")
            self._is_paused = False
            # Notify all nodes that we're resuming
            for node_id, node in self._node_map.items():
                if hasattr(node, "on_resume") and callable(
                    getattr(node, "on_resume")
                ):
                    try:
                        node.on_resume()
                    except Exception as e:
                        self.logger.error(
                            f"Error calling on_resume for node {node.name()}: {e}",
                            exc_info=True,
                        )

            # Resume workflow processing
            if hasattr(self, "_execution_queue"):
                self._resume_workflow_from_queue(self._execution_queue)
            else:
                # If we don't have a queue (shouldn't happen), start from scratch
                self.execute_workflow()
        else:
            # Normal workflow start
            self.execute_workflow()

    def on_stop_workflow(self, data):
        self.logger.info("Stopping workflow execution.")

        # Reset pause state if workflow is being stopped
        self._is_paused = False

        # Clear execution queue and pending nodes
        if hasattr(self, "_execution_queue"):
            self._execution_queue = []
        if hasattr(self, "_pending_nodes"):
            self._pending_nodes = set()

        # Notify all nodes in the workflow to stop
        if self.graph and hasattr(self, "_node_map"):
            for node_id, node in self._node_map.items():
                if hasattr(node, "on_stop") and callable(
                    getattr(node, "on_stop")
                ):
                    try:
                        node.on_stop()
                    except Exception as e:
                        self.logger.error(
                            f"Error calling on_stop for node {node.name()}: {e}",
                            exc_info=True,
                        )

        self.logger.info("Workflow execution has been stopped.")

    def on_pause_workflow(self, data):
        self.logger.info("Pausing workflow execution.")

        # Set pause state flag
        self._is_paused = True

        # Notify all nodes in the workflow to pause
        if self.graph and hasattr(self, "_node_map"):
            for node_id, node in self._node_map.items():
                if hasattr(node, "on_pause") and callable(
                    getattr(node, "on_pause")
                ):
                    try:
                        node.on_pause()
                    except Exception as e:
                        self.logger.error(
                            f"Error calling on_pause for node {node.name()}: {e}",
                            exc_info=True,
                        )

        self.logger.info(
            "Workflow execution has been paused. Use run to resume."
        )

    def handle_message(self, data: Dict):
        node_id = data.get("node_id")
        result = data.get("result")
        output_data = data.get(
            "output_data"
        )  # Get output data from the signal

        if not node_id or not result:
            self.logger.warning(
                "Received incomplete node execution completed signal"
            )
            return

        self.logger.info(
            f"Received execution completed signal from node {node_id}, result: {result}"
        )

        # Find the node in our graph
        node = self._node_map.get(node_id)  # Use the map if available
        if not node:
            # Try finding it in the graph if map isn't populated yet
            for n in self.graph.all_nodes():
                if n.id == node_id:
                    node = n
                    break
            if not node:
                self.logger.warning(f"Could not find node with ID {node_id}")
                return

        # Store the output data received from the signal
        if output_data:
            self._node_outputs[node_id] = output_data
            self.logger.info(
                f"Stored async output for node {node_id}: {list(output_data.keys())}"
            )
        elif node_id not in self._node_outputs:
            # Ensure the node is marked as having output, even if empty
            self._node_outputs[node_id] = {}

        # Remove from pending nodes and mark as executed
        if node_id in self._pending_nodes:
            self.logger.info(
                f"Resuming workflow execution after async completion of node {node.name()}"
            )
            self._pending_nodes.remove(node_id)
            self._executed_nodes.add(node_id)

            # Resume workflow from this node's output ports
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
        else:
            self.logger.warning(
                f"Received completion signal for node {node_id} which was not marked as pending."
            )

    def execute_workflow(self, initial_input_data: Dict = None):
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

    def _resume_workflow_from_queue(self, execution_queue):
        # Continue workflow from a given queue after async completion
        self._execution_queue = execution_queue
        self._process_queue()

    def _process_queue(self):
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
                # Use insert rather than append to prioritize this node for the next cycle
                self._execution_queue.insert(0, node_id)
                return  # Pause workflow execution until the pending async operation completes

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
                # Pause workflow until async node signals completion
                return

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
            processed_count += 1

            if triggered_exec_port_name:
                self._queue_next_nodes(
                    current_node,
                    triggered_exec_port_name,
                    self._execution_queue,
                    self._executed_nodes,
                    self._pending_nodes,  # Pass pending nodes to avoid queuing them
                )
            else:
                self.logger.info(
                    f"  Node {current_node.name()} did not trigger an execution output."
                )

        # Only finalize if queue is empty AND no nodes are pending
        if not self._execution_queue and not self._pending_nodes:
            self._finalize_execution(
                processed_count, max_steps, self._node_outputs, self._node_map
            )
        elif processed_count >= max_steps:
            self.logger.warning(
                "Workflow execution stopped: Maximum processing steps reached (potential cycle detected)."
            )

    def _initialize_execution(self, initial_input_data):
        """Initialize the execution queue, executed nodes, and node map."""
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

    def _prepare_input_data(
        self, current_node, node_outputs, initial_input_data
    ):
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
            for port_name, port in current_node.inputs().items():
                if port_name == current_node.EXEC_IN_PORT_NAME:
                    continue
                connected_ports = port.connected_ports()
                if connected_ports:
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
                        triggered_port_name, source_output_data = (
                            self._execute_node(
                                source_node, source_input_data, node_outputs
                            )
                        )

                        # Key fix: Check if the source node returned None (indicating async execution)
                        if (
                            triggered_port_name is None
                            and source_output_data is None
                        ):
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
                        current_input_data[port_name] = node_outputs[
                            source_node_id
                        ][source_port_name]
                        self.logger.info(
                            f"  Input '{port_name}' received data from '{source_node.name()}.{source_port_name}'"
                        )
                    else:
                        current_input_data[port_name] = None
                        self.logger.warning(
                            f"  Input '{port_name}' missing data from source '{source_node.name()}.{source_port_name}'. Using None."
                        )
                        current_input_data[port_name] = None
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

    def _execute_node(self, current_node, current_input_data, node_outputs):
        """Execute the current node and return its outputs and triggered execution port."""
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
        triggered_exec_port_name,
        execution_queue,
        executed_nodes,
        pending_nodes,
    ):
        """Queue the next nodes based on the triggered execution port."""
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

    def _finalize_execution(
        self, processed_count, max_steps, node_outputs, node_map
    ):
        """Finalize the workflow execution and log results."""
        if processed_count >= max_steps:
            self.logger.info(
                "Workflow execution stopped: Maximum processing steps reached (potential cycle detected)."
            )
        else:
            self.logger.info("---\nWorkflow execution finished.")

        final_outputs = {
            node_map[nid].name(): data for nid, data in node_outputs.items()
        }
        self.logger.info(f"Final Node Outputs: {final_outputs}")
