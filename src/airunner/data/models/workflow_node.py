from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from airunner.data.models.base import BaseModel
from airunner.data.models.base_manager import BaseManager


class WorkflowNode(BaseModel):
    __tablename__ = "workflow_nodes"
    NODE_NAME = "Workflow Node"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    node_identifier = Column(
        String, nullable=False
    )  # e.g., 'ai_runner.nodes.AgentActionNode'
    name = Column(String, nullable=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    properties = Column(
        JSON, default=lambda: {}
    )  # Store node-specific settings, including port definitions

    workflow = relationship("Workflow", back_populates="nodes")

    # Relationships for connections (useful for cascading deletes)
    output_connections = relationship(
        "WorkflowConnection",
        foreign_keys="[WorkflowConnection.output_node_id]",
        back_populates="output_node",
        cascade="all, delete-orphan",
    )
    input_connections = relationship(
        "WorkflowConnection",
        foreign_keys="[WorkflowConnection.input_node_id]",
        back_populates="input_node",
        cascade="all, delete-orphan",
    )

    # Initialize the manager after the class is fully defined
    objects = None

    def __repr__(self):
        return f"<WorkflowNode(id={self.id}, name='{self.name}', identifier='{self.node_identifier}')>"


# Set the manager outside the class definition
WorkflowNode.objects = BaseManager(WorkflowNode)
