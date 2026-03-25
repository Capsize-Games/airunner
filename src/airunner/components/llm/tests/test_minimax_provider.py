"""Tests for MiniMax LLM provider integration.

Tests the MiniMax provider support including:
- ChatModelFactory.create_minimax_model()
- MiniMax routing in create_from_settings()
- Provider config (model list, get_models_for_provider)
- Privacy consent (is_minimax_allowed)
- LLMSettings dataclass (use_minimax, minimax_model, use_api)
- ModelService enum (MINIMAX value)

Note: Tests that would import the full airunner stack (which triggers torch)
are tested indirectly by verifying the source code structure instead of
importing the modules. The torch/tokenizers version conflict in this
environment prevents importing modules that depend on transformers/torch.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pytest

from airunner.enums import ModelService
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.llm.managers.llm_settings import LLMSettings


# ---------------------------------------------------------------------------
# ModelService enum
# ---------------------------------------------------------------------------

class TestModelServiceEnum:
    """Tests for MINIMAX value in ModelService enum."""

    def test_minimax_enum_exists(self):
        """MINIMAX should be a valid ModelService member."""
        assert hasattr(ModelService, "MINIMAX")

    def test_minimax_enum_value(self):
        """MINIMAX value should be 'minimax'."""
        assert ModelService.MINIMAX.value == "minimax"

    def test_minimax_unique(self):
        """MINIMAX should not collide with other values."""
        values = [m.value for m in ModelService]
        assert values.count("minimax") == 1

    def test_all_providers_present(self):
        """All 4 providers should be in ModelService."""
        members = [m.name for m in ModelService]
        assert "LOCAL" in members
        assert "OPENROUTER" in members
        assert "OLLAMA" in members
        assert "MINIMAX" in members


# ---------------------------------------------------------------------------
# LLMProviderConfig
# ---------------------------------------------------------------------------

class TestProviderConfig:
    """Tests for MiniMax models in LLMProviderConfig."""

    def test_minimax_models_list_exists(self):
        """MINIMAX_MODELS class attribute should exist."""
        assert hasattr(LLMProviderConfig, "MINIMAX_MODELS")

    def test_minimax_models_contains_m27(self):
        """MiniMax-M2.7 should be in the model list."""
        assert "MiniMax-M2.7" in LLMProviderConfig.MINIMAX_MODELS

    def test_minimax_models_contains_m27_highspeed(self):
        """MiniMax-M2.7-highspeed should be in the model list."""
        assert "MiniMax-M2.7-highspeed" in LLMProviderConfig.MINIMAX_MODELS

    def test_minimax_models_contains_m25(self):
        """MiniMax-M2.5 should be in the model list."""
        assert "MiniMax-M2.5" in LLMProviderConfig.MINIMAX_MODELS

    def test_minimax_models_contains_m25_highspeed(self):
        """MiniMax-M2.5-highspeed should be in the model list."""
        assert "MiniMax-M2.5-highspeed" in LLMProviderConfig.MINIMAX_MODELS

    def test_minimax_models_contains_custom(self):
        """Custom option should be in the model list."""
        assert "custom" in LLMProviderConfig.MINIMAX_MODELS

    def test_get_models_for_provider_minimax(self):
        """get_models_for_provider('minimax') should return MINIMAX_MODELS."""
        result = LLMProviderConfig.get_models_for_provider("minimax")
        assert result == LLMProviderConfig.MINIMAX_MODELS

    def test_get_models_for_provider_minimax_nonempty(self):
        """MiniMax models list should not be empty."""
        result = LLMProviderConfig.get_models_for_provider("minimax")
        assert len(result) >= 4  # At least 4 models + custom

    def test_existing_providers_unchanged(self):
        """Existing providers should still work."""
        local = LLMProviderConfig.get_models_for_provider("local")
        openrouter = LLMProviderConfig.get_models_for_provider("openrouter")
        ollama = LLMProviderConfig.get_models_for_provider("ollama")
        assert len(local) > 0
        assert len(openrouter) > 0
        assert len(ollama) > 0


# ---------------------------------------------------------------------------
# LLMSettings dataclass
# ---------------------------------------------------------------------------

class TestLLMSettings:
    """Tests for MiniMax fields in LLMSettings dataclass."""

    def test_use_minimax_default_false(self):
        """use_minimax should default to False."""
        settings = LLMSettings()
        assert settings.use_minimax is False

    def test_minimax_model_default(self):
        """minimax_model should default to 'MiniMax-M2.7'."""
        settings = LLMSettings()
        assert settings.minimax_model == "MiniMax-M2.7"

    def test_use_api_includes_minimax(self):
        """use_api should return True when use_minimax is True."""
        settings = LLMSettings()
        settings.use_minimax = True
        assert settings.use_api is True

    def test_use_api_false_when_all_disabled(self):
        """use_api should return False when all API providers are disabled."""
        settings = LLMSettings()
        settings.use_openrouter = False
        settings.use_openai = False
        settings.use_ollama = False
        settings.use_minimax = False
        assert settings.use_api is False

    def test_use_minimax_can_be_set(self):
        """use_minimax should be settable to True."""
        settings = LLMSettings()
        settings.use_minimax = True
        assert settings.use_minimax is True

    def test_use_local_llm_default_true(self):
        """use_local_llm should default to True (unchanged by MiniMax addition)."""
        settings = LLMSettings()
        assert settings.use_local_llm is True

    def test_use_api_with_only_openrouter(self):
        """use_api should still work with openrouter alone (regression)."""
        settings = LLMSettings()
        settings.use_openrouter = True
        assert settings.use_api is True

    def test_minimax_model_settable(self):
        """minimax_model should be settable."""
        settings = LLMSettings()
        settings.minimax_model = "MiniMax-M2.5-highspeed"
        assert settings.minimax_model == "MiniMax-M2.5-highspeed"


# ---------------------------------------------------------------------------
# Source code verification tests (avoid import chain that triggers torch)
# ---------------------------------------------------------------------------

class TestSourceCodeVerification:
    """Verify MiniMax integration in source code without importing heavy modules.

    These tests read the source files directly to verify that the MiniMax
    provider integration code is correctly placed, without triggering the
    torch/transformers import chain.
    """

    @staticmethod
    def _src_airunner_root() -> str:
        """Get the src/airunner directory."""
        # tests -> llm -> components -> airunner (src/airunner)
        d = os.path.dirname(os.path.abspath(__file__))
        for _ in range(4):
            d = os.path.dirname(d)
        return d

    @staticmethod
    def _repo_root() -> str:
        """Get the repository root directory (contains README.md)."""
        # tests -> llm -> components -> airunner -> src -> repo_root
        d = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            d = os.path.dirname(d)
        return d

    def _read_source(self, relative_path: str) -> str:
        """Read source file from the airunner package."""
        full_path = os.path.join(self._src_airunner_root(), relative_path)
        with open(full_path, "r") as f:
            return f.read()

    # --- ChatModelFactory ---

    def test_factory_has_create_minimax_model(self):
        """ChatModelFactory should have create_minimax_model method."""
        src = self._read_source(
            "airunner/components/llm/adapters/chat_model_factory.py"
        )
        assert "def create_minimax_model(" in src

    def test_factory_minimax_uses_correct_base_url(self):
        """MiniMax factory method should use api.minimax.io/v1."""
        src = self._read_source(
            "airunner/components/llm/adapters/chat_model_factory.py"
        )
        assert "https://api.minimax.io/v1" in src

    def test_factory_minimax_checks_privacy(self):
        """MiniMax factory should check is_minimax_allowed."""
        src = self._read_source(
            "airunner/components/llm/adapters/chat_model_factory.py"
        )
        assert "is_minimax_allowed" in src

    def test_factory_minimax_routing_in_create_from_settings(self):
        """create_from_settings should route to MiniMax."""
        src = self._read_source(
            "airunner/components/llm/adapters/chat_model_factory.py"
        )
        assert "use_minimax" in src
        assert "MINIMAX_API_KEY" in src
        assert "create_minimax_model" in src

    def test_factory_minimax_temperature_clamping(self):
        """MiniMax factory should clamp temperature."""
        src = self._read_source(
            "airunner/components/llm/adapters/chat_model_factory.py"
        )
        # Check temperature clamping code
        assert "max(0.0, min(1.0, temperature))" in src

    def test_factory_docstring_includes_minimax(self):
        """Factory class docstring should mention MiniMax."""
        src = self._read_source(
            "airunner/components/llm/adapters/chat_model_factory.py"
        )
        assert "MiniMax" in src

    # --- Privacy consent dialog ---

    def test_privacy_dialog_has_minimax_key(self):
        """Privacy dialog should define SERVICE_MINIMAX_KEY."""
        src = self._read_source(
            "airunner/components/application/gui/dialogs/privacy_consent_dialog.py"
        )
        assert 'SERVICE_MINIMAX_KEY = "privacy/allow_minimax"' in src

    def test_privacy_dialog_has_is_minimax_allowed(self):
        """Privacy dialog should define is_minimax_allowed function."""
        src = self._read_source(
            "airunner/components/application/gui/dialogs/privacy_consent_dialog.py"
        )
        assert "def is_minimax_allowed()" in src

    def test_privacy_dialog_has_minimax_checkbox(self):
        """Privacy dialog should have MiniMax checkbox."""
        src = self._read_source(
            "airunner/components/application/gui/dialogs/privacy_consent_dialog.py"
        )
        assert 'QCheckBox("MiniMax")' in src

    def test_privacy_dialog_minimax_description(self):
        """Privacy dialog should describe MiniMax data handling."""
        src = self._read_source(
            "airunner/components/application/gui/dialogs/privacy_consent_dialog.py"
        )
        assert "MiniMax servers" in src

    # --- Chat prompt widget ---

    def test_prompt_widget_has_minimax_provider(self):
        """Chat prompt widget should list MiniMax in provider dropdown."""
        src = self._read_source(
            "airunner/components/chat/gui/widgets/chat_prompt_widget.py"
        )
        assert '"MiniMax"' in src
        assert "ModelService.MINIMAX.value" in src

    def test_prompt_widget_populates_minimax_models(self):
        """Chat prompt widget should populate MiniMax models."""
        src = self._read_source(
            "airunner/components/chat/gui/widgets/chat_prompt_widget.py"
        )
        assert "ModelService.MINIMAX.value:" in src or 'provider == ModelService.MINIMAX.value' in src

    # --- LLM generate worker ---

    def test_worker_has_use_minimax_property(self):
        """LLM generate worker should have use_minimax property."""
        src = self._read_source(
            "airunner/components/llm/workers/llm_generate_worker.py"
        )
        assert "def use_minimax(self)" in src
        assert "ModelService.MINIMAX.value" in src

    def test_worker_routes_minimax_in_model_manager(self):
        """Worker should configure model manager for MiniMax."""
        src = self._read_source(
            "airunner/components/llm/workers/llm_generate_worker.py"
        )
        assert "self.use_minimax" in src
        assert "use_minimax = True" in src

    # --- Batch processing mixin ---

    def test_batch_processing_includes_minimax(self):
        """Batch processing should recognize MiniMax as API provider."""
        src = self._read_source(
            "airunner/components/llm/managers/mixins/batch_processing_mixin.py"
        )
        assert "use_minimax" in src

    # --- README ---

    def test_readme_mentions_minimax(self):
        """README should mention MiniMax in LLM Providers list."""
        readme_path = os.path.join(self._repo_root(), "README.md")
        with open(readme_path, "r") as f:
            content = f.read()
        assert "MiniMax" in content


# ---------------------------------------------------------------------------
# Integration tests (mocked, no torch dependency)
# ---------------------------------------------------------------------------

class TestMiniMaxIntegration:
    """Integration-style tests that verify the full MiniMax flow without
    triggering heavy imports."""

    def test_settings_enable_minimax_flow(self):
        """Full flow: create settings, enable MiniMax, verify use_api."""
        settings = LLMSettings()
        # Initially local
        assert settings.use_local_llm is True
        assert settings.use_minimax is False
        assert settings.use_api is False

        # Switch to MiniMax
        settings.use_local_llm = False
        settings.use_minimax = True
        settings.minimax_model = "MiniMax-M2.7"

        assert settings.use_api is True
        assert settings.minimax_model == "MiniMax-M2.7"

    def test_provider_config_minimax_models_are_valid(self):
        """All MiniMax model IDs should match expected format."""
        for model in LLMProviderConfig.MINIMAX_MODELS:
            if model == "custom":
                continue
            assert model.startswith("MiniMax-M"), f"Unexpected model format: {model}"

    def test_minimax_model_service_round_trip(self):
        """ModelService.MINIMAX should survive string round-trip."""
        service = ModelService.MINIMAX
        value = service.value  # "minimax"
        restored = ModelService(value)
        assert restored == ModelService.MINIMAX
