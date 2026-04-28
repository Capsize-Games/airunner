from types import SimpleNamespace
from unittest.mock import Mock, patch

from airunner.components.llm.adapters.chat_model_factory import ChatModelFactory
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.llm.managers.download_huggingface import (
    DownloadHuggingFaceModel,
)


class FakeDownloadWorker:
    def __init__(self):
        self.running = False
        self.queue_items = []

    def add_to_queue(self, item):
        self.queue_items.append(item)

    def cancel(self):
        self.running = False


class TestPreferredDownloadResolution:
    def test_resolve_download_target_prefers_gguf_for_qwen(self):
        download_info = LLMProviderConfig.resolve_download_target(
            "local",
            model_id="qwen3-8b",
        )

        assert download_info is not None
        assert download_info["repo_id"] == "Qwen/Qwen3-8B-GGUF"
        assert download_info["model_type"] == "gguf"
        assert download_info["gguf_filename"] == "Qwen3-8B-Q4_K_M.gguf"
        assert download_info["quantization_bits"] == 0

    def test_resolve_download_target_prefers_qwen35_shipped_gguf(self):
        download_info = LLMProviderConfig.resolve_download_target(
            "local",
            model_id="qwen3.5-9b",
        )

        assert download_info is not None
        assert download_info["repo_id"] == "unsloth/Qwen3.5-9B-GGUF"
        assert download_info["model_type"] == "gguf"
        assert download_info["gguf_filename"] == "Qwen3.5-9B-Q8_0.gguf"

    def test_resolve_download_target_prefers_gpt_oss_shipped_gguf(self):
        download_info = LLMProviderConfig.resolve_download_target(
            "local",
            model_id="gpt-oss-20b",
        )

        assert download_info is not None
        assert download_info["repo_id"] == "unsloth/gpt-oss-20b-GGUF"
        assert download_info["model_type"] == "gguf"
        assert download_info["gguf_filename"] == "gpt-oss-20b-F16.gguf"

    def test_resolve_download_target_keeps_transformers_when_gguf_missing(self):
        download_info = LLMProviderConfig.resolve_download_target(
            "local",
            model_id="ministral3-8b",
        )

        assert download_info is not None
        assert (
            download_info["repo_id"]
            == "mistralai/Ministral-3-8B-Instruct-2512-BF16"
        )
        assert download_info["model_type"] == "ministral3"
        assert download_info["gguf_filename"] is None

    def test_get_local_storage_path_groups_gguf_models_by_owner(self):
        storage_path = LLMProviderConfig.get_local_storage_path(
            "/models",
            "local",
            model_id="qwen3-8b",
        )

        assert storage_path == "/models/text/models/llm/causallm/Qwen"

    def test_get_local_storage_path_uses_shipped_qwen_folder_for_qwen35(self):
        storage_path = LLMProviderConfig.get_local_storage_path(
            "/models",
            "local",
            model_id="qwen3.5-9b",
        )

        assert storage_path == "/models/text/models/llm/causallm/Qwen"

    def test_get_local_storage_path_uses_gpt_oss_storage_override(self):
        storage_path = LLMProviderConfig.get_local_storage_path(
            "/models",
            "local",
            model_id="gpt-oss-20b",
        )

        assert storage_path == "/models/text/models/llm/causallm/gpt_oss"

    def test_get_expected_local_artifact_path_returns_exact_gguf_file(self):
        artifact_path = LLMProviderConfig.get_expected_local_artifact_path(
            "/models",
            "local",
            model_id="qwen3-8b",
        )

        assert artifact_path == (
            "/models/text/models/llm/causallm/Qwen/Qwen3-8B-Q4_K_M.gguf"
        )

    def test_get_expected_local_artifact_path_returns_qwen35_file(self):
        artifact_path = LLMProviderConfig.get_expected_local_artifact_path(
            "/models",
            "local",
            model_id="qwen3.5-9b",
        )

        assert artifact_path == (
            "/models/text/models/llm/causallm/Qwen/Qwen3.5-9B-Q8_0.gguf"
        )

    def test_get_expected_local_artifact_path_returns_gpt_oss_file(self):
        artifact_path = LLMProviderConfig.get_expected_local_artifact_path(
            "/models",
            "local",
            model_id="gpt-oss-20b",
        )

        assert artifact_path == (
            "/models/text/models/llm/causallm/gpt_oss/gpt-oss-20b-F16.gguf"
        )

    def test_resolve_model_id_accepts_shipped_aliases(self):
        assert (
            LLMProviderConfig.resolve_model_id("local", "Qwen 3.5 9B")
            == "qwen3.5-9b"
        )
        assert (
            LLMProviderConfig.resolve_model_id("local", "GPT-OSS")
            == "gpt-oss-20b"
        )
        assert (
            LLMProviderConfig.resolve_model_id(
                "local",
                "gpt-oss-20b-F16.gguf",
            )
            == "gpt-oss-20b"
        )


