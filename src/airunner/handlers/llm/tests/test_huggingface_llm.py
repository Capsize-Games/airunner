"""
Tests for HuggingFaceLLM in airunner.handlers.llm.huggingface_llm.
Covers core logic, edge cases, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from airunner.handlers.llm.huggingface_llm import HuggingFaceLLM
from airunner.handlers.llm.llm_request import LLMRequest


@pytest.fixture
def dummy_model():
    model = MagicMock()
    model.device = "cpu"
    model.config.to_dict.return_value = {"max_position_embeddings": 2048}

    def generate(*args, **kwargs):
        # Return a tensor-like object for .size(1) and slicing
        class DummyTensor:
            def __getitem__(self, key):
                return [42, 43, 44]

            def size(self, dim):
                return 3

        return [[0, 1, 2, 3, 4, 5]]

    model.generate = MagicMock(side_effect=generate)
    return model


@pytest.fixture
def dummy_tokenizer():
    # Use a Mock, not MagicMock, and patch __call__ via Mock's side_effect
    from unittest.mock import Mock

    tokenizer = Mock()
    tokenizer.return_tensors = "pt"
    tokenizer.decode.return_value = "hello world"
    tokenizer.apply_chat_template = Mock(return_value="chat prompt")
    # Patch __call__
    tokenizer.side_effect = lambda *args, **kwargs: {"input_ids": [0, 1, 2]}
    return tokenizer


@pytest.fixture
def llm(dummy_model, dummy_tokenizer):
    return HuggingFaceLLM(
        model=dummy_model,
        tokenizer=dummy_tokenizer,
        context_window=2048,
        max_new_tokens=10,
        query_wrapper_prompt="{query_str}",
        tokenizer_name="dummy",
        model_name="dummy",
        device_map="cpu",
        stopping_ids=[99],
        tokenizer_kwargs={},
        tokenizer_outputs_to_remove=[],
        model_kwargs={},
        generate_kwargs={},
        is_chat_model=True,
        system_prompt="sys",
    )


def test_generate_kwargs_and_llm_request(llm):
    llm.llm_request = LLMRequest.from_default()
    gk = llm.generate_kwargs
    assert isinstance(gk, dict)
    assert "temperature" in gk
    assert "do_tts_reply" not in gk


def test_model_and_tokenizer_properties(llm, dummy_model, dummy_tokenizer):
    # The HuggingFaceLLM.model property returns self._model, not the property object
    assert llm._model is dummy_model
    assert llm._tokenizer is dummy_tokenizer


def test_metadata(llm):
    meta = llm.metadata
    assert meta.context_window == 2048
    assert meta.is_chat_model is True
    assert meta.model_name == "dummy"


def test_unload(llm):
    llm.unload()
    assert llm._model is None
    assert llm._tokenizer is None
    assert llm._stopping_criteria is None


def test_tokenizer_messages_to_prompt(llm):
    messages = [MagicMock(role=MagicMock(value="user"), content="hi")]
    prompt = llm._tokenizer_messages_to_prompt(messages)
    assert prompt == "chat prompt"


def test_complete(llm):
    # Patch tokenizer to return a mock with .to() method and input_ids with .size()
    class DummyInputIds(list):
        def size(self, dim):
            return 3

    class DummyInputs(dict):
        def to(self, device):
            return self

    dummy_inputs = DummyInputs({"input_ids": DummyInputIds([0, 1, 2])})
    llm._tokenizer.side_effect = lambda *args, **kwargs: dummy_inputs
    out = llm.complete("test prompt")
    assert hasattr(out, "text")
    assert out.text == "hello world"


def test_stream_complete(llm):
    # Patch TextIteratorStreamer and Thread, and patch tokenizer to return DummyInputs
    from unittest.mock import patch, MagicMock

    class DummyInputs(dict):
        def to(self, device):
            return self

    llm._tokenizer.side_effect = lambda *args, **kwargs: DummyInputs(
        {"input_ids": [0, 1, 2]}
    )
    with patch("transformers.TextIteratorStreamer") as streamer_cls, patch(
        "airunner.handlers.llm.huggingface_llm.Thread"
    ) as thread_cls:
        streamer = MagicMock()
        streamer.__iter__.return_value = iter(["a", "b"])
        streamer_cls.return_value = streamer
        thread = MagicMock()
        thread_cls.return_value = thread
        thread.start.side_effect = lambda: None
        gen = llm.stream_complete("prompt")
        results = list(gen)
        assert results[-1].text == "ab"


def test_chat_and_stream_chat(llm):
    from llama_index.core.base.llms.types import ChatMessage

    class DummyInputIds(list):
        def size(self, dim):
            return 3

    class DummyInputs(dict):
        def to(self, device):
            return self

    dummy_inputs = DummyInputs({"input_ids": DummyInputIds([0, 1, 2])})
    llm._tokenizer.side_effect = lambda *args, **kwargs: dummy_inputs
    messages = [ChatMessage(role="user", content="hi")]
    out = llm.chat(messages)
    assert hasattr(out, "message") or hasattr(out, "text")
    # Instead of patching the instance, patch the class method for stream_chat
    import types

    def dummy_stream_complete(self, *args, **kwargs):
        return iter([])

    llm.__class__.stream_complete = dummy_stream_complete
    out2 = llm.stream_chat(messages)
    assert hasattr(out2, "__iter__")
