from PySide6.QtGui import QPolygonF, QPen, QBrush
from PySide6.QtCore import QPointF, Qt

from NodeGraphQt import BaseNode
from NodeGraphQt.constants import PortTypeEnum

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class BaseWorkflowNode(
    MediatorMixin,
    SettingsMixin,
    BaseNode,
):
    # Base identifier for easier registration and type checking
    __identifier__ = "airunner.workflow.nodes"
    # Execution port constants
    EXEC_IN_PORT_NAME = "exec_in"
    EXEC_OUT_PORT_NAME = "exec_out"
    has_exec_in_port: bool = True
    has_exec_out_port: bool = True

    def __init__(self):
        super().__init__()
        # Add standard execution ports
        # Allow multiple execution inputs to converge on one node
        if self.has_exec_in_port:
            self.add_input(
                self.EXEC_IN_PORT_NAME,
                multi_input=True,
                display_name=False,
                painter_func=self._draw_exec_port,
            )
        if self.has_exec_out_port:
            self.add_output(
                self.EXEC_OUT_PORT_NAME,
                display_name=False,
                painter_func=self._draw_exec_port,
            )

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


# Need to import Qt classes used in the painter function
from PySide6.QtGui import QPolygonF, QPen, QBrush
from PySide6.QtCore import QPointF, Qt
