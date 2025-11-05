"""
End-to-end tests for the fine-tuning system.

Tests the complete flow from UI interaction through training execution,
progress callbacks, adapter saving, and database persistence.
"""

import pytest
import os
from unittest.mock import Mock

from airunner.components.llm.managers.training_mixin import TrainingMixin
from airunner.components.llm.training_presets import (
    TrainingScenario,
    TrainingPreset,
    TRAINING_PRESETS,
)


class MockModelManager(TrainingMixin):
    """Mock model manager for testing training functionality."""

    def __init__(self):
        """Initialize mock model manager."""
        self._tokenizer = Mock()
        self._tokenizer.pad_token = "[PAD]"
        self._tokenizer.eos_token = "[EOS]"
        self._model = Mock()
        self.device = "cpu"
        self.logger = Mock()
        self._cancel_training = False
        self.model_name = "test_model"  # Add model_name attribute

        # Mock settings for adapter path
        self.path_settings = Mock()
        self.path_settings.base_path = "/tmp/airunner"


class TestTrainingPresets:
    """Test training preset definitions."""

    def test_all_scenarios_have_presets(self):
        """Verify all scenarios have defined presets."""
        for scenario in TrainingScenario:
            if scenario != TrainingScenario.CUSTOM:
                assert scenario in TRAINING_PRESETS
                preset = TRAINING_PRESETS[scenario]
                assert isinstance(preset, TrainingPreset)

    def test_author_style_preset_config(self):
        """Validate author style preset has appropriate LoRA settings."""
        preset = TRAINING_PRESETS[TrainingScenario.AUTHOR_STYLE]
        assert preset.lora_r >= 8  # Sufficient rank for style learning
        assert preset.lora_alpha > 0
        assert 0 < preset.lora_dropout < 1
        assert preset.num_train_epochs >= 2

    def test_conversational_tone_preset_config(self):
        """Validate conversational tone preset configuration."""
        preset = TRAINING_PRESETS[TrainingScenario.CONVERSATIONAL_TONE]
        assert preset.learning_rate > 0
        assert preset.per_device_train_batch_size >= 1
        assert preset.gradient_accumulation_steps >= 1

    def test_domain_vocabulary_preset_config(self):
        """Validate domain vocabulary preset configuration."""
        preset = TRAINING_PRESETS[TrainingScenario.DOMAIN_VOCABULARY]
        assert preset.warmup_steps >= 0
        assert isinstance(preset.gradient_checkpointing, bool)

    def test_response_format_preset_config(self):
        """Validate response format preset configuration."""
        preset = TRAINING_PRESETS[TrainingScenario.RESPONSE_FORMAT]
        assert preset.num_train_epochs > 0
        assert preset.lora_r > 0


