"""Workflow control mixin for NodeGraphWorker.

Handles starting, stopping, pausing, and resuming workflow execution.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class WorkflowControlMixin:
    """Mixin for workflow lifecycle control operations."""

    def on_run_workflow(self, data: dict) -> None:
        """Handle workflow run signal.

        Args:
            data: Signal data containing 'graph' key with workflow graph
        """
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

    def on_stop_workflow(self, data: dict) -> None:
        """Handle workflow stop signal.

        Args:
            data: Signal data (unused)
        """
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

    def on_pause_workflow(self, data: dict) -> None:
        """Handle workflow pause signal.

        Args:
            data: Signal data (unused)
        """
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
