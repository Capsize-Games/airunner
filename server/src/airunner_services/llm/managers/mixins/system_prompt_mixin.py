"""System prompt generation for LLM models."""

from typing import List, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.managers.mixins.system_prompt_actions import (
    get_force_tool_instruction,
    get_system_prompt_for_action,
    get_system_prompt_with_context,
)
from airunner_services.llm.managers.mixins.system_prompt_context import (
    augment_custom_system_prompt,
    build_base_prompt_parts,
    build_research_mode_prompt,
    build_system_prompt_for_action,
    get_memory_context,
    get_prompt_mode,
)
from airunner_services.llm.managers.mixins.system_prompt_mood import (
    get_current_mood,
    get_mood_section,
)
from airunner_services.llm.managers.mixins.system_prompt_text import (
    HEALTH_DISCLAIMER,
    MEMORY_INSTRUCTIONS,
    STYLE_GUIDELINES,
)


class SystemPromptMixin:
    """Mixin for LLM system prompt generation with context-aware inclusions."""

    def _get_memory_context(self, user_query: Optional[str] = None) -> str:
        """Return relevant user memory context."""
        return get_memory_context(self, user_query)

    def _get_prompt_mode(self, tool_categories: Optional[List] = None) -> str:
        """Return the prompt mode for the active tool categories."""
        return get_prompt_mode(tool_categories)

    def get_system_prompt_with_context(
        self,
        action: LLMActionType,
        tool_categories: Optional[List] = None,
        force_tool: Optional[str] = None,
    ) -> str:
        """Return the system prompt selected for the active tool context."""
        return get_system_prompt_with_context(
            self,
            action,
            tool_categories,
            force_tool,
        )

    def _build_base_prompt(self, action: LLMActionType) -> List[str]:
        """Return the context-aware prompt parts for one action."""
        return build_base_prompt_parts(self, action)

    def _augment_custom_system_prompt(
        self,
        base_prompt: str,
        action: LLMActionType,
        include_mood: Optional[bool] = None,
        include_datetime: Optional[bool] = None,
        include_style: Optional[bool] = None,
        include_memory: Optional[bool] = None,
        include_ui_context: Optional[bool] = None,
    ) -> str:
        """Append optional Airunner context blocks to a custom prompt."""
        return augment_custom_system_prompt(
            self,
            base_prompt,
            action,
            include_mood,
            include_datetime,
            include_style,
            include_memory,
            include_ui_context,
        )

    def _get_mood_section(self, force: bool = False) -> Optional[str]:
        """Return the mood section when mood prompting is enabled."""
        return get_mood_section(self, force=force)

    def _get_ui_section_context(self) -> Optional[str]:
        """UI context injection is disabled after the home/art split removal."""
        return None

    @property
    def system_prompt(self) -> str:
        """Return the default full-context system prompt."""
        return self._build_system_prompt_for_action(
            LLMActionType.APPLICATION_COMMAND
        )

    def _build_research_mode_prompt(self) -> str:
        """Return the focused deep-research system prompt."""
        return build_research_mode_prompt(self)

    def _build_system_prompt_for_action(self, action: LLMActionType) -> str:
        """Return the base system prompt for one action."""
        return build_system_prompt_for_action(self, action)

    def _get_current_mood(self) -> Optional[dict]:
        """Return the current mood state when available."""
        return get_current_mood(self)

    def get_system_prompt_for_action(
        self,
        action: LLMActionType,
        force_tool: Optional[str] = None,
    ) -> str:
        """Return the final action-specific system prompt."""
        return get_system_prompt_for_action(self, action, force_tool)

    def _get_style_guidelines(self) -> str:
        """Return the conversational style guidelines block."""
        settings = getattr(self, "llm_settings", None)
        if settings is not None and not getattr(
            settings, "include_health_disclaimer", True
        ):
            return STYLE_GUIDELINES
        return STYLE_GUIDELINES + HEALTH_DISCLAIMER

    def _get_memory_instructions(self) -> str:
        """Return the proactive memory-instructions block."""
        return MEMORY_INSTRUCTIONS

    def _get_force_tool_instruction(self, tool_name: str) -> str:
        """Return the instruction block that forces one specific tool."""
        return get_force_tool_instruction(tool_name)
