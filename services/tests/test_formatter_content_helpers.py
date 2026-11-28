"""Unit tests for FormatterExtended.format_content helpers.

_normalize_content_string and _split_mixed_latex were extracted to
keep format_content within the long-function threshold. These tests
pin the coercion and part-splitting behavior, plus the dispatched
format labels.
"""

from airunner_services.utils.text.formatter_extended import FormatterExtended


def test_normalize_passthrough_str():
    assert FormatterExtended._normalize_content_string("hi") == "hi"


def test_normalize_multimodal_list_joins_text_parts():
    content = [
        {"type": "text", "text": "hello"},
        {"type": "image_url", "image_url": {"url": "x"}},
        {"type": "text", "text": "world"},
    ]
    assert FormatterExtended._normalize_content_string(content) == "hello world"


def test_normalize_list_without_text_falls_back_to_repr():
    content = [{"type": "image"}]
    assert FormatterExtended._normalize_content_string(content) == str(content)


def test_normalize_other_types_coerced():
    assert FormatterExtended._normalize_content_string(42) == "42"
    assert FormatterExtended._normalize_content_string(None) == "None"


def test_split_mixed_latex_alternates():
    parts = FormatterExtended._split_mixed_latex("a $$x$$ b $$y$$ c")
    assert [p["type"] for p in parts] == ["text", "latex", "text", "latex", "text"]
    assert parts[1]["content"] == "$$x$$"


def test_split_mixed_latex_skips_empty_segments():
    parts = FormatterExtended._split_mixed_latex("$$x$$")
    assert parts == [{"type": "latex", "content": "$$x$$"}]


def test_format_content_plain_text():
    out = FormatterExtended.format_content("Just a plain sentence.")
    assert out["type"] == FormatterExtended.FORMAT_PLAINTEXT
    assert out["original_content"] == "Just a plain sentence."


def test_format_content_non_string_input_coerced():
    out = FormatterExtended.format_content(123)
    assert out["original_content"] == "123"


def test_format_content_mixed_latex_dispatches_mixed():
    out = FormatterExtended.format_content("text $$x$$ more")
    assert out["type"] == FormatterExtended.FORMAT_MIXED
    assert any(p["type"] == "latex" for p in out["parts"])


def test_format_content_pure_latex_dispatches_latex():
    out = FormatterExtended.format_content("$$E = mc^2$$")
    assert out["type"] == FormatterExtended.FORMAT_LATEX
