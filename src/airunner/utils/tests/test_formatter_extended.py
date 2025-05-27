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


def test_is_latex_edge_cases():
    # Should not match empty string or non-math text
    assert not FormatterExtended._is_latex("")
    assert not FormatterExtended._is_latex("no math here")
    # Should match LaTeX commands even without delimiters
    assert FormatterExtended._is_latex(r"\alpha")
    assert FormatterExtended._is_latex(r"\sum x")
    # Should not match if only a single $ at start or end
    assert not FormatterExtended._is_latex("$not closed")
    assert not FormatterExtended._is_latex("not closed$")


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


def test_is_markdown_all_branches():
    # Headers
    assert FormatterExtended._is_markdown("# Header")
    # Lists
    assert FormatterExtended._is_markdown("- item")
    assert FormatterExtended._is_markdown("* item")
    assert FormatterExtended._is_markdown("+ item")
    assert FormatterExtended._is_markdown("1. item")
    # Emphasis
    assert FormatterExtended._is_markdown("*em*")
    assert FormatterExtended._is_markdown("**bold**")
    assert FormatterExtended._is_markdown("_em_")
    assert FormatterExtended._is_markdown("__bold__")
    # Code blocks
    assert FormatterExtended._is_markdown("""```python\ncode\n```""")
    # Inline code
    assert FormatterExtended._is_markdown("`code`")
    # Links/Images
    assert FormatterExtended._is_markdown("[text](url)")
    # Blockquotes
    assert FormatterExtended._is_markdown("> quote")
    # Not markdown
    assert not FormatterExtended._is_markdown("plain text")
    assert not FormatterExtended._is_markdown("")


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


def test_to_speakable_text_edge_cases():
    # Only code block
    code = """```python\nprint('hi')\n```"""
    out = FormatterExtended.to_speakable_text(code)
    assert "[code block omitted]" in out
    # Only inline code
    inline = "This is `code`"
    out2 = FormatterExtended.to_speakable_text(inline)
    assert "[inline code omitted]" in out2
    # Only LaTeX
    latex = "$$x^2$$"
    out3 = FormatterExtended.to_speakable_text(latex)
    assert out3.startswith("[formula:")
    # Mixed LaTeX and text
    mixed = "before $x^2$ after"
    out4 = FormatterExtended.to_speakable_text(mixed)
    assert "[formula:" in out4
    assert "before" in out4 and "after" in out4


def test_render_markdown_to_html_handles_unknown_lexer(monkeypatch):
    # Simulate unknown language and unknown code for fallback
    def fake_get_lexer_by_name(lang, stripall=True):
        raise Exception("not found")

    def fake_guess_lexer(code, stripall=True):
        raise Exception("not found")

    monkeypatch.setattr("pygments.lexers.get_lexer_by_name", fake_get_lexer_by_name)
    monkeypatch.setattr("pygments.lexers.guess_lexer", fake_guess_lexer)
    md = """```unknownlang\nprint('hi')\n```"""
    # Should not raise, should fallback to text lexer
    html = FormatterExtended._render_markdown_to_html(md)
    assert "codehilite" in html


def test_is_latex_double_backslash():
    # Should match LaTeX with double backslash delimiters
    assert FormatterExtended._is_latex(r"\\[a+b\\]")
    assert FormatterExtended._is_latex(r"\\(a+b\\)")


def test_render_markdown_to_html_fallback_text_lexer(monkeypatch):
    # Simulate both get_lexer_by_name and guess_lexer raising ClassNotFound
    import pygments.util

    def raise_class_not_found(*a, **k):
        raise pygments.util.ClassNotFound("fail")

    monkeypatch.setattr("pygments.lexers.get_lexer_by_name", raise_class_not_found)
    monkeypatch.setattr("pygments.lexers.guess_lexer", raise_class_not_found)
    md = """```unknownlang\nprint('hi')\n```"""
    html = FormatterExtended._render_markdown_to_html(md)
    assert "codehilite" in html


def test_to_speakable_text_double_backslash_latex():
    # Should handle LaTeX with double backslash delimiters
    text = r"\\[a+b\\]"
    out = FormatterExtended.to_speakable_text(text)
    assert "[formula:" in out
    assert "a+b" in out


def test_to_speakable_text_double_backslash_paren():
    # Should handle LaTeX with double backslash paren delimiters
    text = r"\\(a+b\\)"
    out = FormatterExtended.to_speakable_text(text)
    assert "[formula:" in out
    assert "a+b" in out
