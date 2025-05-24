import os
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from airunner.handlers.llm.training_mixin import TrainingMixin


class DummyPathSettings:
    base_path = tempfile.gettempdir()


class DummyTrainer:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.train_called = False
        self.save_model_called = False

    def train(self, *args, **kwargs):
        self.train_called = True

    def save_model(self, output_dir):
        self.save_model_called = True
        self.saved_dir = output_dir


class DummyTrainingMixin(TrainingMixin):
    def __init__(self, model_version="test-version"):
        self.model_version = model_version
        self.path_settings = DummyPathSettings()
        self.model_path = (
            "/tmp/dummy_model_path"  # Add this for _save_finetuned_model
        )


@pytest.fixture
def mixin():
    return DummyTrainingMixin()


def test_finetuned_model_directory_and_adapter_path(mixin):
    assert "fine_tuned_mistral_qllm" in mixin.finetuned_model_directory
    assert mixin.model_version in mixin.finetuned_model_directory
    assert "user_memory_adapter" in mixin.adapter_path
    assert mixin.model_version in mixin.adapter_path


def test_latest_checkpoint_returns_none_if_missing(mixin):
    # Directory does not exist
    with patch("os.path.exists", return_value=False):
        assert mixin.latest_checkpoint is None
    # Directory exists but no checkpoints
    with patch("os.path.exists", return_value=True), patch(
        "os.listdir", return_value=["foo", "bar"]
    ):
        assert mixin.latest_checkpoint is None


def test_latest_checkpoint_returns_latest(mixin):
    import types

    with tempfile.TemporaryDirectory() as d:
        cp1 = os.path.join(d, "checkpoint-1")
        cp2 = os.path.join(d, "checkpoint-2")
        os.mkdir(cp1)
        os.mkdir(cp2)
        os.utime(cp1, (1, 1))
        os.utime(cp2, (2, 2))
        # Patch the property to return our temp dir
        mixin.__class__.finetuned_model_directory = property(lambda self: d)
        assert mixin.latest_checkpoint == cp2


def test_train_invokes_trainer(monkeypatch, mixin):
    # Patch Trainer and Dataset
    dummy_trainer = DummyTrainer()
    monkeypatch.setattr(
        "airunner.handlers.llm.training_mixin.Trainer",
        lambda *a, **k: dummy_trainer,
    )

    class DummyDataset:
        def map(self, *a, **k):
            return self

    monkeypatch.setattr(
        "airunner.handlers.llm.training_mixin.Dataset.from_dict",
        lambda d: DummyDataset(),
    )
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    monkeypatch.setattr("builtins.open", lambda *a, **k: MagicMock())
    monkeypatch.setattr("json.dump", lambda *a, **k: None)
    # Add a dummy logger and tokenizer to the mixin
    mixin.logger = MagicMock()
    mixin._tokenizer = MagicMock()
    mixin._tokenizer.pad_token = None
    mixin._tokenizer.eos_token = "<EOS>"
    mixin._tokenizer.__call__ = lambda *a, **k: {"input_ids": [1, 2, 3]}
    mixin._load_peft_model = lambda m: m
    mixin._model = MagicMock()
    mixin.finetuned_model_directory  # ensure property is accessed
    mixin.train(
        training_data=[("user", "bot")],
        username="U",
        botname="B",
        training_steps=1,
        save_steps=1,
        num_train_epochs=1,
    )
    assert dummy_trainer.train_called
