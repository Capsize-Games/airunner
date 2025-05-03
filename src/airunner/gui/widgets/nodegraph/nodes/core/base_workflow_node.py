from typing import List, Dict, Any, Type
from PySide6.QtGui import QPolygonF, QBrush
from PySide6.QtCore import QPointF, Qt

from NodeGraphQt import BaseNode

from airunner.gui.widgets.base_widget import BaseWidget


class BaseWorkflowNode(BaseNode):
    """
    Base class for all workflow nodes in the application.
    This class provides a structure for defining input and output ports,
    properties, and execution logic for nodes in the workflow.
    It also includes methods for handling connections and disconnections
    between nodes.
    The class is designed to be subclassed for specific node types.
    It provides a default implementation for the execute method,
    which can be overridden in subclasses to define specific behavior.
    """

    """
    Set the following attributes in subclasses:
    - __identifier__: Unique identifier for the node
    - _input_ports: List of dictionaries defining input ports
    - _output_ports: List of dictionaries defining output ports
    - _properties: List of dictionaries defining properties
    """
    __identifier__ = "airunner.workflow.nodes.BaseWorkflowNode"
    _input_ports: List[Dict[str, Any]] = []
    _output_ports: List[Dict[str, Any]] = []
    _properties: List[Dict[str, Any]] = []
    widget_class_: Type[BaseWidget] = None
    widget: BaseWidget = None

    # Execution port constants
    EXEC_IN_PORT_NAME: str = "exec_in"
    EXEC_OUT_PORT_NAME: str = "exec_out"
    has_exec_in_port: bool = True
    has_exec_out_port: bool = True

    # Store registered input and output ports
    # to avoid re-adding them
    _registered_input_ports: Dict[str, Any] = {}
    _registered_output_ports: Dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize ports specific to BaseWorkflowNode
        self._initialize_ports()

        # Connect signals (ensure graph exists)
        if (
            hasattr(self, "graph")
            and self.graph
            and hasattr(self.graph, "connection_changed")
        ):
            self.graph.connection_changed.connect(self._on_connection_changed)
        # Only instantiate widget if widget_class_ is defined
        if self.widget_class_:
            self.widget = self.widget_class_()

    def _initialize_ports(self):
        # Add standard execution ports
        # Allow only one connection for execution ports (1-to-1)
        if self.has_exec_in_port:
            self.add_input(
                self.EXEC_IN_PORT_NAME,
                multi_input=False,  # Only one connection allowed to exec_in
                display_name=False,
                painter_func=self._draw_exec_port,
            )
        if self.has_exec_out_port:
            self.add_output(
                self.EXEC_OUT_PORT_NAME,
                multi_output=False,  # Only one connection allowed from exec_out
                display_name=False,
                painter_func=self._draw_exec_port,
            )
        for port in self._input_ports:
            # Ensure display_name is a boolean if present
            if "display_name" in port and not isinstance(
                port["display_name"], bool
            ):
                port["display_name"] = bool(port["display_name"])
            self._registered_input_ports[port["name"]] = self.add_input(**port)
        for port in self._output_ports:
            # Ensure display_name is a boolean if present
            if "display_name" in port and not isinstance(
                port["display_name"], bool
            ):
                port["display_name"] = bool(port["display_name"])
            self._registered_output_ports[port["name"]] = self.add_output(
                **port
            )
        for prop in self._properties:
            prop["widget_type"] = prop["widget_type"].value
            self.create_property(**prop)

    def on_input_connected(self, in_port, out_port):
        """
        Override method called when a connection is made to an input port.
        Ensures exec_in port only maintains one connection.
        """
        super().on_input_connected(in_port, out_port)
        if in_port and in_port.name() == self.EXEC_IN_PORT_NAME:
            # Disconnect any other connections to this exec_in port except the new one
            for connected_port in in_port.connected_ports():
                if connected_port != out_port:
                    in_port.disconnect_from(connected_port)

    def on_output_connected(self, out_port, in_port):
        """
        Override method called when a connection is made from an output port.
        Ensures exec_out port only maintains one connection.
        """
        super().on_output_connected(out_port, in_port)
        if out_port.name() == self.EXEC_OUT_PORT_NAME:
            # Disconnect any other connections from this exec_out port except the new one
            for connected_port in out_port.connected_ports():
                if connected_port != in_port:
                    out_port.disconnect_from(connected_port)

    def _on_connection_changed(self, disconnected, connected):
        """
        Handle connection changes in the graph.
        This is a fallback method if the on_input_connected and on_output_connected
        are not sufficient.
        """
        if not connected:
            return

        # For each new connection, check if it involves our exec ports
        for src_port, tgt_port in connected:
            # If this node is the source with exec_out
            if (
                src_port.node().id() == self.id()
                and src_port.name() == self.EXEC_OUT_PORT_NAME
            ):
                out_port = self.output(self.EXEC_OUT_PORT_NAME)
                # Disconnect all others except the new connection
                for conn_port in list(out_port.connected_ports()):
                    if conn_port != tgt_port:
                        out_port.disconnect_from(conn_port)

            # If this node is the target with exec_in
            elif (
                tgt_port.node().id() == self.id()
                and tgt_port.name() == self.EXEC_IN_PORT_NAME
            ):
                in_port = self.input(self.EXEC_IN_PORT_NAME)
                # Disconnect all others except the new connection
                for conn_port in list(in_port.connected_ports()):
                    if conn_port != src_port:
                        in_port.disconnect_from(conn_port)

    # Custom painter function for execution ports (simple triangle)
    @staticmethod
    def _draw_exec_port(painter, rect, info):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        points = [
            QPointF(rect.left(), rect.top()),
            QPointF(rect.right(), rect.center().y()),
            QPointF(rect.left(), rect.bottom()),
        ]
        painter.drawPolygon(QPolygonF(points))

    # Method to dynamically add an input port
    def add_dynamic_input(
        self,
        name="input",
        multi_input=False,
        display_name=True,
        color=None,
    ):
        # Ensure port name is unique before adding
        if name not in self.inputs():
            return self.add_input(
                name,
                multi_input=multi_input,
                display_name=display_name,
                color=color,
            )
        return self.input(name)

    # Method to dynamically add an output port
    def add_dynamic_output(
        self,
        name="output",
        multi_output=True,
        display_name=True,
        color=None,
    ):
        # Ensure port name is unique before adding
        if name not in self.outputs():
            return self.add_output(
                name,
                multi_output=multi_output,
                display_name=display_name,
                color=color,
            )
        return self.output(name)

    # Placeholder for execution logic - subclasses should override
    def execute(self, input_data):
        print(
            f"Executing node {self.name()} - Base implementation passes data through."
        )
        # By default, pass input data through if an output exists
        passthrough_data = {}
        # Find the first non-exec output port to pass data through
        data_output_port_name = next(
            (
                name
                for name, port in self.outputs().items()
                if name != self.EXEC_OUT_PORT_NAME
            ),
            None,
        )

        # Find the first non-exec input port to get data from
        data_input_port_name = next(
            (
                name
                for name, port in self.inputs().items()
                if name != self.EXEC_IN_PORT_NAME
            ),
            None,
        )

        if (
            data_output_port_name
            and data_input_port_name
            and data_input_port_name in input_data
        ):
            passthrough_data[data_output_port_name] = input_data[
                data_input_port_name
            ]

        # Return data keyed by output port name and indicate execution flow
        return {**passthrough_data, "_exec_triggered": self.EXEC_OUT_PORT_NAME}

    # Helper to get data from a specific input port name
    def get_input_data(self, port_name, input_data, default=None):
        return input_data.get(port_name, default)

    def on_pause(self):
        """
        Called when the workflow is paused.
        Override in subclasses to implement custom pause behavior.
        This method is called on each node when the workflow is paused.
        """
        try:
            # Log pause action using logger if available, otherwise fallback to print
            if hasattr(self, "logger"):
                self.logger.debug(f"Node '{self.name()}' paused.")
            else:
                self.logger.info(f"Node '{self.name()}' paused.")
        except Exception as e:
            self.logger.info(
                f"Error in on_pause for node '{self.name()}': {e}"
            )

    def on_stop(self):
        """
        Called when the workflow is stopped.
        Override in subclasses to implement custom stop behavior.
        This method is called on each node when the workflow is stopped.
        Use this to cancel any async operations or clean up resources.
        """
        try:
            # Log stop action using logger if available, otherwise fallback to print
            if hasattr(self, "logger"):
                self.logger.debug(f"Node '{self.name()}' stopped.")
            else:
                self.logger.info(f"Node '{self.name()}' stopped.")
        except Exception as e:
            self.logger.info(f"Error in on_stop for node '{self.name()}': {e}")

    def on_resume(self):
        """
        Called when the workflow is resumed after being paused.
        Override in subclasses to implement custom resume behavior.
        This method is called on each node when the workflow is resumed.
        """
        try:
            # Log resume action using logger if available, otherwise fallback to print
            if hasattr(self, "logger"):
                self.logger.debug(f"Node '{self.name()}' resumed.")
            else:
                self.logger.info(f"Node '{self.name()}' resumed.")
        except Exception as e:
            self.logger.info(
                f"Error in on_resume for node '{self.name()}': {e}"
            )
