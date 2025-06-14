from sqlalchemy import Column, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from airunner.components.data.models.base import BaseModel
from airunner.components.data.models.base_manager import BaseManager


class Workflow(BaseModel):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    variables = Column(JSON)

    nodes = relationship(
        "WorkflowNode",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="select",
    )
    connections = relationship(
        "WorkflowConnection",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Initialize the manager after the class is fully defined
    objects = None

    def __repr__(self):
        return f"<Workflow(id={self.id}, name='{self.name}')>"


# Set the manager outside the class definition
Workflow.objects = BaseManager(Workflow)
