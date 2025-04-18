import json
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from airunner.data.models.base import BaseModel


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

    def __repr__(self):
        return f"<Workflow(id={self.id}, name='{self.name}')>"
