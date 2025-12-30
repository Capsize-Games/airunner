from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from airunner.components.data.models.base import BaseModel
from airunner.components.data.models.base_manager import BaseManager


class WorkflowRun(BaseModel):
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    workflow_id = Column(
        Integer,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(String, nullable=False, default="running")

    triggered_by_user_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    error_message = Column(Text, nullable=True)

    # Initialize the manager after the class is fully defined
    objects = None

    def __repr__(self) -> str:
        return f"<WorkflowRun(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"


WorkflowRun.objects = BaseManager(WorkflowRun)


class WorkflowRunEvent(BaseModel):
    __tablename__ = "workflow_run_events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    run_id = Column(
        String,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    node_id = Column(Integer, nullable=True)
    data = Column(JSON, nullable=False, default=lambda: {})

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Initialize the manager after the class is fully defined
    objects = None

    def __repr__(self) -> str:
        return f"<WorkflowRunEvent(id={self.id}, run_id={self.run_id}, type={self.event_type})>"


WorkflowRunEvent.objects = BaseManager(WorkflowRunEvent)
