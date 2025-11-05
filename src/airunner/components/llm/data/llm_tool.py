"""Database model for LLM-generated custom tools."""

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from airunner.components.data.models.base import BaseModel


class LLMTool(BaseModel):
    """Model for storing custom LLM tools created by the agent.

    These tools can be dynamically loaded and used by the LLM agent,
    allowing the agent to expand its own capabilities over time.

    Attributes:
        name: Unique identifier for the tool
        display_name: Human-readable name
        description: What the tool does (used in LLM prompts)
        code: Python code implementing the tool function
        enabled: Whether this tool is currently active
        created_by: 'agent' or 'user'
        version: Version number for tracking updates
        safety_validated: Whether code has passed safety checks
        created_at: Timestamp of creation
        updated_at: Timestamp of last modification
        usage_count: Number of times tool has been called
        success_count: Number of successful executions
        error_count: Number of failed executions
        last_error: Last error message if any
    """

    __tablename__ = "llm_tool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    created_by = Column(String, default="user")  # 'agent' or 'user'
    version = Column(Integer, default=1)
    safety_validated = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Usage statistics
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    @property
    def success_rate(self) -> float:
        """Calculate success rate of tool usage.

        Returns:
            Success rate as percentage (0-100)
        """
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100

    def increment_usage(self, success: bool = True, error: str = None):
        """Increment usage statistics.

        Args:
            success: Whether the execution was successful
            error: Error message if execution failed
        """
        self.usage_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            self.last_error = error
        self.save()

    def validate_code_safety(self) -> tuple[bool, str]:
        """Perform basic safety validation on tool code.

        Returns:
            Tuple of (is_safe, message)
        """
        dangerous_imports = [
            "os.system",
            "subprocess",
            "eval(",
            "exec(",
            "__import__",
            "open(",  # file operations
            "rm ",
            "shutil",
        ]

        code_lower = self.code.lower()
        for dangerous in dangerous_imports:
            if dangerous.lower() in code_lower:
                return False, f"Dangerous operation detected: {dangerous}"

        # Check for proper @tool decorator
        if "@tool" not in self.code:
            return False, "Code must use @tool decorator"

        return True, "Code appears safe"

    def __repr__(self):
        return f"<LLMTool(name='{self.name}', enabled={self.enabled}, version={self.version})>"
