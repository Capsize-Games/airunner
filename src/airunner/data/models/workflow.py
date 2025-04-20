import json
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from airunner.data.models.base import BaseModel
from airunner.data.models.base_manager import BaseManager


class Workflow(BaseModel):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)

    nodes = relationship(
        "WorkflowNode", back_populates="workflow", cascade="all, delete-orphan"
    )
    connections = relationship(
        "WorkflowConnection",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    # Initialize the manager after the class is fully defined
    objects = None

    def __repr__(self):
        return f"<Workflow(id={self.id}, name='{self.name}')>"


# Set the manager outside the class definition
Workflow.objects = BaseManager(Workflow)
