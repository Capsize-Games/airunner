"""
Dual-LLM Router for AI Runner.

This module provides a router that directs requests to either:
1. Fara-7B: For computer use, tool execution, and agentic tasks
2. Standard LLM: For dialogue generation, conversation, and text tasks

The router automatically determines which model to use based on:
- Request type (chat vs computer_use)
- Presence of screenshots/images
- Explicit routing hints

This enables efficient use of specialized models:
- Fara excels at tool use and computer automation
- Standard LLM excels at natural dialogue and text generation

Usage:
    router = DualLLMRouter(
        dialogue_manager=my_llm_manager,
        tool_manager=my_fara_manager,
    )
    response = router.route_request(request)
"""

from typing import Dict, Any, Optional, Union, List
from enum import Enum
from dataclasses import dataclass

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.enums import LLMActionType


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class RouteTarget(Enum):
    """Target for routing a request."""
    DIALOGUE = "dialogue"  # Standard LLM for text generation
    TOOL_USE = "tool_use"  # Fara for computer use/tool execution
    AUTO = "auto"  # Auto-detect based on request content


@dataclass
class RoutingDecision:
    """Decision about which model to route to."""
    target: RouteTarget
    reason: str
    confidence: float = 1.0


class DualLLMRouter:
    """
    Routes requests between dialogue LLM and tool-use LLM (Fara).

    This router enables a dual-model architecture where:
    - Dialogue model handles conversation, text generation, creative writing
    - Tool model (Fara) handles computer use, automation, tool execution

    The router can operate in several modes:
    1. Auto: Automatically detect which model to use
    2. Forced: Always use a specific model
    3. Hybrid: Use both models for different parts of a request
    """

    def __init__(
        self,
        dialogue_manager: Optional[Any] = None,
        tool_manager: Optional[Any] = None,
        default_route: RouteTarget = RouteTarget.AUTO,
        enable_fara: bool = True,
    ):
        """
        Initialize the dual-LLM router.

        Args:
            dialogue_manager: LLMModelManager for dialogue/text generation
            tool_manager: FaraModelManager for tool use/computer control
            default_route: Default routing when auto-detect is inconclusive
            enable_fara: Whether Fara is enabled (if False, always use dialogue)
        """
        self._dialogue_manager = dialogue_manager
        self._tool_manager = tool_manager
        self._default_route = default_route
        self._enable_fara = enable_fara

        # Keywords that suggest tool use
        self._tool_keywords = {
            "click", "scroll", "type", "navigate", "open", "browser",
            "website", "search", "download", "upload", "fill", "form",
            "book", "order", "purchase", "checkout", "add to cart",
            "automate", "automation", "computer", "screen",
        }

        # Keywords that suggest dialogue
        self._dialogue_keywords = {
            "explain", "describe", "write", "tell me", "what is",
            "how does", "why", "story", "poem", "essay", "article",
            "summarize", "translate", "conversation", "chat",
        }

    def set_dialogue_manager(self, manager: Any) -> None:
        """Set the dialogue model manager."""
        self._dialogue_manager = manager

    def set_tool_manager(self, manager: Any) -> None:
        """Set the tool model manager (Fara)."""
        self._tool_manager = manager

    def enable_fara(self, enable: bool = True) -> None:
        """Enable or disable Fara for tool use."""
        self._enable_fara = enable
        logger.info(f"Fara {'enabled' if enable else 'disabled'}")

    def route_request(
        self,
        prompt: str,
        action: Optional[LLMActionType] = None,
        image_data: Optional[Union[str, bytes]] = None,
        force_route: Optional[RouteTarget] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Route a request to the appropriate model.

        Args:
            prompt: The user's prompt/request
            action: Optional action type hint
            image_data: Optional image/screenshot data
            force_route: Force routing to specific target
            **kwargs: Additional arguments passed to the model

        Returns:
            Response dictionary from the appropriate model
        """
        # Determine routing
        decision = self._make_routing_decision(
            prompt=prompt,
            action=action,
            image_data=image_data,
            force_route=force_route,
        )

        logger.debug(f"Routing decision: {decision.target} ({decision.reason})")

        # Route to appropriate model
        if decision.target == RouteTarget.TOOL_USE:
            return self._route_to_tool_model(
                prompt=prompt,
                image_data=image_data,
                **kwargs,
            )
        else:
            return self._route_to_dialogue_model(
                prompt=prompt,
                action=action,
                **kwargs,
            )

    def _make_routing_decision(
        self,
        prompt: str,
        action: Optional[LLMActionType] = None,
        image_data: Optional[Union[str, bytes]] = None,
        force_route: Optional[RouteTarget] = None,
    ) -> RoutingDecision:
        """
        Determine which model to route to.

        Args:
            prompt: The user's prompt
            action: Optional action type hint
            image_data: Optional image data
            force_route: Force routing to specific target

        Returns:
            RoutingDecision with target and reasoning
        """
        # Force route overrides everything
        if force_route and force_route != RouteTarget.AUTO:
            return RoutingDecision(
                target=force_route,
                reason="Forced routing",
            )

        # If Fara is disabled, always use dialogue
        if not self._enable_fara or self._tool_manager is None:
            return RoutingDecision(
                target=RouteTarget.DIALOGUE,
                reason="Fara disabled or not available",
            )

        # If image data is present, likely needs tool use
        if image_data:
            return RoutingDecision(
                target=RouteTarget.TOOL_USE,
                reason="Screenshot/image present",
                confidence=0.9,
            )

        # Check action type hints
        if action:
            tool_actions = {
                LLMActionType.PERFORM_RAG_SEARCH,
                LLMActionType.SEARCH,
            }
            if action in tool_actions:
                return RoutingDecision(
                    target=RouteTarget.TOOL_USE,
                    reason=f"Action type {action} suggests tool use",
                    confidence=0.8,
                )

        # Analyze prompt keywords
        prompt_lower = prompt.lower()

        tool_score = sum(1 for kw in self._tool_keywords if kw in prompt_lower)
        dialogue_score = sum(1 for kw in self._dialogue_keywords if kw in prompt_lower)

        if tool_score > dialogue_score:
            return RoutingDecision(
                target=RouteTarget.TOOL_USE,
                reason=f"Tool keywords ({tool_score}) > dialogue keywords ({dialogue_score})",
                confidence=min(0.5 + tool_score * 0.1, 0.9),
            )
        elif dialogue_score > tool_score:
            return RoutingDecision(
                target=RouteTarget.DIALOGUE,
                reason=f"Dialogue keywords ({dialogue_score}) > tool keywords ({tool_score})",
                confidence=min(0.5 + dialogue_score * 0.1, 0.9),
            )

        # Default routing
        if self._default_route == RouteTarget.TOOL_USE:
            return RoutingDecision(
                target=RouteTarget.TOOL_USE,
                reason="Default route (inconclusive analysis)",
                confidence=0.5,
            )
        else:
            return RoutingDecision(
                target=RouteTarget.DIALOGUE,
                reason="Default route (inconclusive analysis)",
                confidence=0.5,
            )

    def _route_to_tool_model(
        self,
        prompt: str,
        image_data: Optional[Union[str, bytes]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Route request to Fara for tool use."""
        if self._tool_manager is None:
            logger.warning("Tool manager not available, falling back to dialogue")
            return self._route_to_dialogue_model(prompt=prompt, **kwargs)

        try:
            # If we have a screenshot, use get_next_action
            if image_data:
                result = self._tool_manager.get_next_action(
                    screenshot=image_data,
                    goal=prompt,
                )
                return {
                    "response": result.get("thought", ""),
                    "action": result.get("action", {}),
                    "model": "fara",
                    "raw": result,
                }
            else:
                # No screenshot - use _do_generate
                result = self._tool_manager._do_generate(
                    prompt=prompt,
                    image_data=image_data,
                    **kwargs,
                )
                return {
                    **result,
                    "model": "fara",
                }
        except Exception as e:
            logger.error(f"Tool model error: {e}")
            return {
                "response": f"Error using tool model: {e}",
                "error": str(e),
                "model": "fara",
            }

    def _route_to_dialogue_model(
        self,
        prompt: str,
        action: Optional[LLMActionType] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Route request to dialogue LLM."""
        if self._dialogue_manager is None:
            return {
                "response": "No dialogue model available",
                "error": "Dialogue manager not configured",
                "model": "none",
            }

        try:
            result = self._dialogue_manager._do_generate(
                prompt=prompt,
                action=action or LLMActionType.CHAT,
                **kwargs,
            )
            return {
                **result,
                "model": "dialogue",
            }
        except Exception as e:
            logger.error(f"Dialogue model error: {e}")
            return {
                "response": f"Error using dialogue model: {e}",
                "error": str(e),
                "model": "dialogue",
            }

    def execute_computer_task(
        self,
        goal: str,
        initial_context: Optional[str] = None,
        on_step_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete computer use task using Fara.

        This method sets up the FaraController and runs a full
        automation task, handling screenshots and action execution.

        Args:
            goal: The task goal description
            initial_context: Optional additional context
            on_step_callback: Callback for each step

        Returns:
            TaskResult dictionary
        """
        if not self._enable_fara or self._tool_manager is None:
            return {
                "status": "failure",
                "error": "Fara not available for computer tasks",
            }

        try:
            from airunner.components.llm.managers.fara_controller import (
                FaraController,
            )

            controller = FaraController(
                fara_manager=self._tool_manager,
                on_step_callback=on_step_callback,
            )

            result = controller.execute_task(
                goal=goal,
                initial_context=initial_context,
            )

            return {
                "status": result.status.value,
                "goal": result.goal,
                "steps_taken": result.steps_taken,
                "action_history": result.action_history,
                "memorized_facts": result.memorized_facts,
                "error": result.error,
            }
        except Exception as e:
            logger.error(f"Computer task error: {e}")
            return {
                "status": "failure",
                "error": str(e),
            }


class ToolUseIntegration:
    """
    Integration layer for using Fara as the tool executor for standard LLM.

    This allows the standard LLM to request tool execution, which is then
    handled by Fara. The standard LLM focuses on understanding intent and
    generating responses, while Fara handles actual tool execution.

    Flow:
    1. User sends request to dialogue LLM
    2. Dialogue LLM determines tool is needed, generates tool call
    3. Tool call is intercepted and sent to Fara
    4. Fara executes the tool and returns result
    5. Result is returned to dialogue LLM for response generation
    """

    def __init__(
        self,
        dialogue_manager: Any,
        fara_manager: Any,
    ):
        """
        Initialize the tool use integration.

        Args:
            dialogue_manager: Standard LLM manager
            fara_manager: Fara model manager
        """
        self._dialogue_manager = dialogue_manager
        self._fara_manager = fara_manager
        self._tool_call_interceptor = None

    def register_tool_interceptor(self) -> None:
        """
        Register Fara as the tool call interceptor for the dialogue LLM.

        This hooks into the dialogue LLM's tool execution flow and redirects
        certain tool calls to Fara.
        """
        # This would hook into the workflow_manager's tool execution
        # For now, this is a placeholder for the integration point
        logger.info("Tool interceptor registered for Fara integration")

    def execute_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool call using Fara.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            context: Optional context for the execution

        Returns:
            Tool execution result
        """
        # Map tool calls to Fara actions
        fara_action_map = {
            "web_search": "web_search",
            "visit_url": "visit_url",
            "click_element": "left_click",
            "type_text": "type",
            "scroll_page": "scroll",
        }

        if tool_name in fara_action_map:
            fara_action = fara_action_map[tool_name]
            # Convert tool args to Fara format
            fara_args = self._convert_tool_args(tool_name, tool_args)

            # This would need a screenshot - for now return placeholder
            return {
                "tool": tool_name,
                "fara_action": fara_action,
                "args": fara_args,
                "status": "pending_screenshot",
            }
        else:
            # Not a Fara-compatible tool
            return {
                "tool": tool_name,
                "status": "not_fara_compatible",
            }

    def _convert_tool_args(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert standard tool arguments to Fara action format."""
        if tool_name == "web_search":
            return {"action": "web_search", "query": args.get("query", "")}
        elif tool_name == "visit_url":
            return {"action": "visit_url", "url": args.get("url", "")}
        elif tool_name == "type_text":
            return {
                "action": "type",
                "text": args.get("text", ""),
                "coordinate": args.get("coordinates", []),
            }
        else:
            return {"action": tool_name, **args}