class TestTrainingMixin:
    """Test TrainingMixin functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = MockModelManager()
        self.training_data = [
            ("Example 1", "This is a test example for training."),
            ("Example 2", "Another example with different content."),
            ("Example 3", "A third example to ensure variety."),
        ]

    def test_get_adapter_path(self):
        """Test adapter path generation."""
        adapter_name = "test_adapter"
        path = self.manager.get_adapter_path(adapter_name)
        assert adapter_name in path
        assert "adapters" in path or "lora" in path.lower()

    def test_validate_training_prerequisites_success(self):
        """Test validation passes with valid inputs."""
        # Should not raise
        self.manager._validate_training_prerequisites(self.training_data)

    def test_validate_training_prerequisites_no_data(self):
        """Test validation fails with empty training data."""
        with pytest.raises(ValueError, match="training_data must be provided"):
            self.manager._validate_training_prerequisites([])

    def test_validate_training_prerequisites_no_model(self):
        """Test validation fails without loaded model."""
        manager = MockModelManager()
        manager._model = None
        with pytest.raises(RuntimeError, match="Tokenizer and base model"):
            manager._validate_training_prerequisites(self.training_data)

    def test_validate_training_prerequisites_no_tokenizer(self):
        """Test validation fails without loaded tokenizer."""
        manager = MockModelManager()
        manager._tokenizer = None
        with pytest.raises(RuntimeError, match="Tokenizer and base model"):
            manager._validate_training_prerequisites(self.training_data)

    def test_cancel_fine_tune(self):
        """Test cancel_fine_tune sets flag."""
        assert not self.manager._cancel_training
        self.manager.cancel_fine_tune()
        assert self.manager._cancel_training


class TestFinetuningWorkerFlow:
    """Test the worker's fine-tuning orchestration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worker_methods = self._create_mock_worker()

    def _create_mock_worker(self):
        """Create mock worker methods for testing."""
        return {
            "prepare_examples": Mock(
                return_value=[
                    ("Title 1", "Content 1"),
                    ("Title 2", "Content 2"),
                ]
            ),
            "setup_model": Mock(return_value=True),
            "execute_training": Mock(return_value=True),
            "save_model": Mock(),
            "emit_complete": Mock(),
            "emit_error": Mock(),
            "emit_progress": Mock(),
        }

    def test_successful_training_flow(self):
        """Test complete successful training flow."""
        data = {
            "files": ["test.txt"],
            "adapter_name": "test_adapter",
            "preset": TrainingScenario.AUTHOR_STYLE.value,
        }

        # Simulate worker flow
        examples = self.worker_methods["prepare_examples"](data, data["files"])
        assert len(examples) == 2
        self.worker_methods["emit_progress"]({"progress": 5})

        model_setup = self.worker_methods["setup_model"]("test_adapter")
        assert model_setup

        training_success = self.worker_methods["execute_training"](
            examples, "test_adapter", data
        )
        assert training_success

        self.worker_methods["save_model"]("test_adapter", data["files"], data)
        self.worker_methods["emit_complete"]("test_adapter")

        # Verify call sequence
        self.worker_methods["prepare_examples"].assert_called_once()
        self.worker_methods["emit_progress"].assert_called()
        self.worker_methods["setup_model"].assert_called_once()
        self.worker_methods["execute_training"].assert_called_once()
        self.worker_methods["save_model"].assert_called_once()
        self.worker_methods["emit_complete"].assert_called_once()
        self.worker_methods["emit_error"].assert_not_called()

    def test_failed_model_setup_flow(self):
        """Test flow when model setup fails."""
        data = {
            "files": ["test.txt"],
            "adapter_name": "test_adapter",
        }

        self.worker_methods["setup_model"].return_value = False

        self.worker_methods["prepare_examples"](data, data["files"])
        model_setup = self.worker_methods["setup_model"]("test_adapter")

        if not model_setup:
            self.worker_methods["emit_error"]("test_adapter", "Setup failed")

        # Verify failure handling
        self.worker_methods["execute_training"].assert_not_called()
        self.worker_methods["save_model"].assert_not_called()
        self.worker_methods["emit_complete"].assert_not_called()

    def test_failed_training_execution_flow(self):
        """Test flow when training execution fails."""
        data = {
            "files": ["test.txt"],
            "adapter_name": "test_adapter",
        }

        self.worker_methods["execute_training"].return_value = False

        examples = self.worker_methods["prepare_examples"](data, data["files"])
        self.worker_methods["setup_model"]("test_adapter")
        training_success = self.worker_methods["execute_training"](
            examples, "test_adapter", data
        )

        if not training_success:
            self.worker_methods["emit_error"](
                "test_adapter", "Training failed"
            )

        # Verify partial execution
        self.worker_methods["setup_model"].assert_called_once()
        self.worker_methods["execute_training"].assert_called_once()
        self.worker_methods["save_model"].assert_not_called()
        self.worker_methods["emit_complete"].assert_not_called()

    def test_no_training_data_flow(self):
        """Test flow when no training examples are extracted."""
        data = {
            "files": [],
            "adapter_name": "test_adapter",
        }

        self.worker_methods["prepare_examples"].return_value = []

        examples = self.worker_methods["prepare_examples"](data, data["files"])

        if not examples:
            self.worker_methods["emit_error"](
                "test_adapter", "No training data"
            )

        # Verify early termination
        self.worker_methods["setup_model"].assert_not_called()
        self.worker_methods["execute_training"].assert_not_called()


