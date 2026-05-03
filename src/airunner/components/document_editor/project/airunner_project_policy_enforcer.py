"""Policy enforcement helpers for AIRunner coding-project actions."""

from dataclasses import dataclass

from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)


@dataclass(frozen=True)
class AirunnerProjectPolicyDecision:
    """Represent one allow-or-block policy decision."""

    allowed: bool
    message: str | None
    context: dict[str, object]


class AirunnerProjectPolicyEnforcer:
    """Evaluate project-scoped autonomy policy for agent actions."""

    def __init__(self, project_service: AirunnerProjectService):
        self.project_service = project_service

    def context(self) -> dict[str, object]:
        """Return the current trust, autonomy, and effective policy flags."""
        settings = self.project_service.load_settings()
        return {
            "trust_level": settings.trust_level.value,
            "autonomy_mode": settings.autonomy_mode.value,
            "effective_policy": settings.effective_policy(),
        }

    def file_write_decision(
        self,
        *,
        reviewed: bool = False,
    ) -> AirunnerProjectPolicyDecision:
        """Return whether a file write may proceed."""
        context = self.context()
        policy = context["effective_policy"]
        if policy["require_file_review"] and not reviewed:
            return AirunnerProjectPolicyDecision(
                allowed=False,
                message="File review required for this project.",
                context=context,
            )
        return AirunnerProjectPolicyDecision(True, None, context)

    def command_decision(
        self,
        *,
        approved: bool = False,
    ) -> AirunnerProjectPolicyDecision:
        """Return whether a command execution may proceed."""
        context = self.context()
        policy = context["effective_policy"]
        if policy["require_command_approval"] and not approved:
            return AirunnerProjectPolicyDecision(
                allowed=False,
                message="Command approval required for this project.",
                context=context,
            )
        return AirunnerProjectPolicyDecision(True, None, context)

    def background_agent_decision(self) -> AirunnerProjectPolicyDecision:
        """Return whether background agents may run automatically."""
        context = self.context()
        policy = context["effective_policy"]
        if not policy["allow_background_agents"]:
            return AirunnerProjectPolicyDecision(
                allowed=False,
                message="Background agents are disabled for this project.",
                context=context,
            )
        return AirunnerProjectPolicyDecision(True, None, context)