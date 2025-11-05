"""Tests for ValidationMixin.

Tests the validation mixin functionality including model path validation,
file existence checking, and component loading verification.
"""

from unittest.mock import Mock, patch

from airunner.components.llm.managers.mixins.validation_mixin import (
    ValidationMixin,
)
from airunner.enums import SignalCode, ModelType, ModelStatus


class TestableValidationMixin(ValidationMixin):
    """Testable version of ValidationMixin."""

    def __init__(self):
        self.llm_settings = Mock()
        self.llm_settings.use_local_llm = True
        self.model_path = "/fake/model/path"
        self.model_name = "test-model"
        self.logger = Mock()
        self.emit_signal = Mock()
        self.model_status = {ModelType.LLM: ModelStatus.UNLOADED}
        self.change_model_status = Mock()
        self._chat_model = None
        self._workflow_manager = None
        self._model = None
        self._tokenizer = None


class TestCheckModelExists:
    """Tests for _check_model_exists method."""

    def test_returns_true_for_api_mode(self):
        """Test returns True when using API-based LLM."""
        mixin = TestableValidationMixin()
        mixin.llm_settings.use_local_llm = False

        result = mixin._check_model_exists()

        assert result is True

    @patch("os.path.exists")
    def test_returns_false_when_path_missing(self, mock_exists):
        """Test returns False when model path doesn't exist."""
        mock_exists.return_value = False
        mixin = TestableValidationMixin()

        result = mixin._check_model_exists()

        assert result is False
        mixin.logger.info.assert_called()

    @patch("os.path.exists")
    @patch("os.listdir")
    def test_returns_true_when_files_present(self, mock_listdir, mock_exists):
        """Test returns True when config and safetensors exist."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["config.json", "model.safetensors"]
        mixin = TestableValidationMixin()

        result = mixin._check_model_exists()

        assert result is True


class TestVerifyModelFiles:
    """Tests for _verify_model_files method."""

    @patch("os.path.exists")
    @patch("os.listdir")
    def test_returns_true_with_all_files(self, mock_listdir, mock_exists):
        """Test returns True when all required files present."""
        mock_listdir.return_value = ["config.json", "model.safetensors"]
        mock_exists.return_value = True  # config.json exists
        mixin = TestableValidationMixin()

        result = mixin._check_model_files_exist("/fake/path")

        assert result is True

    @patch("os.listdir")
    def test_returns_false_missing_config(self, mock_listdir):
        """Test returns False when config.json missing."""
        mock_listdir.return_value = ["model.safetensors"]
        mixin = TestableValidationMixin()

        with patch("os.path.exists", return_value=False):
            result = mixin._check_model_files_exist("/fake/path")

        assert result is False

    @patch("os.listdir")
    def test_returns_false_missing_safetensors(self, mock_listdir):
        """Test returns False when no safetensors files."""
        mock_listdir.return_value = ["config.json"]
        mixin = TestableValidationMixin()

        with patch("os.path.exists", return_value=True):
            result = mixin._check_model_files_exist("/fake/path")

        assert result is False


class TestCheckEssentialFiles:
    """Tests for _check_essential_files method."""

    @patch("os.path.exists")
    def test_returns_true_all_present(self, mock_exists):
        """Test returns True when all essential files exist."""
        mock_exists.return_value = True
        mixin = TestableValidationMixin()

        result = mixin._check_essential_files("/path", ["config.json"])

        assert result is True

    @patch("os.path.exists")
    def test_returns_false_when_missing(self, mock_exists):
        """Test returns False when files missing."""
        mock_exists.return_value = False
        mixin = TestableValidationMixin()

        result = mixin._check_essential_files("/path", ["config.json"])

        assert result is False


class TestLogMissingFiles:
    """Tests for _log_missing_files method."""

    @patch("os.path.exists")
    def test_logs_missing_files(self, mock_exists):
        """Test logs which files are missing."""
        mock_exists.return_value = False
        mixin = TestableValidationMixin()

        mixin._log_missing_files("/path", ["config.json", "model.json"])

        mixin.logger.info.assert_called_once()
        log_msg = mixin.logger.info.call_args[0][0]
        assert "config.json" in log_msg


class TestTriggerModelDownload:
    """Tests for _trigger_model_download method."""

    @patch(
        "airunner.components.llm.managers.mixins.validation_mixin.LLMProviderConfig"
    )
    def test_emits_download_signal(self, mock_config):
        """Test emits download signal with correct data."""
        mock_config.LOCAL_MODELS = {
            "model1": {"name": "test-model", "repo_id": "org/model"}
        }
        mixin = TestableValidationMixin()

        result = mixin._trigger_model_download()

        assert result is False
        mixin.emit_signal.assert_called_once()
        assert (
            mixin.emit_signal.call_args[0][0]
            == SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED
        )

    @patch(
        "airunner.components.llm.managers.mixins.validation_mixin.LLMProviderConfig"
    )
    def test_returns_false_when_repo_not_found(self, mock_config):
        """Test returns False when repo_id not found."""
        mock_config.LOCAL_MODELS = {}
        mixin = TestableValidationMixin()

        result = mixin._trigger_model_download()

        assert result is False
        mixin.logger.error.assert_called()


class TestGetRepoIdForModel:
    """Tests for _get_repo_id_for_model method."""

    @patch(
        "airunner.components.llm.managers.mixins.validation_mixin.LLMProviderConfig"
    )
    def test_returns_repo_id_when_found(self, mock_config):
        """Test returns repo_id when model found."""
        mock_config.LOCAL_MODELS = {
            "model1": {"name": "test-model", "repo_id": "org/model"}
        }
        mixin = TestableValidationMixin()

        result = mixin._get_repo_id_for_model()

        assert result == "org/model"

    @patch(
        "airunner.components.llm.managers.mixins.validation_mixin.LLMProviderConfig"
    )
    def test_returns_empty_when_not_found(self, mock_config):
        """Test returns empty string when model not found."""
        mock_config.LOCAL_MODELS = {}
        mixin = TestableValidationMixin()

        result = mixin._get_repo_id_for_model()

        assert result == ""


class TestValidateModelPath:
    """Tests for _validate_model_path method."""

    @patch(
        "airunner.components.llm.managers.mixins.validation_mixin.ModelResourceManager"
    )
    def test_returns_true_when_path_set(self, mock_manager):
        """Test returns True when model path is set."""
        mixin = TestableValidationMixin()
        mock_registry = Mock()
        mock_registry.get_model.return_value = {"name": "test"}
        mock_manager.return_value.registry = mock_registry

        result = mixin._validate_model_path()

        assert result is True

    def test_returns_false_when_path_not_set(self):
        """Test returns False when model path not set."""
        mixin = TestableValidationMixin()
        mixin.model_path = None

        result = mixin._validate_model_path()

        assert result is False


class TestCheckAndDownloadModel:
    """Tests for _check_and_download_model method."""

    def test_returns_true_for_api_mode(self):
        """Test returns True for API-based models."""
        mixin = TestableValidationMixin()
        mixin.llm_settings.use_local_llm = False

        result = mixin._check_and_download_model()

        assert result is True

    @patch("os.path.exists")
    @patch("os.listdir")
    def test_returns_true_when_model_exists(self, mock_listdir, mock_exists):
        """Test returns True when model already exists."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["config.json", "model.safetensors"]
        mixin = TestableValidationMixin()

        result = mixin._check_and_download_model()

        assert result is True

    @patch("os.path.exists")
    def test_triggers_download_when_missing(self, mock_exists):
        """Test triggers download when model missing."""
        mock_exists.return_value = False
        mixin = TestableValidationMixin()

        with patch.object(mixin, "_trigger_model_download"):
            result = mixin._check_and_download_model()

        assert result is False


