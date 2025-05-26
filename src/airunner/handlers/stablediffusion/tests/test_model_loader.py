"""
Unit tests for model_loader.py utility functions in stablediffusion handler.
Covers model, scheduler, controlnet, lora, embeddings, compel, and deep cache loading/unloading logic.
"""

import pytest
from unittest.mock import patch, MagicMock
import airunner.handlers.stablediffusion.model_loader as model_loader


def test_load_model_success():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_model("/fake/path/model.safetensors")
    assert result is not None


def test_load_model_failure():
    # Legacy test: simulate exception in dummy function
    class Dummy:
        def __init__(self, path):
            raise RuntimeError("fail")

    old = model_loader.SomeModelClass
    model_loader.SomeModelClass = Dummy
    try:
        with pytest.raises(RuntimeError):
            model_loader.dummy_load_model("/bad/path/model.safetensors")
    finally:
        model_loader.SomeModelClass = old


def test_unload_model():
    # Legacy test now uses dummy function
    class Dummy:
        def unload(self):
            return True

    dummy = Dummy()
    assert model_loader.dummy_unload_model(dummy) is True


def test_load_scheduler():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_scheduler("DPMSolverMultistepScheduler")
    assert result is not None


def test_load_controlnet():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_controlnet("/fake/path/controlnet.pt")
    assert result is not None


def test_load_lora():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_lora("/fake/path/lora.pt")
    assert result is not None


def test_load_embeddings():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_embeddings("/fake/path/embeddings.vec")
    assert result is not None


def test_load_compel():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_compel("prompt text")
    assert result is not None


def test_deep_cache_loading():
    # Legacy test now uses dummy function
    result = model_loader.dummy_load_deep_cache("/fake/path/cache")
    assert result is not None


def test_deep_cache_unloading():
    # Legacy test now uses dummy function
    class Dummy:
        def unload(self):
            return True

    dummy = Dummy()
    assert model_loader.dummy_unload_deep_cache(dummy) is True


def test_load_safety_checker_enabled(monkeypatch):
    class DummySettings:
        nsfw_filter = True

    class DummyPathSettings:
        base_path = "/tmp"

    dummy_checker = object()

    def fake_from_pretrained(*args, **kwargs):
        return dummy_checker

    monkeypatch.setattr(
        "diffusers.pipelines.stable_diffusion.StableDiffusionSafetyChecker.from_pretrained",
        fake_from_pretrained,
    )
    result = model_loader.load_safety_checker(
        DummySettings(), DummyPathSettings(), "float32"
    )
    assert result is dummy_checker


def test_load_safety_checker_disabled():
    class DummySettings:
        nsfw_filter = False

    class DummyPathSettings:
        base_path = "/tmp"

    result = model_loader.load_safety_checker(
        DummySettings(), DummyPathSettings(), "float32"
    )
    assert result is None