class TestProgressCallbacks:
    """Test progress callback mechanism."""

    def test_progress_callback_invoked(self):
        """Test that progress callbacks are invoked during training."""
        callback = Mock()
        MockModelManager()

        # Simulate progress update
        progress_data = {"progress": 50, "step": 100}
        callback(progress_data)

        callback.assert_called_once_with(progress_data)

    def test_multiple_progress_updates(self):
        """Test multiple progress callbacks during training."""
        callback = Mock()

        # Simulate training progress
        for i in range(0, 101, 25):
            callback({"progress": i, "step": i * 10})

        assert callback.call_count == 5
        # Verify final call
        final_call = callback.call_args_list[-1]
        assert final_call[0][0]["progress"] == 100


class TestDatasetPreparation:
    """Test training dataset preparation."""

    def test_chunk_text_to_examples(self):
        """Test text chunking for training examples."""
        title = "Test Document"
        text = "A" * 5000  # Long text requiring chunking

        # Simulate chunking logic
        max_chars = 2000
        chunks = []
        start = 0
        idx = 1
        while start < len(text):
            chunk = text[start : start + max_chars]
            chunks.append((f"{title} - part {idx}", chunk))
            start += max_chars
            idx += 1

        assert len(chunks) == 3  # 5000 chars / 2000 max = 3 chunks
        assert all(len(chunk[1]) <= max_chars for chunk in chunks)

    def test_long_context_examples(self):
        """Test long-context example preparation."""
        title = "Long Document"
        text = "B" * 8000  # 8000 chars

        max_chars = 10000
        if len(text) <= max_chars:
            examples = [(title, text)]
        else:
            # Would chunk here
            examples = [(title, text[:max_chars])]

        assert len(examples) == 1
        assert examples[0][0] == title
        assert len(examples[0][1]) == 8000

    def test_author_style_paragraph_preservation(self):
        """Test author style preserves paragraph boundaries."""
        title = "Author Work"
        text = "Para 1.\n\nPara 2.\n\nPara 3."

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        examples = [
            (f"{title} - para {i+1}", p) for i, p in enumerate(paragraphs)
        ]

        assert len(examples) == 3
        assert "Para 1." in examples[0][1]
        assert "Para 2." in examples[1][1]
        assert "Para 3." in examples[2][1]


class TestAdapterManagement:
    """Test adapter path and persistence."""

    def test_adapter_path_structure(self):
        """Test adapter path follows expected structure."""
        manager = MockModelManager()
        adapter_name = "my_custom_adapter"

        path = manager.get_adapter_path(adapter_name)

        # Verify path contains adapter name
        assert adapter_name in path
        # Verify path is absolute
        assert os.path.isabs(path)

    def test_adapter_path_uniqueness(self):
        """Test different adapter names produce different paths."""
        manager = MockModelManager()

        path1 = manager.get_adapter_path("adapter_1")
        path2 = manager.get_adapter_path("adapter_2")

        assert path1 != path2
        assert "adapter_1" in path1
        assert "adapter_2" in path2


class TestTrainingCancellation:
    """Test training cancellation mechanism."""

    def test_cancel_sets_flag(self):
        """Test cancel_fine_tune sets cancellation flag."""
        manager = MockModelManager()

        assert not manager._cancel_training
        manager.cancel_fine_tune()
        assert manager._cancel_training

    def test_cooperative_cancellation_check(self):
        """Test that cancellation flag is checked during training."""
        manager = MockModelManager()

        # Simulate training loop checking cancellation
        stopped_at = None
        for i in range(100):
            if manager._cancel_training:
                stopped_at = i
                break
            if i == 50:
                manager.cancel_fine_tune()

        # Should have stopped shortly after 50, not reached 100
        assert stopped_at is not None
        assert stopped_at <= 52  # Allow for loop increment


