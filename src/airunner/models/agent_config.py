"""Service-owned agent configuration model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from airunner.base import BaseModel


class AgentConfig(BaseModel):
    """Persist custom agent definitions for user-managed agents."""

    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    tools = Column(Text, nullable=True)
    template = Column(String(50), nullable=False, default="custom", index=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    is_active = Column(Integer, nullable=False, default=1, index=True)

    def __repr__(self) -> str:
        """Return a readable representation for debug output."""
        return (
            f"<AgentConfig(id={self.id}, name='{self.name}', "
            f"template='{self.template}', active={bool(self.is_active)})>"
        )

    @property
    def tool_list(self) -> list[str]:
        """Parse the persisted tools string into a list."""
        if not self.tools:
            return []
        return [tool.strip() for tool in self.tools.split(",") if tool.strip()]

    @tool_list.setter
    def tool_list(self, tools: list[str]) -> None:
        """Persist the tool list as a comma-separated string."""
        self.tools = ",".join(tools) if tools else None

    def to_dict(self) -> dict:
        """Convert the model into a serializable dictionary."""
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


__all__ = ["AgentConfig"]