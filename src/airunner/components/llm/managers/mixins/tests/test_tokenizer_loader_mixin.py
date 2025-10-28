"""Tests for TokenizerLoaderMixin."""

import pytest
from unittest.mock import Mock, patch
from transformers import AutoConfig

from airunner.components.llm.managers.mixins.tokenizer_loader_mixin import (
    TokenizerLoaderMixin,
)


class TestableTokenizerMixin(TokenizerLoaderMixin):
    """Testable version of TokenizerLoaderMixin."""

    def __init__(self):
        """Initialize with mock attributes."""
        self.logger = Mock()
        self.model_path = "/fake/model/path"
        self._tokenizer = None


class TestIsMistral3Config:
    """Tests for _is_mistral3_config method."""

    def test_returns_true_for_mistral3_model_type(self):
        """Test returns True when model_type is mistral3."""
        mixin = TestableTokenizerMixin()
        config = Mock(spec=AutoConfig)
        config.model_type = "mistral3"
        config.architectures = None

        result = mixin._is_mistral3_config(config)

        assert result is True

    def test_returns_true_for_mistral3_architecture(self):
        """Test returns True when architecture contains Mistral3."""
        mixin = TestableTokenizerMixin()
        config = Mock(spec=AutoConfig)
        config.model_type = "other"
        config.architectures = ["Mistral3ForCausalLM"]

        result = mixin._is_mistral3_config(config)

        assert result is True

    def test_returns_false_for_non_mistral3(self):
        """Test returns False for non-Mistral3 models."""
        mixin = TestableTokenizerMixin()
        config = Mock(spec=AutoConfig)
        config.model_type = "llama"
        config.architectures = ["LlamaForCausalLM"]

        result = mixin._is_mistral3_config(config)

        assert result is False

    def test_handles_missing_attributes(self):
        """Test handles config without model_type or architectures."""
        mixin = TestableTokenizerMixin()
        config = Mock(spec=AutoConfig)
        del config.model_type
        del config.architectures

        result = mixin._is_mistral3_config(config)

        assert result is False


class TestHandleMistral3Tokenizer:
    """Tests for _handle_mistral3_tokenizer method."""

    @patch("os.path.exists")
    def test_returns_true_when_tekken_exists(self, mock_exists):
        """Test returns True when tekken.json exists."""
        mock_exists.return_value = True
        mixin = TestableTokenizerMixin()

        result = mixin._handle_mistral3_tokenizer()

        assert result is True
        mixin.logger.info.assert_called()

    @patch("os.path.exists")
    def test_raises_error_when_tekken_missing(self, mock_exists):
        """Test raises FileNotFoundError when tekken.json missing."""
        mock_exists.return_value = False
        mixin = TestableTokenizerMixin()

        with pytest.raises(FileNotFoundError, match="tekken.json not found"):
            mixin._handle_mistral3_tokenizer()


class TestLoadStandardTokenizer:
    """Tests for _load_standard_tokenizer method."""

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.AutoTokenizer"
    )
    def test_loads_tokenizer_without_trust_remote_code(self, mock_auto_tok):
        """Test loads tokenizer with trust_remote_code=False."""
        mock_tokenizer = Mock()
        mock_auto_tok.from_pretrained.return_value = mock_tokenizer
        mixin = TestableTokenizerMixin()

        mixin._load_standard_tokenizer()

        assert mixin._tokenizer == mock_tokenizer
        mock_auto_tok.from_pretrained.assert_called_once_with(
            mixin.model_path,
            local_files_only=True,
            trust_remote_code=False,
        )

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.AutoTokenizer"
    )
    def test_falls_back_on_key_error(self, mock_auto_tok):
        """Test falls back to trust_remote_code=True on KeyError."""
        mock_auto_tok.from_pretrained.side_effect = KeyError("test error")
        mixin = TestableTokenizerMixin()
        mixin._load_tokenizer_with_trust_remote_code = Mock()

        mixin._load_standard_tokenizer()

        mixin._load_tokenizer_with_trust_remote_code.assert_called_once()


class TestLoadTokenizerWithTrustRemoteCode:
    """Tests for _load_tokenizer_with_trust_remote_code method."""

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.AutoTokenizer"
    )
    def test_loads_with_trust_remote_code(self, mock_auto_tok):
        """Test loads tokenizer with trust_remote_code=True."""
        mock_tokenizer = Mock()
        mock_auto_tok.from_pretrained.return_value = mock_tokenizer
        mixin = TestableTokenizerMixin()

        mixin._load_tokenizer_with_trust_remote_code()

        assert mixin._tokenizer == mock_tokenizer
        mock_auto_tok.from_pretrained.assert_called_once_with(
            mixin.model_path,
            local_files_only=True,
            trust_remote_code=True,
        )

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.AutoTokenizer"
    )
    def test_falls_back_to_slow_tokenizer_on_key_error(self, mock_auto_tok):
        """Test falls back to slow tokenizer on KeyError."""
        mock_auto_tok.from_pretrained.side_effect = KeyError("mapping error")
        mixin = TestableTokenizerMixin()
        mixin._load_slow_tokenizer = Mock()

        mixin._load_tokenizer_with_trust_remote_code()

        mixin._load_slow_tokenizer.assert_called_once()


