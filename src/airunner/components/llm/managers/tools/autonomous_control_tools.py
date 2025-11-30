"""Autonomous application control tools - giving the LLM full control over the application."""

from typing import Callable, Optional
import json

from langchain.tools import tool

from airunner.components.tools.base_tool import BaseTool
from airunner.enums import SignalCode


class AutonomousControlTools(BaseTool):
    """Mixin class providing full autonomous control over the application.

    These tools allow the LLM to control the application like a user would,
    enabling true autonomous operation with human-in-the-loop oversight.
    """

    def get_application_state_tool(self) -> Callable:
        """Get current application state and configuration."""

        @tool
        def get_application_state() -> str:
            """Get the current state of the application.

            Returns information about active models, current settings,
            loaded documents, system resources, and application status.
            Essential for understanding the application's current context.

            Returns:
                JSON-formatted application state

            Usage:
                get_application_state()
            """
            try:
                state = {
                    "application": {
                        "name": "AI Runner",
                        "version": "2.0",
                        "mode": "autonomous",
                    },
                    "llm": {
                        "active": True,
                        "model": getattr(
                            self, "active_llm_model_name", "unknown"
                        ),
                        "tools_count": (
                            len(self.get_all_tools())
                            if hasattr(self, "get_all_tools")
                            else 0
                        ),
                    },
                    "conversation": {
                        "current_id": getattr(
                            self, "current_conversation_id", None
                        ),
                        "has_context": True,
                    },
                    "capabilities": {
                        "image_generation": True,
                        "rag": self.rag_manager is not None,
                        "knowledge_base": True,
                        "web_access": True,
                        "code_execution": True,
                    },
                }

                return json.dumps(state, indent=2)

            except Exception as e:
                self.logger.error(f"Error getting application state: {e}")
                return f"Error getting application state: {str(e)}"

        return get_application_state

    def schedule_task_tool(self) -> Callable:
        """Schedule a task to run at a specific time or interval."""

        @tool
        def schedule_task(
            task_name: str,
            description: str,
            when: str,
            params: Optional[dict] = None,
        ) -> str:
            """Schedule a task to run automatically.

            Enables autonomous operation by scheduling tasks without user intervention.
            Tasks can be one-time or recurring.

            Args:
                task_name: Descriptive name for the task
                description: Description of what the task will do
                when: When to run ("now", natural language like "in 5 minutes", or schedule syntax)
                params: Optional parameters dict for the task (will be forwarded unchanged)

            Returns:
                Confirmation with task ID

            Examples:
                schedule_task("Morning Summary", "summarize_conversations", "daily:09:00")
                schedule_task("Hourly News", "check_news", "hourly", '{"category": "tech"}')
                schedule_task("Generate Art", "generate_image", "once:2025-10-24 15:00", '{"prompt": "sunset"}')
            """
            try:
                # Emit signal to schedule task (forward params dict directly)
                self.emit_signal(
                    SignalCode.SCHEDULE_TASK_SIGNAL,
                    {
                        "task_name": task_name,
                        "description": description,
                        "when": when,
                        "params": params,
                    },
                )

                return f"Scheduled task '{task_name}' to run {when}: {description}"

            except Exception as e:
                self.logger.error(f"Error scheduling task: {e}")
                return f"Error scheduling task: {str(e)}"

        return schedule_task

    def set_application_mode_tool(self) -> Callable:
        """Set the application's operational mode."""

        @tool
        def set_application_mode(
            mode: str, reason: str, auto_approve: bool = False
        ) -> str:
            """Set the application's operational mode.

            Controls the level of autonomy and user interaction required.

            Modes:
            - "autonomous": Full autonomous operation, minimal user prompts
            - "supervised": Agent proposes actions, user approves
            - "manual": Traditional user-driven operation
            - "hybrid": Mix of autonomous and manual based on context

            Args:
                mode: Operational mode to set
                auto_approve: Whether to automatically approve agent actions (use carefully!)

            Returns:
                Confirmation message

            Usage:
                set_application_mode("autonomous", auto_approve=True)
            """
            try:
                valid_modes = ["autonomous", "supervised", "manual", "hybrid"]

                if mode not in valid_modes:
                    return f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"

                payload = {"mode": mode, "reason": reason}
                # Only include auto_approve if True to match test expectations
                if auto_approve:
                    payload["auto_approve"] = True

                self.emit_signal(
                    SignalCode.SET_APPLICATION_MODE_SIGNAL,
                    payload,
                )

                approval_str = " with auto-approval" if auto_approve else ""
                return f"Set application mode to '{mode}'{approval_str}. Reason: {reason}"

            except Exception as e:
                self.logger.error(f"Error setting application mode: {e}")
                return f"Error setting application mode: {str(e)}"

        return set_application_mode

    def request_user_input_tool(self) -> Callable:
        """Request input or approval from the user."""

        @tool
        def request_user_input(
            prompt: str,
            input_type: str = "text",
            options: Optional[str] = None,
            timeout_seconds: int = 300,
        ) -> str:
            """Request input or decision from the user.

            Enables human-in-the-loop oversight for critical decisions.
            The agent can ask the user for guidance when needed.

            Args:
                prompt: Question or prompt to show the user
                input_type: Type of input - "text", "yes_no", "choice", "approval"
                options: For "choice" type - JSON list of options
                timeout_seconds: How long to wait for response (default 300s/5min)

            Returns:
                User's response or timeout message

            Examples:
                request_user_input("Should I delete old conversations?", "yes_no")
                request_user_input("Choose a style:", "choice", '["modern", "classic", "minimal"]')
                request_user_input("Approve this image generation?", "approval")
            """
            try:
                request_data = {
                    "prompt": prompt,
                    "input_type": input_type,
                    "timeout_seconds": timeout_seconds,
                }

                if options:
                    try:
                        request_data["options"] = json.loads(options)
                    except json.JSONDecodeError:
                        return f"Error: options must be valid JSON list. Got: {options}"

                # This would typically block and wait for user response
                # Implementation depends on UI/notification system
                self.emit_signal(
                    SignalCode.REQUEST_USER_INPUT_SIGNAL, request_data
                )

                return f"Requested user input: '{prompt}' (waiting for response...)"

            except Exception as e:
                self.logger.error(f"Error requesting user input: {e}")
                return f"Error requesting user input: {str(e)}"

        return request_user_input

    def analyze_user_behavior_tool(self) -> Callable:
        """Analyze user behavior patterns to better serve them."""

        @tool
        def analyze_user_behavior(days_back: int = 30) -> str:
            """Analyze user interaction patterns to improve service.

            Examines user behavior, preferences, and usage patterns to provide
            more personalized and proactive assistance.

            Args:
                days_back: Number of days of history to analyze (default 30)

            Returns:
                Analysis summary with insights and recommendations

            Usage:
                analyze_user_behavior(days_back=7)
            """
            try:
                from airunner.components.data.session_manager import (
                    session_scope,
                )
                from airunner.components.llm.data.conversation import (
                    Conversation,
                )
                from datetime import datetime, timedelta

                with session_scope() as session:
                    cutoff = datetime.now() - timedelta(days=days_back)
                    conversations = (
                        session.query(Conversation)
                        .filter(Conversation.timestamp >= cutoff)
                        .all()
                    )

                    if not conversations:
                        return f"No conversation data found in the last {days_back} days."

                    # Analyze patterns
                    total_conversations = len(conversations)
                    total_messages = sum(
                        len(c.value) if c.value else 0 for c in conversations
                    )
                    avg_messages_per_conv = (
                        total_messages / total_conversations
                        if total_conversations > 0
                        else 0
                    )

                    # Analyze topics (simple keyword extraction)
                    topics = {}
                    for conv in conversations:
                        if conv.title:
                            words = conv.title.lower().split()
                            for word in words:
                                if len(word) > 4:  # Skip short words
                                    topics[word] = topics.get(word, 0) + 1

                    top_topics = sorted(
                        topics.items(), key=lambda x: x[1], reverse=True
                    )[:5]

                    # Build analysis
                    analysis_parts = [
                        f"User Behavior Analysis (last {days_back} days):",
                        f"\nActivity:",
                        f"  - Total conversations: {total_conversations}",
                        f"  - Total messages: {total_messages}",
                        f"  - Avg messages/conversation: {avg_messages_per_conv:.1f}",
                        f"  - Conversations per day: {total_conversations / days_back:.1f}",
                    ]

                    if top_topics:
                        analysis_parts.append("\nTop Topics:")
                        for topic, count in top_topics:
                            analysis_parts.append(
                                f"  - {topic}: {count} times"
                            )

                    analysis_parts.append("\nRecommendations:")
                    if avg_messages_per_conv < 5:
                        analysis_parts.append(
                            "  - User prefers brief interactions - keep responses concise"
                        )
                    else:
                        analysis_parts.append(
                            "  - User engages in detailed discussions - provide thorough responses"
                        )

                    if total_conversations > 20:
                        analysis_parts.append(
                            "  - High activity user - consider proactive suggestions"
                        )

                    return "\n".join(analysis_parts)

            except Exception as e:
                self.logger.error(f"Error analyzing user behavior: {e}")
                return f"Error analyzing user behavior: {str(e)}"

        return analyze_user_behavior

    def propose_action_tool(self) -> Callable:
        """Propose an action to the user for approval."""

        @tool
        def propose_action(
            action: str,
            rationale: str,
            confidence: float = 1.0,
            requires_approval: bool = False,
        ) -> str:
            """Propose an action to the user with rationale.

            Enables the agent to suggest actions and explain why.
            Supports both supervised (user approval) and autonomous (auto-execute) modes.

            Args:
                action_name: Name of the action (e.g., "clean_old_conversations")
                description: What the action will do
                rationale: Why this action is recommended
                auto_execute: If True, execute without waiting for approval (use carefully!)

            Returns:
                Proposal status or execution result

            Usage:
                propose_action(
                    "organize_conversations",
                    "Group conversations by topic and add titles",
                    "Will make it easier to find past discussions"
                )
            """
            try:
                proposal = {
                    "action": action,
                    "rationale": rationale,
                    "confidence": confidence,
                    "requires_approval": requires_approval,
                }

                self.emit_signal(
                    SignalCode.AGENT_ACTION_PROPOSAL_SIGNAL, proposal
                )

                base = f"Proposed action: {action}\nRationale: {rationale}\nConfidence: {confidence:.2f}"
                if requires_approval:
                    return base + "\nAwaiting user approval..."
                return base + "\nExecuting automatically."

            except Exception as e:
                self.logger.error(f"Error proposing action: {e}")
                return f"Error proposing action: {str(e)}"

        return propose_action

    def monitor_system_health_tool(self) -> Callable:
        """Monitor system health and resource usage."""

        @tool
        def monitor_system_health() -> str:
            """Monitor system health, resources, and potential issues.

            Checks CPU, memory, disk usage, and application health.
            Helps the agent be proactive about system issues.

            Returns:
                System health report

            Usage:
                monitor_system_health()
            """
            try:
                import psutil
                import os

                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                # Process info
                process = psutil.Process(os.getpid())
                process_memory = process.memory_info().rss / 1024 / 1024  # MB

                health_report = [
                    "System Health Report:",
                    f"CPU usage: {cpu_percent}%",
                    f"Memory usage: {memory.percent}%",
                    f"Disk usage: {disk.percent}%",
                    f"Process memory (MB): {process_memory:.1f}",
                ]

                # Health warnings
                warnings = []
                if cpu_percent > 80:
                    warnings.append("⚠ High CPU usage detected")
                if memory.percent > 85:
                    warnings.append("⚠ High memory usage detected")
                if disk.percent > 90:
                    warnings.append("⚠ Disk space running low")

                if warnings:
                    health_report.append("Warnings:")
                    health_report.extend([w for w in warnings])
                else:
                    health_report.append("All systems healthy")

                return "\n".join(health_report)

            except Exception as e:
                self.logger.error(f"Error monitoring system health: {e}")
                return f"Error monitoring system health: {str(e)}"

        return monitor_system_health

    def log_agent_decision_tool(self) -> Callable:
        """Log agent decisions for transparency and debugging."""

        @tool
        def log_agent_decision(
            decision: str, reasoning: str, confidence: float = 1.0
        ) -> str:
            """Log an agent decision with reasoning.

            Creates a transparent record of agent decision-making.
            Useful for debugging, auditing, and improving the agent.

            Args:
                decision: What decision was made
                reasoning: Why this decision was made
                confidence: Confidence level 0.0-1.0 (default 1.0)

            Returns:
                Confirmation message

            Usage:
                log_agent_decision(
                    "Summarized old conversations",
                    "User has 50+ conversations, summarizing will improve search",
                    confidence=0.9
                )
            """
            try:
                import datetime

                log_entry = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "decision": decision,
                    "reasoning": reasoning,
                    "confidence": confidence,
                }

                # Store in knowledge base for learning
                from airunner.components.knowledge.knowledge_base import (
                    get_knowledge_base,
                )

                kb = get_knowledge_base()
                kb.add_fact(
                    fact=f"Decision: {decision}. Reasoning: {reasoning}",
                    section="Notes",
                )

                self.logger.info(f"Agent decision logged: {decision}")
                return f"Logged agent decision: {decision} (confidence: {int(confidence*100)}%)"

            except Exception as e:
                self.logger.error(f"Error logging decision: {e}")
                return f"Error logging decision: {str(e)}"

        return log_agent_decision
