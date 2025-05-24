"""
Unit tests for airunner.utils.llm.parse_template.parse_template
"""

import pytest


def test_parse_template_causallm(monkeypatch):
    monkeypatch.setattr(
        "airunner.settings.AIRUNNER_DEFAULT_LLM_HF_PATH", "hf-path"
    )
    from airunner.utils import parse_template

    tpl = {
        "system_instructions": "sys",
        "model": "hf-path",
        "llm_category": "causallm",
        "template": "body",
    }
    out = parse_template(tpl)
    assert "[INST]<<SYS>>" in out
    assert "sys" in out
    assert "body" in out


def test_parse_template_nonmatch(monkeypatch):
    monkeypatch.setattr(
        "airunner.settings.AIRUNNER_DEFAULT_LLM_HF_PATH", "hf-path"
    )
    from airunner.utils import parse_template

    tpl = {
        "system_instructions": "sys",
        "model": "other",
        "llm_category": "causallm",
        "template": "body",
    }
    out = parse_template(tpl)
    assert out == ""
