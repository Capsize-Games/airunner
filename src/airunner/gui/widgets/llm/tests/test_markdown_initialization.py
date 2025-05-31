#!/usr/bin/env python3
"""
Test to validate markdown widget initialization and web engine startup.
"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from airunner.gui.widgets.llm.contentwidgets.markdown_widget import (
    MarkdownWidget,
)


@pytest.fixture
def markdown_widget(qtbot):
    """Create a markdown widget for testing."""
    # Mock the MathJax URL to avoid network requests during testing
    with patch("os.environ.get", return_value="0"):
        widget = MarkdownWidget()
        qtbot.addWidget(widget)
        return widget


class TestMarkdownInitialization:
    """Test class for markdown widget initialization."""

    def test_web_engine_initialization(self, qtbot, markdown_widget):
        """Test that the web engine initializes properly."""
        # The widget should have a webView
        assert hasattr(
            markdown_widget, "webView"
        ), "Should have webView attribute"
        assert (
            markdown_widget.webView is not None
        ), "webView should not be None"

    def test_mathjax_url_property(self, qtbot, markdown_widget):
        """Test that MathJax URL is accessible."""
        mathjax_url = markdown_widget.mathjax_url
        assert mathjax_url is not None, "MathJax URL should not be None"
        assert isinstance(mathjax_url, str), "MathJax URL should be a string"
        assert len(mathjax_url) > 0, "MathJax URL should not be empty"

    def test_content_setting(self, qtbot, markdown_widget):
        """Test that content can be set without errors."""
        test_content = "# Test Header\n\nThis is a test markdown content."

        # Should not raise an exception
        markdown_widget.setContent(test_content)

        # Content should be stored
        assert (
            markdown_widget.content() == test_content
        ), "Content should be stored correctly"

    def test_disable_scrollbars_method(self, qtbot, markdown_widget):
        """Test that the disable scrollbars method exists and can be called."""
        # Method should exist
        assert hasattr(
            markdown_widget, "_disable_scrollbars"
        ), "Should have _disable_scrollbars method"

        # Should be callable without errors
        markdown_widget._disable_scrollbars(True)

    def test_initialization_html_generation(self, qtbot, markdown_widget):
        """Test that initialization HTML can be generated."""
        # Method should exist
        assert hasattr(
            markdown_widget, "_initialize_web_engine"
        ), "Should have _initialize_web_engine method"

        # Should be callable without errors
        markdown_widget._initialize_web_engine()