class TestLoadSlowTokenizer:
    """Tests for _load_slow_tokenizer method."""

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.AutoTokenizer"
    )
    def test_loads_slow_tokenizer(self, mock_auto_tok):
        """Test loads slow tokenizer with use_fast=False."""
        mock_tokenizer = Mock()
        mock_auto_tok.from_pretrained.return_value = mock_tokenizer
        mixin = TestableTokenizerMixin()

        mixin._load_slow_tokenizer()

        assert mixin._tokenizer == mock_tokenizer
        mock_auto_tok.from_pretrained.assert_called_once_with(
            mixin.model_path,
            local_files_only=True,
            trust_remote_code=True,
            use_fast=False,
        )


class TestLoadTokenizer:
    """Tests for _load_tokenizer method."""

    def test_returns_early_if_tokenizer_already_loaded(self):
        """Test returns immediately if tokenizer already exists."""
        mixin = TestableTokenizerMixin()
        mixin._tokenizer = Mock()
        mixin._load_model_config = Mock()

        mixin._load_tokenizer()

        mixin._load_model_config.assert_not_called()

    def test_loads_mistral3_tokenizer(self):
        """Test loads Mistral3 tokenizer when config indicates Mistral3."""
        mixin = TestableTokenizerMixin()
        mock_config = Mock()
        mixin._load_model_config = Mock(return_value=mock_config)
        mixin._is_mistral3_config = Mock(return_value=True)
        mixin._handle_mistral3_tokenizer = Mock(return_value=True)

        mixin._load_tokenizer()

        mixin._handle_mistral3_tokenizer.assert_called_once()
        mixin._is_mistral3_config.assert_called_once_with(mock_config)

    def test_loads_standard_tokenizer_for_non_mistral3(self):
        """Test loads standard tokenizer for non-Mistral3 models."""
        mixin = TestableTokenizerMixin()
        mock_config = Mock()
        mixin._load_model_config = Mock(return_value=mock_config)
        mixin._is_mistral3_config = Mock(return_value=False)
        mixin._load_standard_tokenizer = Mock()
        mixin._configure_loaded_tokenizer = Mock()

        mixin._load_tokenizer()

        mixin._load_standard_tokenizer.assert_called_once()
        mixin._configure_loaded_tokenizer.assert_called_once()

    def test_handles_loading_errors(self):
        """Test handles errors during tokenizer loading."""
        mixin = TestableTokenizerMixin()
        error = Exception("test error")
        mixin._load_model_config = Mock(side_effect=error)
        mixin._handle_tokenizer_error = Mock()

        mixin._load_tokenizer()

        mixin._handle_tokenizer_error.assert_called_once_with(error)


class TestLoadModelConfig:
    """Tests for _load_model_config method."""

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.AutoConfig"
    )
    def test_loads_config_from_pretrained(self, mock_auto_config):
        """Test loads AutoConfig from model path."""
        mock_config = Mock()
        mock_auto_config.from_pretrained.return_value = mock_config
        mixin = TestableTokenizerMixin()

        result = mixin._load_model_config()

        assert result == mock_config
        mock_auto_config.from_pretrained.assert_called_once_with(
            mixin.model_path,
            local_files_only=True,
            trust_remote_code=True,
        )


class TestConfigureLoadedTokenizer:
    """Tests for _configure_loaded_tokenizer method."""

    def test_disables_default_system_prompt_when_tokenizer_exists(self):
        """Test sets use_default_system_prompt to False."""
        mixin = TestableTokenizerMixin()
        mock_tokenizer = Mock()
        mixin._tokenizer = mock_tokenizer

        mixin._configure_loaded_tokenizer()

        assert mock_tokenizer.use_default_system_prompt is False

    def test_does_nothing_when_no_tokenizer(self):
        """Test does nothing if tokenizer is None."""
        mixin = TestableTokenizerMixin()
        mixin._tokenizer = None

        # Should not raise an error
        mixin._configure_loaded_tokenizer()


class TestHandleTokenizerError:
    """Tests for _handle_tokenizer_error method."""

    @patch(
        "airunner.components.llm.managers.mixins.tokenizer_loader_mixin.traceback"
    )
    def test_logs_error_and_sets_tokenizer_none(self, mock_traceback):
        """Test logs error details and sets tokenizer to None."""
        mock_traceback.format_exc.return_value = "traceback output"
        mixin = TestableTokenizerMixin()
        mixin._tokenizer = Mock()  # Start with a tokenizer
        error = ValueError("test error")

        mixin._handle_tokenizer_error(error)

        assert mixin._tokenizer is None
        assert mixin.logger.error.call_count == 3
        mixin.logger.error.assert_any_call(
            "Error loading tokenizer: ValueError: test error"
        )
