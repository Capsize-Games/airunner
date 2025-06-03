from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from airunner.data.models.base import BaseModel
from airunner.data.models.base_manager import BaseManager


class WorkflowConnection(BaseModel):
    __tablename__ = "workflow_connections"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)

    output_node_id = Column(
        Integer, ForeignKey("workflow_nodes.id"), nullable=False
    )
    output_port_name = Column(String, nullable=False)

    input_node_id = Column(
        Integer, ForeignKey("workflow_nodes.id"), nullable=False
    )
    input_port_name = Column(String, nullable=False)

    workflow = relationship("Workflow", back_populates="connections")
    output_node = relationship(
        "WorkflowNode",
        foreign_keys=[output_node_id],
        back_populates="output_connections",
    )
    input_node = relationship(
        "WorkflowNode",
        foreign_keys=[input_node_id],
        back_populates="input_connections",
    )

    # Initialize the manager after the class is fully defined
    objects = None

    def __repr__(self):
        return f"<WorkflowConnection(id={self.id}, from='{self.output_node_id}:{self.output_port_name}', to='{self.input_node_id}:{self.input_port_name}')>"


# Set the manager outside the class definition
WorkflowConnection.objects = BaseManager(WorkflowConnection)
