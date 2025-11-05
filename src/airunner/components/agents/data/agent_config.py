"""Agent configuration database model."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
)
from airunner.components.data.models.base import BaseModel


class AgentConfig(BaseModel):
    """Custom agent configuration model.

    Represents a user-defined AI agent with specific tools, system prompt,
    and configuration for specialized tasks.

    Attributes:
        id: Primary key
        name: Unique agent name identifier
        description: Human-readable description of agent purpose
        system_prompt: Custom system prompt for the agent
        tools: Comma-separated list of tool names available to agent
        template: Template category (coding, research, creative, custom)
        created_at: When agent was created
        updated_at: When agent was last modified
        is_active: Whether agent is currently active
    """

    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    tools = Column(Text, nullable=True)  # JSON array stored as text
    template = Column(String(50), nullable=False, default="custom", index=True)
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    is_active = Column(Integer, nullable=False, default=1, index=True)

    def __repr__(self) -> str:
        """String representation of agent config."""
        return (
            f"<AgentConfig(id={self.id}, name='{self.name}', "
            f"template='{self.template}', active={bool(self.is_active)})>"
        )

    @property
    def tool_list(self) -> list[str]:
        """Parse tools string into list.

        Returns:
            List of tool names, or empty list if no tools configured
        """
        if not self.tools:
            return []
        # Tools stored as comma-separated string
        return [t.strip() for t in self.tools.split(",") if t.strip()]

    @tool_list.setter
    def tool_list(self, tools: list[str]) -> None:
        """Set tools from list.

        Args:
            tools: List of tool names
        """
        self.tools = ",".join(tools) if tools else None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of agent config
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tools": self.tool_list,
            "template": self.template,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "is_active": bool(self.is_active),
        }
