import pytest
from airunner.utils.text.formatter_extended import FormatterExtended


def test_is_latex():
    assert FormatterExtended._is_latex("$x^2$")
    assert FormatterExtended._is_latex("$$E=mc^2$$")
    assert FormatterExtended._is_latex(r"\[a+b\]")
    assert FormatterExtended._is_latex(r"\(a+b\)")
    assert FormatterExtended._is_latex(r"\frac{a}{b}")
    assert not FormatterExtended._is_latex("plain text")


def test_is_latex_bracket_and_paren():
    # These should not match due to double backslash bug in _is_latex
    assert FormatterExtended._is_latex("\\[a+b\\]")
    assert FormatterExtended._is_latex("\\(a+b\\)")
    # These should also match with single backslash (for robustness)
    assert FormatterExtended._is_latex(r"\[a+b\]")
    assert FormatterExtended._is_latex(r"\(a+b\)")
    # Test both double and single backslash bracket/paren LaTeX detection
    assert FormatterExtended._is_latex(r"\\[a+b\\]")
    assert FormatterExtended._is_latex(r"\\(a+b\\)")
    # Accept single backslash for robustness
    assert FormatterExtended._is_latex(r"\[a+b\]")
    assert FormatterExtended._is_latex(r"\(a+b\)")


def test_is_pure_latex():
    assert FormatterExtended._is_pure_latex("$$E=mc^2$$")
    assert FormatterExtended._is_pure_latex("$x^2$")
    assert FormatterExtended._is_pure_latex(r"\[a+b\]")
    assert FormatterExtended._is_pure_latex(r"\(a+b\)")
    assert not FormatterExtended._is_pure_latex("text $x^2$")


def test_is_markdown():
    assert FormatterExtended._is_markdown("# Header")
    assert FormatterExtended._is_markdown("- item")
    assert FormatterExtended._is_markdown("* item")
    assert FormatterExtended._is_markdown("1. item")
    assert FormatterExtended._is_markdown("**bold**")
    assert FormatterExtended._is_markdown("`code`")
    assert FormatterExtended._is_markdown("[link](url)")
    assert FormatterExtended._is_markdown("> quote")
    assert not FormatterExtended._is_markdown("plain text")


def test_format_content_types():
    # Mixed
    mixed = "Text before $$x^2$$ text after"
    result = FormatterExtended.format_content(mixed)
    assert result["type"] == FormatterExtended.FORMAT_MIXED
    assert any(p["type"] == "latex" for p in result["parts"])
    # Pure LaTeX
    latex = "$$x^2$$"
    result = FormatterExtended.format_content(latex)
    assert result["type"] == FormatterExtended.FORMAT_LATEX
    # Markdown
    md = "# Header\nSome text"
    result = FormatterExtended.format_content(md)
    assert result["type"] == FormatterExtended.FORMAT_MARKDOWN
    # Plaintext
    pt = "Just text"
    result = FormatterExtended.format_content(pt)
    assert result["type"] == FormatterExtended.FORMAT_PLAINTEXT


def test_strip_nonlinguistic():
    text = "$$x^2$$ `code` plain"
    out = FormatterExtended.strip_nonlinguistic(text)
    assert "x^2" not in out and "code" not in out
    assert "plain" in out


def test_to_speakable_text():
    text = "$$x^2$$ `code`"
    out = FormatterExtended.to_speakable_text(text)
    assert "[formula:" in out
    assert "[code block omitted]" not in out  # only for code blocks
    text2 = "```python\nprint(1)\n```"
    out2 = FormatterExtended.to_speakable_text(text2)
    assert "[code block omitted]" in out2