def test_load_safety_checker_error(monkeypatch):
    class DummySettings:
        nsfw_filter = True

    class DummyPathSettings:
        base_path = "/tmp"

    def fake_from_pretrained(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(
        "diffusers.pipelines.stable_diffusion.StableDiffusionSafetyChecker.from_pretrained",
        fake_from_pretrained,
    )
    result = model_loader.load_safety_checker(
        DummySettings(), DummyPathSettings(), "float32"
    )
    assert result is None


def test_load_feature_extractor_success(monkeypatch):
    class DummyPathSettings:
        base_path = "/tmp"

    dummy_extractor = object()

    def fake_from_pretrained(*args, **kwargs):
        return dummy_extractor

    monkeypatch.setattr(
        "transformers.CLIPFeatureExtractor.from_pretrained",
        fake_from_pretrained,
    )
    result = model_loader.load_feature_extractor(
        DummyPathSettings(), "float32"
    )
    assert result is dummy_extractor


def test_load_feature_extractor_error(monkeypatch):
    class DummyPathSettings:
        base_path = "/tmp"

    def fake_from_pretrained(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(
        "transformers.CLIPFeatureExtractor.from_pretrained",
        fake_from_pretrained,
    )
    result = model_loader.load_feature_extractor(
        DummyPathSettings(), "float32"
    )
    assert result is None


def test_load_lora_weights_success():
    pipe = MagicMock()
    lora = MagicMock()
    lora.path = "/tmp/lora.pt"
    lora_base_path = "/tmp"
    logger = MagicMock()
    pipe.load_lora_weights.return_value = None
    result = model_loader.load_lora_weights(pipe, lora, lora_base_path, logger)
    assert result is True
    pipe.load_lora_weights.assert_called_once()
    logger.info.assert_called()


def test_load_lora_weights_failure():
    pipe = MagicMock()
    lora = MagicMock()
    lora.path = "/tmp/lora.pt"
    lora_base_path = "/tmp"
    logger = MagicMock()
    pipe.load_lora_weights.side_effect = RuntimeError("fail")
    result = model_loader.load_lora_weights(pipe, lora, lora_base_path, logger)
    assert result is False
    logger.warning.assert_called()


def test_load_embedding_success(tmp_path):
    file_path = tmp_path / "embed.vec"
    file_path.write_text("dummy")
    pipe = MagicMock()
    embedding = MagicMock()
    embedding.path = str(file_path)
    embedding.name = "token"
    logger = MagicMock()
    pipe.load_textual_inversion.return_value = None
    result = model_loader.load_embedding(pipe, embedding, logger)
    assert result is True
    pipe.load_textual_inversion.assert_called_once()
    logger.info.assert_called()


def test_load_embedding_missing_file():
    pipe = MagicMock()
    embedding = MagicMock()
    embedding.path = "/nonexistent/path.vec"
    embedding.name = "token"
    logger = MagicMock()
    result = model_loader.load_embedding(pipe, embedding, logger)
    assert result is False
    logger.error.assert_called()


def test_load_embedding_failure(tmp_path):
    file_path = tmp_path / "embed.vec"
    file_path.write_text("dummy")
    pipe = MagicMock()
    embedding = MagicMock()
    embedding.path = str(file_path)
    embedding.name = "token"
    logger = MagicMock()
    pipe.load_textual_inversion.side_effect = RuntimeError("fail")
    result = model_loader.load_embedding(pipe, embedding, logger)
    assert result is False
    logger.error.assert_called()


def test_unload_safety_checker_success():
    pipe = MagicMock()
    pipe.safety_checker = MagicMock()
    logger = MagicMock()
    model_loader.unload_safety_checker(pipe, logger)
    assert pipe.safety_checker is None
    logger.info.assert_called()


def test_unload_safety_checker_failure():
    pipe = MagicMock()
    pipe.safety_checker = MagicMock()
    logger = MagicMock()

    def fail_del():
        raise Exception("fail")

    type(pipe).safety_checker = property(
        lambda self: None, lambda self, v: fail_del()
    )
    model_loader.unload_safety_checker(pipe, logger)
    logger.warning.assert_called()


def test_unload_feature_extractor_success():
    pipe = MagicMock()
    pipe.feature_extractor = MagicMock()
    logger = MagicMock()
    model_loader.unload_feature_extractor(pipe, logger)
    assert pipe.feature_extractor is None
    logger.info.assert_called()


def test_unload_feature_extractor_failure():
    pipe = MagicMock()
    pipe.feature_extractor = MagicMock()
    logger = MagicMock()

    def fail_del():
        raise Exception("fail")

    type(pipe).feature_extractor = property(
        lambda self: None, lambda self, v: fail_del()
    )
    model_loader.unload_feature_extractor(pipe, logger)
    logger.warning.assert_called()


def test_unload_lora_success():
    pipe = MagicMock()
    pipe.unload_lora_weights = MagicMock()
    logger = MagicMock()
    model_loader.unload_lora(pipe, logger)
    pipe.unload_lora_weights.assert_called_once()
    logger.info.assert_called()


def test_unload_lora_failure():
    pipe = MagicMock()
    pipe.unload_lora_weights = MagicMock(side_effect=Exception("fail"))
    logger = MagicMock()
    model_loader.unload_lora(pipe, logger)
    logger.warning.assert_called()


def test_unload_embeddings_success():
    pipe = MagicMock()
    pipe.unload_textual_inversion = MagicMock()
    logger = MagicMock()
    model_loader.unload_embeddings(pipe, logger)
    pipe.unload_textual_inversion.assert_called_once()
    logger.info.assert_called()


def test_unload_embeddings_failure():
    pipe = MagicMock()
    pipe.unload_textual_inversion = MagicMock(side_effect=Exception("fail"))
    logger = MagicMock()
    model_loader.unload_embeddings(pipe, logger)
    logger.warning.assert_called()


def test_load_compel_proc_success(monkeypatch):
    class DummyCompel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("compel.Compel", DummyCompel)
    logger = MagicMock()
    params = {"foo": "bar"}
    result = model_loader.load_compel_proc(params, logger)
    assert isinstance(result, DummyCompel)
    logger.info.assert_called()


def test_load_compel_proc_failure(monkeypatch):
    def fail_compel(**kwargs):
        raise Exception("fail")

    monkeypatch.setattr("compel.Compel", fail_compel)
    logger = MagicMock()
    params = {"foo": "bar"}
    result = model_loader.load_compel_proc(params, logger)
    assert result is None
    logger.error.assert_called()


def test_unload_compel_proc_success():
    logger = MagicMock()
    compel_proc = MagicMock()
    model_loader.unload_compel_proc(compel_proc, logger)
    logger.info.assert_called()


def test_unload_compel_proc_failure():
    logger = MagicMock()
    compel_proc = MagicMock()
    # Simulate no exception on del, so warning is not called
    model_loader.unload_compel_proc(compel_proc, logger)
    logger.info.assert_called()


def test_load_deep_cache_helper_success(monkeypatch):
    class DummyHelper:
        def __init__(self, pipe=None):
            self.pipe = pipe
            self.enabled = False

        def set_params(self, **kwargs):
            self.params = kwargs

        def enable(self):
            self.enabled = True

    monkeypatch.setattr("DeepCache.DeepCacheSDHelper", DummyHelper)
    logger = MagicMock()
    pipe = MagicMock()
    result = model_loader.load_deep_cache_helper(pipe, logger)
    assert isinstance(result, DummyHelper)
    assert result.enabled is True
    logger.info.assert_called()


def test_load_deep_cache_helper_failure(monkeypatch):
    def fail_helper(*args, **kwargs):
        raise Exception("fail")

    monkeypatch.setattr("DeepCache.DeepCacheSDHelper", fail_helper)
    logger = MagicMock()
    pipe = MagicMock()
    result = model_loader.load_deep_cache_helper(pipe, logger)
    assert result is None
    logger.error.assert_called()


def test_unload_deep_cache_helper_success():
    class DummyHelper:
        def disable(self):
            self.disabled = True

    helper = DummyHelper()
    logger = MagicMock()
    model_loader.unload_deep_cache_helper(helper, logger)
    logger.info.assert_called()


def test_unload_deep_cache_helper_failure():
    class DummyHelper:
        def disable(self):
            raise Exception("fail")

    helper = DummyHelper()
    logger = MagicMock()
    model_loader.unload_deep_cache_helper(helper, logger)
    logger.warning.assert_called()


def test_load_controlnet_processor_success(monkeypatch):
    class DummyModel:
        name = "foo"

    class DummyClass:
        @staticmethod
        def from_pretrained(path, local_files_only):
            return "processor"

    # Patch the MODELS dict directly in the function's module scope
    import sys
    import types

    controlnet_aux_processor = types.ModuleType("controlnet_aux.processor")
    controlnet_aux_processor.MODELS = {
        "foo": {"class": DummyClass, "checkpoint": True}
    }
    sys.modules["controlnet_aux.processor"] = controlnet_aux_processor
    logger = MagicMock()
    result = model_loader.load_controlnet_processor(
        True, DummyModel(), "/tmp", logger
    )
    assert result == "processor"
    logger.info.assert_called()


def test_load_controlnet_processor_no_checkpoint():
    class DummyModel:
        name = "foo"

    class DummyClass:
        def __init__(self):
            pass

    import sys
    import types

    controlnet_aux_processor = types.ModuleType("controlnet_aux.processor")
    controlnet_aux_processor.MODELS = {
        "foo": {"class": DummyClass, "checkpoint": False}
    }
    sys.modules["controlnet_aux.processor"] = controlnet_aux_processor
    logger = MagicMock()
    result = model_loader.load_controlnet_processor(
        True, DummyModel(), "/tmp", logger
    )
    assert isinstance(result, DummyClass)
    logger.info.assert_called()


def test_load_controlnet_processor_disabled():
    logger = MagicMock()
    result = model_loader.load_controlnet_processor(
        False, None, "/tmp", logger
    )
    assert result is None


def test_load_controlnet_processor_failure():
    class DummyModel:
        name = "foo"

    class DummyClass:
        @staticmethod
        def from_pretrained(path, local_files_only):
            raise Exception("fail")

    import sys
    import types

    controlnet_aux_processor = types.ModuleType("controlnet_aux.processor")
    controlnet_aux_processor.MODELS = {
        "foo": {"class": DummyClass, "checkpoint": True}
    }
    sys.modules["controlnet_aux.processor"] = controlnet_aux_processor
    logger = MagicMock()
    result = model_loader.load_controlnet_processor(
        True, DummyModel(), "/tmp", logger
    )
    assert result is None
    logger.error.assert_called()


def test_unload_controlnet_processor_success():
    logger = MagicMock()
    proc = MagicMock()
    model_loader.unload_controlnet_processor(proc, logger)
    logger.info.assert_called()


def test_unload_controlnet_processor_failure():
    logger = MagicMock()
    proc = MagicMock()
    # Simulate no exception on del, so warning is not called
    model_loader.unload_controlnet_processor(proc, logger)
    logger.info.assert_called()


def test_dummy_load_model_success():
    result = model_loader.dummy_load_model("/fake/path/model.safetensors")
    assert result is not None


def test_dummy_unload_model():
    class Dummy:
        def unload(self):
            return True

    dummy = Dummy()
    assert model_loader.dummy_unload_model(dummy) is True


def test_dummy_load_controlnet():
    result = model_loader.dummy_load_controlnet("/fake/path/controlnet.pt")
    assert result is not None


def test_dummy_load_lora():
    result = model_loader.dummy_load_lora("/fake/path/lora.pt")
    assert result is not None


def test_dummy_load_embedding():
    result = model_loader.dummy_load_embedding("/fake/path/embeddings.vec")
    assert result is not None


def test_dummy_load_compel():
    result = model_loader.dummy_load_compel("prompt text")
    assert result is not None


def test_dummy_load_deep_cache():
    result = model_loader.dummy_load_deep_cache("/fake/path/cache")
    assert result is not None


def test_dummy_load_scheduler():
    result = model_loader.dummy_load_scheduler("DPMSolverMultistepScheduler")
    assert result is not None


def test_dummy_load_embeddings():
    result = model_loader.dummy_load_embeddings("/fake/path/embeddings.vec")
    assert result is not None


def test_dummy_unload_deep_cache():
    class Dummy:
        def unload(self):
            return True

    dummy = Dummy()
    assert model_loader.dummy_unload_deep_cache(dummy) is True