class TestCheckComponentsLoadedForApi:
    """Tests for _check_components_loaded_for_api method."""

    def test_returns_true_when_components_loaded(self):
        """Test returns True when chat model and workflow loaded."""
        mixin = TestableValidationMixin()
        mixin._chat_model = Mock()
        mixin._workflow_manager = Mock()

        result = mixin._check_components_loaded_for_api()

        assert result is True

    def test_returns_false_when_missing_components(self):
        """Test returns False when components missing."""
        mixin = TestableValidationMixin()

        result = mixin._check_components_loaded_for_api()

        assert result is False


class TestCheckComponentsLoadedForLocal:
    """Tests for _check_components_loaded_for_local method."""

    def test_returns_true_when_all_loaded(self):
        """Test returns True when all components loaded."""
        mixin = TestableValidationMixin()
        mixin._model = Mock()
        mixin._tokenizer = Mock()
        mixin._chat_model = Mock()
        mixin._workflow_manager = Mock()

        result = mixin._check_components_loaded_for_local()

        assert result is True

    def test_returns_false_when_model_missing(self):
        """Test returns False when model not loaded."""
        mixin = TestableValidationMixin()
        mixin._tokenizer = Mock()
        mixin._chat_model = Mock()
        mixin._workflow_manager = Mock()

        result = mixin._check_components_loaded_for_local()

        assert result is False
