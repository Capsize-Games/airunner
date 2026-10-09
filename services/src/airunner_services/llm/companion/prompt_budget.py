"""Prompt scoping and budget trimming for B10 composition.

Chatbot scope is enforced again at composition time (defense in
depth behind the B03 repository): any fact, episode, or turn naming
another chatbot is dropped and recorded, never rendered.

Truncation policy (applied in this order until the prompt fits
``ContextBudget.max_prompt_tokens``):

1. Cap facts to ``max_facts`` (best-ranked kept) and recent turns
   to ``max_recent_turns`` (newest kept).
2. Drop episodic summaries, oldest first.
3. Drop facts, lowest-ranked first.
4. Drop recent turns, oldest first.
5. Truncate the narrative to the remaining allowance.

Token estimates reuse B09's ``estimate_tokens`` so every companion
budget stays comparable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from .narrative import (
    estimate_tokens,
    fit_to_budget,
    sanitize_memory_text,
)

if TYPE_CHECKING:
    from .contracts import ChatbotId, ContextBudget
    from .memory_repository import TurnRecord
    from .prompt import PromptInputs
    from .prompt_sections import EpisodeSnippet
    from .recall import CitedFact


class _WorkingSet:
    """Truncatable view of one composition's memory inputs."""

    def __init__(self, inputs: PromptInputs, budget: ContextBudget) -> None:
        self.dropped: List[str] = []
        self.facts = _scoped_facts(inputs, self.dropped)
        self.facts = self.facts[: budget.max_facts]
        self.episodes = _scoped_episodes(inputs, self.dropped)
        self.turns = _capped_turns(inputs, budget, self.dropped)
        self.narrative = _clean_narrative(inputs)

    def shrink_once(self) -> bool:
        """Drop the next lowest-priority item; False if pinned."""
        if self.episodes:
            removed = self.episodes.pop(0)
            self.dropped.append(
                f"episode:{int(removed.session_id)}:over-budget"
            )
            return True
        if self.facts:
            removed_fact = self.facts.pop()
            self.dropped.append(f"fact:{removed_fact.fact_id}:over-budget")
            return True
        if self.turns:
            self.turns.pop(0)
            self.dropped.append("turn:oldest:over-budget")
            return True
        return False

    def fit_narrative(self, budget: ContextBudget, total: int) -> bool:
        """Fit the narrative to the allowance; False if none."""
        if not self.narrative:
            return False
        allowance = budget.max_prompt_tokens - (
            total - estimate_tokens(self.narrative)
        )
        if allowance <= 0:
            self.narrative = None
            self.dropped.append("narrative:over-budget")
            return True
        self.narrative = (
            fit_to_budget(self.narrative, allowance * 4, allowance) or None
        )
        self.dropped.append(_narrative_drop(self.narrative))
        return True


def _narrative_drop(narrative: Optional[str]) -> str:
    """The drop record for a truncated (or emptied) narrative."""
    if narrative is None:
        return "narrative:over-budget"
    return "narrative:truncated"


def _scoped_facts(inputs: PromptInputs, dropped: List[str]) -> List[CitedFact]:
    """This chatbot's facts, best-ranked first (stable)."""
    kept = [
        fact
        for fact in inputs.facts
        if _keep_fact(inputs.chatbot_id, fact, dropped)
    ]
    return sorted(kept, key=lambda fact: (-(fact.score or 0.0), fact.fact_id))


def _keep_fact(
    chatbot_id: ChatbotId, fact: CitedFact, dropped: List[str]
) -> bool:
    """True when one fact belongs to this chatbot's prompt."""
    if int(fact.chatbot_id) == int(chatbot_id):
        return True
    dropped.append(f"fact:{fact.fact_id}:cross-chatbot")
    return False


def _scoped_episodes(
    inputs: PromptInputs, dropped: List[str]
) -> List[EpisodeSnippet]:
    """This chatbot's episodes, oldest first (stable)."""
    kept = [
        episode
        for episode in inputs.episodes
        if _keep_episode(inputs.chatbot_id, episode, dropped)
    ]
    return sorted(kept, key=lambda episode: int(episode.session_id))


def _keep_episode(
    chatbot_id: ChatbotId,
    episode: EpisodeSnippet,
    dropped: List[str],
) -> bool:
    """True when one episode belongs to this chatbot's prompt."""
    if int(episode.chatbot_id) == int(chatbot_id):
        return True
    dropped.append(f"episode:{int(episode.session_id)}:cross-chatbot")
    return False


def _capped_turns(
    inputs: PromptInputs, budget: ContextBudget, dropped: List[str]
) -> List[TurnRecord]:
    """This chatbot's newest turns, oldest first, within cap."""
    kept = [
        turn
        for turn in inputs.recent_turns
        if _keep_turn(inputs.chatbot_id, turn, dropped)
    ]
    ordered = sorted(
        kept,
        key=lambda turn: (turn.turn_index or 0, turn.turn_id or 0),
    )
    if budget.max_recent_turns <= 0:
        return []
    return ordered[-budget.max_recent_turns :]


def _keep_turn(
    chatbot_id: ChatbotId, turn: TurnRecord, dropped: List[str]
) -> bool:
    """True when one turn belongs to this chatbot's prompt."""
    if int(turn.chatbot_id) == int(chatbot_id):
        return True
    dropped.append(f"turn:{turn.turn_id}:cross-chatbot")
    return False


def _clean_narrative(inputs: PromptInputs) -> Optional[str]:
    """This chatbot's narrative, sanitized (None when blank)."""
    if inputs.narrative is None:
        return None
    clean = sanitize_memory_text(inputs.narrative)
    return clean if clean else None


__all__ = ["_WorkingSet"]
