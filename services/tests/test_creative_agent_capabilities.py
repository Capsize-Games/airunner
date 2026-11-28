"""Unit tests for CreativeAgent capability registration split.

The four registration blocks were split into writing/style groups
to keep _register_capabilities within the long-function threshold.
These tests pin the capability names, priorities, and keyword sets.
"""

from unittest.mock import MagicMock

from airunner_services.agents.expert_agents.creative_agent import (
    CreativeExpertAgent,
)


def _make_agent():
    agent = CreativeExpertAgent.__new__(CreativeExpertAgent)
    agent.register_capability = MagicMock()
    return agent


def _names(agent):
    return [call.kwargs["name"] for call in agent.register_capability.call_args_list]


def _priority(agent, name):
    for call in agent.register_capability.call_args_list:
        if call.kwargs["name"] == name:
            return call.kwargs["priority"]
    raise KeyError(name)


def test_all_four_capabilities_registered_in_order():
    agent = _make_agent()
    agent._register_capabilities()
    assert _names(agent) == [
        "creative_writing",
        "brainstorming",
        "rewriting",
        "style_adaptation",
    ]


def test_priorities_preserved():
    agent = _make_agent()
    agent._register_capabilities()
    assert _priority(agent, "creative_writing") == 9
    assert _priority(agent, "brainstorming") == 8
    assert _priority(agent, "rewriting") == 7
    assert _priority(agent, "style_adaptation") == 7


def test_writing_group_only_registers_writing_caps():
    agent = _make_agent()
    agent._register_writing_capabilities()
    assert _names(agent) == ["creative_writing", "brainstorming"]


def test_style_group_only_registers_style_caps():
    agent = _make_agent()
    agent._register_style_capabilities()
    assert _names(agent) == ["rewriting", "style_adaptation"]


def test_keyword_sets_preserved():
    agent = _make_agent()
    agent._register_capabilities()
    by_name = {
        call.kwargs["name"]: call.kwargs["keywords"]
        for call in agent.register_capability.call_args_list
    }
    assert by_name["creative_writing"] == [
        "write", "story", "article", "blog", "content",
        "compose", "draft", "creative", "narrative", "fiction",
    ]
    assert by_name["brainstorming"] == [
        "brainstorm", "ideas", "suggest", "propose", "come up with",
        "think of", "generate ideas", "creative ideas",
    ]
    assert by_name["rewriting"] == [
        "rephrase", "rewrite", "paraphrase", "different way",
        "another way", "reword", "improve", "polish",
    ]
    assert by_name["style_adaptation"] == [
        "style", "tone", "voice", "formal", "casual",
        "professional", "friendly", "technical", "simple",
    ]