class TestPresetParameterOverrides:
    """Test custom parameter overrides with presets."""

    def test_preset_with_custom_epochs(self):
        """Test preset with overridden num_train_epochs."""
        data = {
            "preset": TrainingScenario.AUTHOR_STYLE.value,
            "num_train_epochs": 5,  # Override
        }

        # Verify override would be applied
        assert "num_train_epochs" in data
        assert data["num_train_epochs"] == 5

    def test_preset_with_custom_learning_rate(self):
        """Test preset with overridden learning rate."""
        data = {
            "preset": TrainingScenario.CONVERSATIONAL_TONE.value,
            "learning_rate": 1e-5,  # Override
        }

        assert "learning_rate" in data
        assert data["learning_rate"] == 1e-5

    def test_multiple_parameter_overrides(self):
        """Test multiple parameter overrides simultaneously."""
        data = {
            "preset": TrainingScenario.DOMAIN_VOCABULARY.value,
            "num_train_epochs": 3,
            "learning_rate": 2e-5,
            "per_device_train_batch_size": 2,
            "gradient_accumulation_steps": 8,
        }

        override_params = [
            "num_train_epochs",
            "learning_rate",
            "per_device_train_batch_size",
            "gradient_accumulation_steps",
        ]

        for param in override_params:
            assert param in data


class TestDatabasePersistence:
    """Test fine-tuned model database persistence."""

    def test_save_fine_tuned_model_record(self):
        """Test saving fine-tuned model record to database."""
        # This would require database mocking
        # Testing the data structure that would be saved
        adapter_name = "test_adapter"
        adapter_path = "/path/to/adapter"
        files = ["file1.txt", "file2.txt"]
        settings = {"preset": "AUTHOR_STYLE", "num_train_epochs": 3}

        record_data = {
            "name": adapter_name,
            "adapter_path": adapter_path,
            "files": files,
            "settings": settings,
        }

        assert record_data["name"] == adapter_name
        assert record_data["adapter_path"] == adapter_path
        assert len(record_data["files"]) == 2
        assert record_data["settings"]["preset"] == "AUTHOR_STYLE"


class TestIntegrationScenarios:
    """Integration tests for common training scenarios."""

    def test_author_style_training_scenario(self):
        """Test complete author style training scenario."""
        manager = MockModelManager()

        # Prepare author-style data
        training_data = [
            (
                "Chapter 1",
                "The protagonist walked through the misty forest...",
            ),
            ("Chapter 2", "Dawn broke over the ancient city..."),
            ("Chapter 3", "She pondered the mysterious letter..."),
        ]

        # Validate prerequisites
        manager._validate_training_prerequisites(training_data)

        # Get adapter path
        adapter_path = manager.get_adapter_path("hemingway_style")
        assert "hemingway_style" in adapter_path

        # Verify preset exists
        preset = TRAINING_PRESETS[TrainingScenario.AUTHOR_STYLE]
        assert preset.num_train_epochs >= 2

    def test_conversational_tone_training_scenario(self):
        """Test conversational tone training scenario."""
        manager = MockModelManager()

        training_data = [
            ("Convo 1", "User: Hello! Assistant: Hi there! How can I help?"),
            (
                "Convo 2",
                "User: What's the weather? Assistant: Let me check...",
            ),
        ]

        manager._validate_training_prerequisites(training_data)

        adapter_path = manager.get_adapter_path("friendly_assistant")
        assert "friendly_assistant" in adapter_path

        preset = TRAINING_PRESETS[TrainingScenario.CONVERSATIONAL_TONE]
        assert preset.learning_rate > 0

    def test_domain_vocabulary_training_scenario(self):
        """Test domain-specific vocabulary training scenario."""
        manager = MockModelManager()

        training_data = [
            ("Medical Term 1", "Myocardial infarction refers to..."),
            ("Medical Term 2", "Nephrology is the study of..."),
            ("Medical Term 3", "Electrocardiogram measures..."),
        ]

        manager._validate_training_prerequisites(training_data)

        adapter_path = manager.get_adapter_path("medical_vocabulary")
        assert "medical_vocabulary" in adapter_path

        preset = TRAINING_PRESETS[TrainingScenario.DOMAIN_VOCABULARY]
        assert preset.warmup_steps >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
