"""Builders for autonomous control insight and monitoring tools."""

from __future__ import annotations

import os
from typing import Callable

import psutil
from langchain_core.tools import tool

from airunner_services.knowledge import get_knowledge_base
from airunner_services.tools.base_tool import BaseTool


def _tool_error(owner: BaseTool, action: str, exc: Exception) -> str:
    """Log and format one autonomous insight-tool error."""
    owner.logger.error("Error %s: %s", action, exc)
    return f"Error {action}: {exc}"


def _propose_action_result(
    owner: BaseTool,
    action: str,
    rationale: str,
    confidence: float,
    requires_approval: bool,
) -> str:
    """Submit one action proposal and return the agent-facing status."""
    proposal = {
        "action": action,
        "rationale": rationale,
        "confidence": confidence,
        "requires_approval": requires_approval,
    }
    if not owner.dispatch_tool_action("agent_action_proposal", proposal):
        return "Action proposals are unavailable in this runtime."
    base = (
        f"Proposed action: {action}\nRationale: {rationale}\n"
        f"Confidence: {confidence:.2f}"
    )
    if requires_approval:
        return base + "\nAwaiting user approval..."
    return base + "\nExecuting automatically."


def build_propose_action_tool(owner: BaseTool) -> Callable:
    """Build the action-proposal tool."""

    @tool
    def propose_action(
        action: str,
        rationale: str,
        confidence: float = 1.0,
        requires_approval: bool = False,
    ) -> str:
        """Propose one action to the user."""
        try:
            return _propose_action_result(
                owner,
                action,
                rationale,
                confidence,
                requires_approval,
            )
        except Exception as exc:
            return _tool_error(owner, "proposing action", exc)

    return propose_action


def _health_warning_lines(
    cpu_percent: float,
    memory_percent: float,
    disk_percent: float,
) -> list[str]:
    """Return warning lines for one health snapshot."""
    warnings = []
    if cpu_percent > 80:
        warnings.append("⚠ High CPU usage detected")
    if memory_percent > 85:
        warnings.append("⚠ High memory usage detected")
    if disk_percent > 90:
        warnings.append("⚠ Disk space running low")
    return warnings


def _monitor_system_health_result() -> str:
    """Return one system health report."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    process = psutil.Process(os.getpid())
    process_memory = process.memory_info().rss / 1024 / 1024
    lines = [
        "System Health Report:",
        f"CPU usage: {cpu_percent}%",
        f"Memory usage: {memory.percent}%",
        f"Disk usage: {disk.percent}%",
        f"Process memory (MB): {process_memory:.1f}",
    ]
    warnings = _health_warning_lines(cpu_percent, memory.percent, disk.percent)
    if warnings:
        return "\n".join(lines + ["Warnings:", *warnings])
    return "\n".join(lines + ["All systems healthy"])


def build_monitor_system_health_tool(owner: BaseTool) -> Callable:
    """Build the system health monitoring tool."""

    @tool
    def monitor_system_health() -> str:
        """Monitor system health and resources."""
        try:
            return _monitor_system_health_result()
        except Exception as exc:
            return _tool_error(owner, "monitoring system health", exc)

    return monitor_system_health


def _log_agent_decision_result(
    owner: BaseTool,
    decision: str,
    reasoning: str,
    confidence: float,
) -> str:
    """Persist one agent decision note for transparency."""
    kb = get_knowledge_base()
    kb.add_fact(
        fact=f"Decision: {decision}. Reasoning: {reasoning}",
        section="Notes",
    )
    owner.logger.info("Agent decision logged: %s", decision)
    return (
        f"Logged agent decision: {decision} "
        f"(confidence: {int(confidence * 100)}%)"
    )


def build_log_agent_decision_tool(owner: BaseTool) -> Callable:
    """Build the agent-decision logging tool."""

    @tool
    def log_agent_decision(
        decision: str,
        reasoning: str,
        confidence: float = 1.0,
    ) -> str:
        """Log one agent decision and its reasoning."""
        try:
            return _log_agent_decision_result(
                owner,
                decision,
                reasoning,
                confidence,
            )
        except Exception as exc:
            return _tool_error(owner, "logging decision", exc)

    return log_agent_decision
