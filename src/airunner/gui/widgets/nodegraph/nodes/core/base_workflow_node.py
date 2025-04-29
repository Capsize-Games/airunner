from PySide6.QtGui import QPolygonF, QPen, QBrush
from PySide6.QtCore import QPointF, Qt

from NodeGraphQt import BaseNode

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class BaseWorkflowNode(
    MediatorMixin,
    SettingsMixin,
    BaseNode,
):
    # Base identifier for easier registration and type checking
    __identifier__ = "airunner.workflow.nodes.BaseWorkflowNode"
    # Execution port constants
    EXEC_IN_PORT_NAME = "exec_in"
    EXEC_OUT_PORT_NAME = "exec_out"
    has_exec_in_port: bool = True
    has_exec_out_port: bool = True

    def __init__(self):
        super().__init__()
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

        # Connect to the connection changed signals
        if hasattr(self.graph, "connection_changed"):
            self.graph.connection_changed.connect(self._on_connection_changed)

    def on_input_connected(self, in_port, out_port):
        """
        Override method called when a connection is made to an input port.
        Ensures exec_in port only maintains one connection.
        """
        super().on_input_connected(in_port, out_port)
        if in_port.name() == self.EXEC_IN_PORT_NAME:
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