class TestPreferredDownloadManager:
    def test_download_prefers_prequantized_gguf_for_supported_llm(self):
        fake_worker = FakeDownloadWorker()
        manager = DownloadHuggingFaceModel.__new__(DownloadHuggingFaceModel)
        manager.download_worker = None
        manager.logger = Mock()

        with patch(
            "airunner.components.llm.managers.download_huggingface.create_worker",
            return_value=fake_worker,
        ):
            manager.download(
                repo_id="Qwen/Qwen3-8B",
                model_type="llm",
                quantization_bits=4,
            )

        assert len(fake_worker.queue_items) == 1
        queued = fake_worker.queue_items[0]
        assert queued["repo_id"] == "Qwen/Qwen3-8B-GGUF"
        assert queued["model_type"] == "gguf"
        assert queued["gguf_filename"] == "Qwen3-8B-Q4_K_M.gguf"

    def test_download_keeps_base_repo_when_no_gguf_variant_exists(self):
        fake_worker = FakeDownloadWorker()
        manager = DownloadHuggingFaceModel.__new__(DownloadHuggingFaceModel)
        manager.download_worker = None
        manager.logger = Mock()

        with patch(
            "airunner.components.llm.managers.download_huggingface.create_worker",
            return_value=fake_worker,
        ):
            manager.download(
                repo_id="mistralai/Ministral-3-8B-Instruct-2512-BF16",
                model_type="ministral3",
                quantization_bits=4,
            )

        assert len(fake_worker.queue_items) == 1
        queued = fake_worker.queue_items[0]
        assert queued["repo_id"] == "mistralai/Ministral-3-8B-Instruct-2512-BF16"
        assert queued["model_type"] == "ministral3"
        assert queued["gguf_filename"] is None


class TestSharedGGUFSelection:
    def test_create_from_settings_uses_expected_gguf_file_in_shared_directory(
        self, tmp_path
    ):
        shared_dir = tmp_path / "Qwen"
        shared_dir.mkdir()
        preferred_gguf = shared_dir / "Qwen3-8B-Q4_K_M.gguf"
        other_gguf = shared_dir / "Qwen2.5-7B-Q4_K_M.gguf"
        preferred_gguf.write_text("preferred")
        other_gguf.write_text("other")

        with patch(
            "airunner.utils.settings.get_qsettings.get_qsettings"
        ) as mock_qsettings, patch(
            "airunner.components.llm.data.llm_generator_settings.LLMGeneratorSettings"
        ) as mock_db_settings, patch(
            "airunner.components.llm.adapters.chat_model_factory.get_model_optimizer"
        ) as mock_optimizer, patch.object(
            ChatModelFactory,
            "create_gguf_model",
            return_value="gguf-model",
        ) as mock_create_gguf:
            mock_qsettings.return_value.value.return_value = None
            mock_db_settings.objects.first.return_value = SimpleNamespace(
                model_id="qwen3-8b",
                quantization_bits=0,
                enable_thinking=True,
            )
            mock_optimizer.return_value.find_existing_gguf.return_value = str(other_gguf)

            result = ChatModelFactory.create_from_settings(
                llm_settings=SimpleNamespace(use_local_llm=True),
                model_path=str(shared_dir),
            )

        assert result == "gguf-model"
        assert (
            mock_create_gguf.call_args.kwargs["model_path"]
            == str(preferred_gguf)
        )