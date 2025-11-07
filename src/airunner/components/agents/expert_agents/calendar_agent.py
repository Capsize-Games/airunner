"""Calendar expert agent for calendar and event management."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from airunner.components.agents.expert_agent import ExpertAgent
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class CalendarExpertAgent(ExpertAgent):
    """Expert agent specialized in calendar and event management.

    This agent handles tasks related to:
    - Creating, updating, and deleting calendar events
    - Querying events by date/time
    - Managing reminders
    - Scheduling and availability checks
    """

    def __init__(self):
        """Initialize calendar expert agent."""
        super().__init__(
            name="calendar_expert",
            description="Specialized agent for calendar and event management",
        )
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Register agent capabilities."""
        self.register_capability(
            name="event_management",
            description="Create, update, and delete calendar events",
            keywords=[
                "event",
                "calendar",
                "schedule",
                "appointment",
                "meeting",
                "create event",
                "add event",
                "update event",
                "delete event",
                "cancel",
            ],
            priority=9,
        )

        self.register_capability(
            name="event_query",
            description="Query and search calendar events",
            keywords=[
                "when",
                "what time",
                "schedule",
                "busy",
                "free",
                "available",
                "find event",
                "show events",
            ],
            priority=8,
        )

        self.register_capability(
            name="reminder_management",
            description="Manage event reminders",
            keywords=["remind", "reminder", "notification", "alert", "notify"],
            priority=7,
        )

    def get_available_tools(self) -> List[str]:
        """Get list of calendar-related tools.

        Returns:
            List of tool names
        """
        return [
            "create_event",
            "update_event",
            "delete_event",
            "get_events",
            "create_reminder",
            "update_reminder",
            "delete_reminder",
        ]

    async def execute_task(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a calendar-related task.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            Dictionary containing task result
        """
        self.logger.info(f"Calendar agent executing task: {task[:50]}...")

        context = context or {}
        task_lower = task.lower()

        # Determine task type
        if any(
            kw in task_lower for kw in ["create", "add", "schedule", "new"]
        ):
            return await self._create_event_task(task, context)
        elif any(
            kw in task_lower for kw in ["update", "change", "modify", "edit"]
        ):
            return await self._update_event_task(task, context)
        elif any(kw in task_lower for kw in ["delete", "remove", "cancel"]):
            return await self._delete_event_task(task, context)
        elif any(
            kw in task_lower for kw in ["when", "what", "show", "find", "list"]
        ):
            return await self._query_events_task(task, context)
        elif any(
            kw in task_lower for kw in ["remind", "reminder", "notification"]
        ):
            return await self._reminder_task(task, context)
        else:
            # Default to query
            return await self._query_events_task(task, context)

    async def _create_event_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle event creation task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        # This would integrate with the calendar tools created earlier
        # For now, return a structured response for the LLM
        return {
            "success": True,
            "result": {
                "action": "create_event",
                "task_description": task,
                "recommended_tool": "create_event",
                "parameters_to_extract": [
                    "title",
                    "description",
                    "start_datetime",
                    "end_datetime",
                    "location",
                    "tags",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "event_management",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _update_event_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle event update task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "update_event",
                "task_description": task,
                "recommended_tool": "update_event",
                "parameters_to_extract": [
                    "event_id",
                    "title",
                    "description",
                    "start_datetime",
                    "end_datetime",
                    "location",
                    "tags",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "event_management",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _delete_event_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle event deletion task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "delete_event",
                "task_description": task,
                "recommended_tool": "delete_event",
                "parameters_to_extract": ["event_id"],
            },
            "metadata": {
                "agent": self.name,
                "capability": "event_management",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _query_events_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle event query task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "query_events",
                "task_description": task,
                "recommended_tool": "get_events",
                "parameters_to_extract": [
                    "start_date",
                    "end_date",
                    "tags",
                    "search_query",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "event_query",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _reminder_task(self, task: str, context: Dict) -> Dict[str, Any]:
        """Handle reminder management task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        task_lower = task.lower()

        if any(kw in task_lower for kw in ["create", "add", "set"]):
            action = "create_reminder"
        elif any(kw in task_lower for kw in ["update", "change", "modify"]):
            action = "update_reminder"
        elif any(kw in task_lower for kw in ["delete", "remove", "cancel"]):
            action = "delete_reminder"
        else:
            action = "create_reminder"

        return {
            "success": True,
            "result": {
                "action": action,
                "task_description": task,
                "recommended_tool": action,
                "parameters_to_extract": ["event_id", "reminder_time"],
            },
            "metadata": {
                "agent": self.name,
                "capability": "reminder_management",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
