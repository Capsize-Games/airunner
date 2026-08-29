"""Tests for the deterministic madlibs Prompt Builder engine.

The engine is pure Python (no Qt), so these tests run without a GUI or a
database. They lock down the structure of the generated prompts for both
Z-Image Turbo (6-part single prompt, no negative prompt) and SDXL (layered
positive + negative "bug list").
"""

from __future__ import annotations

import pytest

from airunner.components.art.gui.windows.prompt_builder.prompt_builder_engine import (
    SCENE_LOCATIONS,
    PromptBuilderEngine,
    PromptBuilderState,
)


@pytest.fixture
def engine() -> PromptBuilderEngine:
    return PromptBuilderEngine()


def _sdxl_state(seed: int = 42, **overrides) -> PromptBuilderState:
    defaults = dict(
        randomize=True,
        seed=seed,
        target_generator="stablediffusion",
    )
    defaults.update(overrides)
    return PromptBuilderState(**defaults)


def _zimage_state(seed: int = 42, **overrides) -> PromptBuilderState:
    defaults = dict(
        randomize=True,
        seed=seed,
        target_generator="zimage",
    )
    defaults.update(overrides)
    return PromptBuilderState(**defaults)


# -- Z-Image ----------------------------------------------------------------


def test_zimage_has_no_negative_prompt(engine):
    result = engine.build(_zimage_state())
    assert result.prompt
    assert result.negative_prompt == ""


def test_zimage_covers_six_sections(engine):
    result = engine.build(_zimage_state(seed=1))
    prompt = result.prompt.lower()

    # Subject + scene + composition + lighting + style + polish.
    assert " shot" in prompt  # composition/framing
    assert "light" in prompt  # lighting section
    assert "photography" in prompt or "painting" in prompt  # style
    assert "focus" in prompt or "detail" in prompt  # polish
    assert "style" in prompt or "palette" in prompt  # style/color


def test_zimage_is_deterministic_for_same_seed(engine):
    a = engine.build(_zimage_state(seed=123))
    b = engine.build(_zimage_state(seed=123))
    assert a.prompt == b.prompt


def test_zimage_differs_for_different_seeds(engine):
    a = engine.build(_zimage_state(seed=1))
    b = engine.build(_zimage_state(seed=2))
    assert a.prompt != b.prompt


def test_zimage_respects_explicit_values(engine):
    state = _zimage_state(
        seed=1,
        randomize=False,
        subject="a lighthouse keeper",
        scene="a windswept coastal cliff",
        shot_type="Wide shot",
        lighting="volumetric lighting through atmospheric haze",
        style_group="Cinematic",
        style_detail="1980s sci-fi film still aesthetic",
    )
    result = engine.build(state)
    assert "lighthouse keeper" in result.prompt
    assert "coastal cliff" in result.prompt
    assert "Wide shot" in result.prompt
    assert "volumetric" in result.prompt
    assert "1980s sci-fi" in result.prompt


def test_zimage_applies_prefix_and_suffix(engine):
    state = _zimage_state(prefix="masterpiece", suffix="ultra detailed")
    result = engine.build(state)
    assert result.prompt.startswith("masterpiece, ")
    assert result.prompt.endswith(", ultra detailed")


# -- SDXL -------------------------------------------------------------------


def test_sdxl_has_negative_prompt(engine):
    result = engine.build(_sdxl_state())
    assert result.prompt
    assert result.negative_prompt
    assert "watermark" in result.negative_prompt
    assert "extra fingers" in result.negative_prompt


def test_sdxl_is_deterministic_for_same_seed(engine):
    a = engine.build(_sdxl_state(seed=99))
    b = engine.build(_sdxl_state(seed=99))
    assert a.prompt == b.prompt


def test_sdxl_negative_includes_style_bug_list(engine):
    state = _sdxl_state(seed=1, style_group="Photorealistic")
    result = engine.build(state)
    assert "CGI" in result.negative_prompt
    assert "3d render" in result.negative_prompt


def test_sdxl_custom_negative_appended(engine):
    state = _sdxl_state(seed=1, custom_negative="out of frame, cropped")
    result = engine.build(state)
    assert "out of frame" in result.negative_prompt
    assert "cropped" in result.negative_prompt


def test_sdxl_includes_lighting_and_style(engine):
    result = engine.build(_sdxl_state(seed=2))
    prompt = result.prompt.lower()
    assert "light" in prompt
    assert "palette" in prompt or "photography" in prompt


# -- shared -----------------------------------------------------------------


def test_word_count_reported(engine):
    result = engine.build(_zimage_state())
    assert result.word_count > 0
    assert result.word_count == len(result.prompt.split())


def test_custom_subject_overrides_noun(engine):
    state = _zimage_state(
        randomize=False, custom_subject="a purple robot bartender"
    )
    result = engine.build(state)
    assert "purple robot bartender" in result.prompt


def test_fresh_seed_draws_different_prompt_each_build(engine):
    """seed=None must produce a different prompt on every build."""
    a = engine.build(_zimage_state(seed=None))
    b = engine.build(_zimage_state(seed=None))
    assert a.prompt != b.prompt


def test_subjects_and_scenes_vary_across_seeds(engine):
    """Across many seeds the subject and scene lists should be well-covered.

    This guards against the old same-index clumping where every slot drew
    from the same seeded RNG and kept landing on the same relative entries.
    """
    subjects = set()
    scenes = set()
    for seed in range(40):
        result = engine.build(_zimage_state(seed=seed))
        subject = result.prompt.split(",")[0].strip()
        # Scene appears after the subject/attributes/action; grab the phrase
        # that matches a known location.
        matched_scene = next(
            (loc for loc in SCENE_LOCATIONS if loc in result.prompt),
            None,
        )
        subjects.add(subject)
        if matched_scene:
            scenes.add(matched_scene)
    assert len(subjects) >= 10
    assert len(scenes) >= 8


def test_no_literal_random_leaks(engine):
    """The literal word 'Random' must never appear in a built prompt."""
    for seed in range(20):
        result = engine.build(_zimage_state(seed=seed))
        assert "Random" not in result.prompt


def test_quality_terms_are_positive_for_zimage(engine):
    """Z-Image cannot use negative prompts, so all polish is positive.

    Every quality phrase is positively framed (e.g. "sharp focus",
    "crisp details", "precise color accuracy") rather than negated
    ("no blur", "no artifacts").
    """
    negated_phrases = (
        "no blur",
        "no noise",
        "no artifacts",
        "without blur",
        "not blurry",
    )
    for seed in range(20):
        result = engine.build(_zimage_state(seed=seed))
        lower = result.prompt.lower()
        for phrase in negated_phrases:
            assert phrase not in lower
