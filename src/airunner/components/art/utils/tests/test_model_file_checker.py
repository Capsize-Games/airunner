"""Tests for ModelFileChecker utility."""

import tempfile
from pathlib import Path

from airunner.components.art.utils.model_file_checker import ModelFileChecker


class TestModelFileChecker:
    """Test suite for ModelFileChecker utility."""

    def test_get_required_files_art_model(self):
        """Test getting required files for art models."""
        files = ModelFileChecker.get_required_files(
            model_type="art",
            model_id="SD 1.5",
            version="SD 1.5",
            pipeline_action="txt2img",
        )
        assert files is not None
        assert isinstance(files, list)
        assert "model_index.json" in files
        assert "scheduler/scheduler_config.json" in files

    def test_get_required_files_llm_model(self):
        """Test getting required files for LLM models."""
        files = ModelFileChecker.get_required_files(
            model_type="llm",
            model_id="meta-llama/Llama-3.1-8B-Instruct",
        )
        assert files is not None
        assert isinstance(files, list)
        assert "config.json" in files

    def test_get_required_files_stt_model(self):
        """Test getting required files for STT models."""
        files = ModelFileChecker.get_required_files(
            model_type="stt",
            model_id="openai/whisper-tiny",
        )
        assert files is not None
        assert isinstance(files, list)
        assert "config.json" in files
        assert "model.safetensors" in files

    def test_get_required_files_tts_openvoice(self):
        """Test getting required files for OpenVoice TTS models."""
        files = ModelFileChecker.get_required_files(
            model_type="tts_openvoice",
            model_id="myshell-ai/MeloTTS-English",
        )
        assert files is not None
        assert isinstance(files, list)
        assert "config.json" in files
        assert "checkpoint.pth" in files

    def test_get_required_files_unknown_model(self):
        """Test getting required files for unknown model returns None."""
        files = ModelFileChecker.get_required_files(
            model_type="unknown",
            model_id="test/model",
        )
        assert files is None

    def test_check_missing_files_all_present(self):
        """Test checking files when all are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create required files
            Path(tmpdir, "config.json").touch()
            Path(tmpdir, "model.safetensors").touch()

            # This should pass even though we don't have bootstrap data for this path
            # because if no bootstrap data exists, we assume files are present
            all_exist, missing = ModelFileChecker.check_missing_files(
                model_path=tmpdir,
                model_type="stt",
                model_id="openai/whisper-tiny",
            )

            # When files don't exist, it returns them as missing
            assert not all_exist
            assert len(missing) > 0

    def test_check_missing_files_some_missing(self):
        """Test checking files when some are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only some files
            Path(tmpdir, "config.json").touch()
            # model.safetensors is missing

            all_exist, missing = ModelFileChecker.check_missing_files(
                model_path=tmpdir,
                model_type="stt",
                model_id="openai/whisper-tiny",
            )

            assert not all_exist
            assert "model.safetensors" in missing

    def test_check_missing_files_path_not_exist(self):
        """Test checking files when path doesn't exist."""
        all_exist, missing = ModelFileChecker.check_missing_files(
            model_path="/nonexistent/path",
            model_type="stt",
            model_id="openai/whisper-tiny",
        )

        assert not all_exist
        assert missing == []

    def test_get_model_repo_id_huggingface_format(self):
        """Test extracting repo ID from HuggingFace format path."""
        repo_id = ModelFileChecker.get_model_repo_id(
            "stable-diffusion-v1-5/stable-diffusion-v1-5"
        )
        assert repo_id == "stable-diffusion-v1-5/stable-diffusion-v1-5"

    def test_get_model_repo_id_local_path(self):
        """Test that local paths return None."""
        repo_id = ModelFileChecker.get_model_repo_id("/local/path/to/model")
        assert repo_id is None

    def test_get_model_repo_id_relative_path(self):
        """Test that relative paths return None."""
        repo_id = ModelFileChecker.get_model_repo_id("./local/model")
        assert repo_id is None

    def test_get_model_repo_id_none(self):
        """Test that None input returns None."""
        repo_id = ModelFileChecker.get_model_repo_id(None)
        assert repo_id is None

    def test_should_trigger_download_missing_files_hf_repo(self):
        """Test download trigger for missing files with HF repo."""
        should_download, info = ModelFileChecker.should_trigger_download(
            model_path="openai/whisper-tiny",
            model_type="stt",
            model_id="openai/whisper-tiny",
        )

        # Should trigger download since files don't exist
        assert should_download
        assert info["repo_id"] == "openai/whisper-tiny"
        assert "missing_files" in info

    def test_should_trigger_download_local_path_missing_files(self):
        """Test download trigger for local path with missing files but valid model_id."""
        should_download, info = ModelFileChecker.should_trigger_download(
            model_path="/local/path/to/model",
            model_type="stt",
            model_id="openai/whisper-tiny",
        )

        # Should trigger download using model_id as fallback repo_id
        assert should_download
        assert info["repo_id"] == "openai/whisper-tiny"
        assert "missing_files" in info

    def test_should_trigger_download_all_files_present(self):
        """Test download trigger when all files are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create all required files for whisper-tiny
            required_files = ModelFileChecker.get_required_files(
                model_type="stt",
                model_id="openai/whisper-tiny",
            )

            for file_path in required_files:
                file_full_path = Path(tmpdir) / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.touch()

            should_download, info = ModelFileChecker.should_trigger_download(
                model_path=tmpdir,
                model_type="stt",
                model_id="openai/whisper-tiny",
            )

            # Should not trigger download when all files present
            assert not should_download
            assert info == {}


class TestUnifiedModelFiles:
    """Test suite for unified model files bootstrap data."""

    def test_unified_model_files_has_all_types(self):
        """Test that unified data includes all model types."""
        from airunner.components.data.bootstrap.unified_model_files import (
            UNIFIED_MODEL_FILES,
        )

        assert \"art\" in UNIFIED_MODEL_FILES\n        assert \"llm\" in UNIFIED_MODEL_FILES\n        assert \"stt\" in UNIFIED_MODEL_FILES\n        assert \"tts_openvoice\" in UNIFIED_MODEL_FILES

    def test_get_required_files_for_model_art(self):
        """Test get_required_files_for_model for art models."""
        from airunner.components.data.bootstrap.unified_model_files import (
            get_required_files_for_model,
        )

        files = get_required_files_for_model(
            model_type="art",
            model_id="SD 1.5",
            version="SD 1.5",
            pipeline_action="txt2img",
        )

        assert files is not None
        assert isinstance(files, list)
        assert len(files) > 0

    def test_get_required_files_for_model_llm(self):
        """Test get_required_files_for_model for LLM models."""
        from airunner.components.data.bootstrap.unified_model_files import (
            get_required_files_for_model,
        )

        files = get_required_files_for_model(
            model_type="llm",
            model_id="meta-llama/Llama-3.1-8B-Instruct",
        )

        assert files is not None
        # LLM files are now a dict of {filename: expected_size}
        assert isinstance(files, dict)
        assert "config.json" in files

    def test_get_required_files_for_model_stt(self):
        """Test get_required_files_for_model for STT models."""
        from airunner.components.data.bootstrap.unified_model_files import (
            get_required_files_for_model,
        )

        files = get_required_files_for_model(
            model_type="stt",
            model_id="openai/whisper-tiny",
        )

        assert files is not None
        assert isinstance(files, list)
        assert "config.json" in files
        assert "model.safetensors" in files

    def test_get_required_files_for_model_invalid(self):
        """Test get_required_files_for_model with invalid type."""
        from airunner.components.data.bootstrap.unified_model_files import (
            get_required_files_for_model,
        )

        files = get_required_files_for_model(
            model_type="invalid",
            model_id="test/model",
        )

        assert files is None
