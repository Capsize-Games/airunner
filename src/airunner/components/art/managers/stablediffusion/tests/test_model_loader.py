import types


from airunner.components.art.managers.stablediffusion import model_loader


def test_load_embedding_path_missing(monkeypatch, tmp_path):
    emb = types.SimpleNamespace(path=str(tmp_path / "nope.pt"), name="e1")

    class DummyPipe:
        pass

    res = model_loader.load_embedding(path=emb.path)
    # current stub returns an object with the path attribute
    assert hasattr(res, "path")
    assert res.path == emb.path


def test_load_lora_weights_success(monkeypatch):
    class DummyPipe:
        def load_lora_weights(self, base, weight_name=None, adapter_name=None):
            return None

    lora = types.SimpleNamespace(path="/some/path/adapter.safetensors")
    res = model_loader.load_lora_weights(
        DummyPipe(),
        lora,
        "/some/path",
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, warning=lambda *a, **k: None
        ),
    )
    assert res is True


def test_unload_functions_noop(monkeypatch):
    class Pipe:
        pass

    pipe = Pipe()
    # functions should not raise
    model_loader.unload_lora(
        pipe,
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, warning=lambda *a, **k: None
        ),
    )
    model_loader.unload_embeddings(
        pipe,
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, warning=lambda *a, **k: None
        ),
    )


def test_load_compel_proc_and_unload(monkeypatch):
    class C:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setitem(
        __import__("sys").modules, "compel", types.SimpleNamespace(Compel=C)
    )
    proc = model_loader.load_compel_proc(
        {},
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, error=lambda *a, **k: None
        ),
    )
    assert proc is not None
    # unload should not raise
    model_loader.unload_compel_proc(
        proc,
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, warning=lambda *a, **k: None
        ),
    )


def test_load_deep_cache_helper_and_unload(monkeypatch):
    class Helper:
        def __init__(self, pipe=None):
            pass

        def set_params(self, **kw):
            pass

        def enable(self):
            pass

        def disable(self):
            pass

    monkeypatch.setitem(
        __import__("sys").modules,
        "DeepCache",
        types.SimpleNamespace(DeepCacheSDHelper=Helper),
    )
    helper = model_loader.load_deep_cache_helper(
        pipe=object(),
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, error=lambda *a, **k: None
        ),
    )
    assert helper is not None
    model_loader.unload_deep_cache_helper(
        helper,
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, warning=lambda *a, **k: None
        ),
    )


def test_load_controlnet_processor_returns_none_when_disabled():
    res = model_loader.load_controlnet_processor(
        False,
        controlnet_model=None,
        controlnet_processor_path="/tmp",
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None, error=lambda *a, **k: None
        ),
    )
    assert res is None
