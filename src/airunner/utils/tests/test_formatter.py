"""
Test suite for src/airunner/utils/text/formatter.py
Covers all public and private methods of Formatter.
"""

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
)
from airunner.utils.text.formatter import Formatter

import tempfile
import pytest


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$x^2 + y^2 = z^2$", True),
        ("$$E=mc^2$$", True),
        (r"\[a+b\]", True),
        (r"\(a+b\)", True),
        ("This is not latex", False),
        ("\\frac{a}{b}", True),
        ("alpha beta", False),
    ],
)
def test_is_latex(text, expected):
    assert Formatter._is_latex(text) is expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$$E=mc^2$$", True),
        ("$x^2$", True),
        (r"\[a+b\]", True),
        (r"\(a+b\)", True),
        ("$not closed", False),
        ("plain text", False),
    ],
)
def test_is_pure_latex(text, expected):
    assert Formatter._is_pure_latex(text) is expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# Header", True),
        ("* List item", True),
        ("**bold**", True),
        ("_italic_", True),
        ("`code`", True),
        ("[link](url)", True),
        ("> quote", True),
        ("plain text", False),
        ("no markdown here", False),
    ],
)
def test_is_markdown(text, expected):
    assert Formatter._is_markdown(text) is expected


def test_render_markdown_to_html():
    md = "# Title\n\nSome **bold** text."
    html = Formatter._render_markdown_to_html(md)
    assert "<h1>" in html and "<strong>" in html


def test_render_plaintext_to_image_creates_file():
    text = "Hello, world!\nSecond line."
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "out.png")
        result = Formatter._render_plaintext_to_image(text, out_path)
        assert os.path.exists(result)
        assert result == out_path


def test_render_plaintext_to_image_handles_error(monkeypatch):
    def fail_save(*a, **kw):
        raise OSError("fail")

    import PIL.Image

    monkeypatch.setattr(PIL.Image.Image, "save", fail_save)
    text = "test"
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "fail.png")
        result = Formatter._render_plaintext_to_image(text, out_path)
        assert result == ""


def test_render_plaintext_to_image_error(monkeypatch, tmp_path):
    from airunner.utils.text.formatter import Formatter

    def raise_exc(*a, **k):
        raise Exception("fail")

    monkeypatch.setattr("PIL.Image.new", raise_exc)
    out = Formatter._render_plaintext_to_image(
        "text", str(tmp_path / "out.png")
    )
    assert out == ""


@pytest.mark.parametrize(
    "content,expected_type",
    [
        ("# Header", Formatter._FORMAT_MARKDOWN),
        ("* List", Formatter._FORMAT_MARKDOWN),
        ("plain text", Formatter._FORMAT_PLAINTEXT),
        ("No markdown here", Formatter._FORMAT_PLAINTEXT),
    ],
)
def test_format_content_types(content, expected_type):
    result = Formatter.format_content(content)
    assert result["type"] == expected_type
    assert result["original_content"] == content
    if expected_type == Formatter._FORMAT_MARKDOWN:
        assert result["output"].startswith("<")
    else:
        assert result["output"] == content


def test_format_content_creates_output_dir(tmp_path):
    content = "plain text"
    outdir = tmp_path / "newdir"
    assert not outdir.exists()
    Formatter.format_content(content, str(outdir))
    assert outdir.exists()
