"""Tests for ModelSelectorWidget."""

import pytest

# Qt imports
try:
    from PySide6.QtWidgets import QApplication
    import sys

    # Create QApplication if it doesn't exist
    if not QApplication.instance():
        app = QApplication(sys.argv)
except ImportError:
    pytest.skip("PySide6 not available", allow_module_level=True)

from airunner.components.settings.gui.widgets.model_selector_widget import (
    ModelSelectorWidget,
)
from airunner.enums import ModelService


class TestModelSelectorWidget:
    """Test cases for ModelSelectorWidget."""

    def test_create_widget(self):
        """Test creating model selector widget."""
        widget = ModelSelectorWidget()
        assert widget is not None
        assert widget.provider_combo is not None
        assert widget.model_combo is not None

    def test_populate_providers(self):
        """Test that providers are populated."""
        widget = ModelSelectorWidget()
        assert widget.provider_combo.count() == 3  # Local, OpenRouter, Ollama

    def test_provider_selection(self):
        """Test selecting a provider."""
        widget = ModelSelectorWidget()

        # Connect signal
        signal_received = []

        def on_provider_changed(provider):
            signal_received.append(provider)

        widget.provider_changed.connect(on_provider_changed)

        # Select OpenRouter provider (different from default)
        widget.provider_combo.setCurrentIndex(
            1
        )  # Change index to trigger signal

        # Signal should be emitted
        assert len(signal_received) > 0
        assert signal_received[-1] == ModelService.OPENROUTER.value

    def test_model_population_local(self):
        """Test that models are populated for local provider."""
        widget = ModelSelectorWidget()

        # Select local provider
        widget.set_provider(ModelService.LOCAL.value)

        # Should have models (at least "custom")
        assert widget.model_combo.count() > 0

    def test_model_selection(self):
        """Test selecting a model."""
        widget = ModelSelectorWidget()

        # Connect signal
        signal_received = []

        def on_model_changed(provider, model_id):
            signal_received.append((provider, model_id))

        widget.model_changed.connect(on_model_changed)

        # Set provider first
        widget.set_provider(ModelService.LOCAL.value)

        # Select a model (custom should always be available)
        widget.set_model("custom")

        # Signal should be emitted
        assert len(signal_received) > 0
        assert signal_received[-1][0] == ModelService.LOCAL.value
        assert signal_received[-1][1] == "custom"

    def test_get_provider(self):
        """Test getting current provider."""
        widget = ModelSelectorWidget()
        widget.set_provider(ModelService.LOCAL.value)

        assert widget.get_provider() == ModelService.LOCAL.value

    def test_get_model_id(self):
        """Test getting current model ID."""
        widget = ModelSelectorWidget()
        widget.set_provider(ModelService.LOCAL.value)
        widget.set_model("custom")

        assert widget.get_model_id() == "custom"

    def test_model_info_display_local(self):
        """Test model info display for local models."""
        widget = ModelSelectorWidget()
        widget.set_provider(ModelService.LOCAL.value)

        # Select a known model (qwen3-8b should have info)
        widget.set_model("qwen3-8b")

        # Should display VRAM info
        vram_text = widget.vram_label.text()
        assert vram_text != "-"
        assert "GB" in vram_text or vram_text == "Unknown"

    def test_model_info_display_remote(self):
        """Test model info display for remote providers."""
        widget = ModelSelectorWidget()
        widget.set_provider(ModelService.OPENROUTER.value)

        # For remote providers, should show N/A
        assert (
            "N/A" in widget.vram_label.text()
            or "remote" in widget.vram_label.text()
        )

    def test_manage_button_exists(self):
        """Test that manage button is present."""
        widget = ModelSelectorWidget()
        assert widget.manage_button is not None
        assert widget.manage_button.text() == "Manage Models..."

    def test_clear_info_on_provider_change(self):
        """Test that model info clears when provider changes."""
        widget = ModelSelectorWidget()

        # Set a local model with info
        widget.set_provider(ModelService.LOCAL.value)
        widget.set_model("qwen3-8b")

        # Change provider
        widget.set_provider(ModelService.OPENROUTER.value)

        # Info should be cleared or show remote info
        vram_text = widget.vram_label.text()
        assert "N/A" in vram_text or "remote" in vram_text

    def test_custom_model_no_info(self):
        """Test that custom model shows no specific info."""
        widget = ModelSelectorWidget()
        widget.set_provider(ModelService.LOCAL.value)
        widget.set_model("custom")

        # Custom model should show placeholder info
        assert widget.vram_label.text() == "-"
        assert widget.context_label.text() == "-"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
