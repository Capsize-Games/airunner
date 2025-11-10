
from airunner.components.art.managers.stablediffusion import (
    prompt_utils,
    prompt_weight_bridge,
)


def test_format_prompt_basic():
    out = prompt_utils.format_prompt("cat", preset="")
    assert out == "cat"


def test_format_prompt_with_preset_and_additional():
    out = prompt_utils.format_prompt(
        "a", preset="b", additional_prompts=[{"prompt": "c"}]
    )
    assert "and()" in out


def test_apply_negative_and_preset():
    assert prompt_utils.apply_preset_to_prompt("p", "") == "p"
    assert prompt_utils.apply_negative_prompt("p", "n") == "p, n"


def test_prompt_weight_bridge_basic():
    p = "(abc)"
    res = prompt_weight_bridge.PromptWeightBridge.convert(p)
    assert isinstance(res, str)

    # test get_weight boundaries
    assert 0.0 <= prompt_weight_bridge.PromptWeightBridge.get_weight(1) <= 2.0
