from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from airunner_common.contract_enums import ModelStatus, ModelType
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

from airunner_services.llm.adapters.chat_gguf_chat_format_detection import (
    _detect_chat_format,
)
from airunner_services.llm.adapters.chat_gguf_generation_request import (
    _base_chat_kwargs,
)
from airunner_services.llm.adapters.chat_gguf_model_loading import load_model
from airunner_services.llm.managers.mixins.component_loader_mixin import (
    ComponentLoaderMixin,
)
from airunner_services.llm.adapters.sidecar_llama_server_proxy import (
    SidecarLlamaServerProxy,
)
from airunner_services.model_management.llm_model_manager import (
    LLMModelManager,
)
from airunner_services.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
    resolve_llama_cpp_runtime_settings,
)
from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient


class RecordingClient:
    def __init__(self):
        self.calls = []
        self.cancelled = []
        self.started = []
        self.stopped = 0
        self.stop_options = []
        self.binding_count = 0

    def start_backend(self, profile, **selection):
        self.started.append((profile, selection))
        self.binding_count += 1
        return f"binding-{self.binding_count}"

    def stop_backend(self, *, expected_binding=None, timeout_seconds=120.0):
        self.stopped += 1
        self.stop_options.append((expected_binding, timeout_seconds))
        return True

    def openai_request(
        self,
        request_id,
        payload,
        *,
        runtime_profile,
        endpoint_path,
        expected_binding=None,
    ):
        self.calls.append((request_id, payload, runtime_profile, endpoint_path, expected_binding))
        if payload.get("stream"):
            return iter(
                [
                    {"choices": [{"delta": {"content": "hi"}}]},
                    {"choices": [], "usage": {"completion_tokens": 1}},
                ]
            )
        return {"choices": [{"message": {"content": "hi"}}]}

    def cancel(self, request_id):
        self.cancelled.append(request_id)


def test_proxy_load_and_close_use_shared_profile_lifecycle():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, "qwen-profile")

    proxy.load()
    proxy.close()

    assert client.started == [("qwen-profile", {
        "model_path": None,
        "model_id": None,
        "n_ctx": None,
        "n_gpu_layers": None,
    })]
    assert client.stop_options == [("binding-1", 5.0)]
    assert client.stopped == 1


def test_selected_qwen_profile_resolves_runtime_identity_and_tuning(tmp_path):
    model_path = tmp_path / "Qwen3.5-9B-Q8_0.gguf"
    model_path.write_bytes(b"gguf-fixture")

    settings = resolve_llama_cpp_runtime_settings(
        runtime_profile="default",
        selected_model_id="qwen3.5-9b",
        selected_model_path=str(model_path),
        selected_n_ctx=32768,
        selected_n_gpu_layers=0,
    )

    assert settings.model_id == "qwen3.5-9b"
    assert settings.model_path == str(model_path)
    assert settings.n_ctx == 32768
    assert settings.n_gpu_layers == 0
    assert settings.n_batch == 256
    assert settings.flash_attn is True
    assert settings.cache_type_k == "q8_0"
    assert settings.cache_type_v == "q8_0"
    assert settings.repeat_last_n == 4096


def test_client_binds_selected_model_before_reporting_backend_loaded(
    monkeypatch,
    tmp_path,
):
    model_path = tmp_path / "selected.gguf"
    model_path.write_bytes(b"gguf-fixture")
    other_path = tmp_path / "previous.gguf"
    other_path.write_bytes(b"gguf-fixture")
    base = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=str(other_path),
        model_id="custom",
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=-1,
        startup_timeout_seconds=1,
    )
    resolved_selections = []

    def resolver(profile, **selection):
        resolved_selections.append((profile, selection))
        return LlamaCppRuntimeSettings(
            **{
                **base.__dict__,
                "model_path": selection["selected_model_path"],
                "model_id": selection["selected_model_id"],
                "runtime_profile": profile,
                "n_ctx": selection["selected_n_ctx"],
                "n_gpu_layers": selection["selected_n_gpu_layers"],
            }
        )

    launched = []

    class FakeLauncher:
        def __init__(self, settings):
            self.settings = settings
            self.endpoint = settings.endpoint
            self.started = False

        def start(self):
            self.started = True
            launched.append(self.settings)

        def stop(self):
            pass

    monkeypatch.setattr(
        "airunner_services.runtimes.sidecar_llm_client.SidecarLauncher",
        FakeLauncher,
    )
    client = SidecarLLMClient(settings=base, settings_resolver=resolver)

    client.start_backend(
        "profile-a",
        model_path=str(model_path),
        model_id="selected-model",
        n_ctx=32768,
        n_gpu_layers=12,
    )

    assert launched[-1].model_path == str(model_path)
    assert launched[-1].model_id == "selected-model"
    assert launched[-1].n_ctx == 32768
    assert launched[-1].n_gpu_layers == 12
    assert launched[-1].runtime_profile == "profile-a"
    assert resolved_selections[0][1]["selected_model_path"] == str(model_path)

    record, failure = client._reserve_request("request-1", "profile-a")
    assert failure is None
    client._start_for_request("request-1", record)
    assert launched[-1].model_path == str(model_path)
    assert resolved_selections[-1][1]["selected_model_id"] == "selected-model"
    client._release_request("request-1", record)
    assert client.stop_backend()


def test_client_rejects_launcher_model_mismatch_before_start(tmp_path):
    selected_path = tmp_path / "selected.gguf"
    selected_path.write_bytes(b"gguf-fixture")
    configured_path = tmp_path / "configured.gguf"
    configured_path.write_bytes(b"gguf-fixture")
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=str(configured_path),
        model_id="selected-model",
        runtime_profile="profile-a",
        n_ctx=32768,
        n_gpu_layers=12,
        startup_timeout_seconds=1,
    )

    class Launcher:
        def __init__(self):
            self.endpoint = settings.endpoint
            self.started = False

        def start(self):
            self.started = True

        def stop(self):
            pass

    launcher = Launcher()
    client = SidecarLLMClient(settings=settings, launcher=launcher)

    with pytest.raises(RuntimeError, match="does not match the selected GGUF"):
        client.start_backend(
            "profile-a",
            model_path=str(selected_path),
            model_id="selected-model",
            n_ctx=32768,
            n_gpu_layers=12,
        )

    assert launcher.started is False


def test_client_reserves_and_releases_unstarted_stream_leases():
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=None,
        model_id=None,
        runtime_profile="default",
        n_ctx=32768,
        n_gpu_layers=-1,
        startup_timeout_seconds=1,
    )

    class Launcher:
        def __init__(self):
            self.endpoint = settings.endpoint

        def start(self):
            raise AssertionError("unstarted stream must not start backend")

        def stop(self):
            pass

    client = SidecarLLMClient(settings=settings, launcher=Launcher())
    stream = client.openai_request(
        "same-request",
        {"messages": [], "stream": True},
        runtime_profile=None,
        endpoint_path="/v1/chat/completions",
    )

    assert client._active_request_count() == 1
    with pytest.raises(RuntimeError, match="already active"):
        client.openai_request(
            "same-request",
            {"messages": [], "stream": True},
            runtime_profile=None,
            endpoint_path="/v1/chat/completions",
        )

    stream.close()

    assert client._active_request_count() == 0


def test_proxy_preserves_chat_tools_sampling_and_endpoint():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, "qwen-profile")
    proxy.load()
    payload = {
        "messages": [{"role": "user", "content": "question"}],
        "tools": [{"type": "function", "function": {"name": "search"}}],
        "tool_choice": "auto",
        "stop": ["STOP"],
        "temperature": 0.3,
        "top_k": 20,
        "max_tokens": 512,
    }

    result = proxy.create_chat_completion(**payload)

    assert result["choices"][0]["message"]["content"] == "hi"
    request_id, sent, profile, endpoint, _binding = client.calls[0]
    assert request_id
    assert sent == payload
    assert profile == "qwen-profile"
    assert endpoint == "/v1/chat/completions"


def test_proxy_raw_completion_carries_harmony_prompt_and_stream_usage():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, "gpt-oss-profile")
    proxy.load()
    completion = proxy.create_completion(
        prompt="<|im_start|>assistant",
        stream=True,
        max_tokens=64,
        stop=["<|im_end|>"],
    )

    events = list(completion)

    assert events[-1]["usage"] == {"completion_tokens": 1}
    assert events[-1]["choices"] == [
        {
            "index": 0,
            "delta": {},
            "text": "",
            "finish_reason": None,
        }
    ]
    _, sent, profile, endpoint, _binding = client.calls[0]
    assert sent["prompt"] == "<|im_start|>assistant"
    assert sent["stop"] == ["<|im_end|>"]
    assert profile == "gpt-oss-profile"
    assert endpoint == "/v1/completions"


def test_chat_stream_requests_provider_usage_and_preserves_final_event():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, None)
    proxy.load()
    events = list(
        proxy.create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )
    )

    assert client.calls[0][1]["stream_options"] == {"include_usage": True}
    assert events[-1]["usage"] == {"completion_tokens": 1}


def test_proxy_cancellation_is_limited_to_its_active_stream():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, None)
    proxy.load()
    stream = proxy.create_chat_completion(stream=True, messages=[])
    next(stream)

    proxy.cancel_active_requests()

    assert client.cancelled == [client.calls[0][0]]
    stream.close()


def test_stream_ids_are_released_when_open_fails_or_iterator_never_starts():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, None)
    proxy.load()

    def fail_open(*_args, **_kwargs):
        raise RuntimeError("open failed")

    client.openai_request = fail_open
    with pytest.raises(RuntimeError, match="open failed"):
        proxy.create_chat_completion(stream=True, messages=[])
    proxy.cancel_active_requests()
    assert client.cancelled == []

    client.openai_request = lambda *_args, **_kwargs: iter([{"choices": []}])
    stream = proxy.create_chat_completion(stream=True, messages=[])
    stream.close()
    proxy.cancel_active_requests()
    assert client.cancelled == []


def test_stream_iterator_error_releases_request_ownership():
    client = RecordingClient()
    proxy = SidecarLlamaServerProxy(client, None)
    proxy.load()

    def broken_stream():
        yield {"choices": [{"delta": {"content": "started"}}]}
        raise RuntimeError("stream broke")

    client.openai_request = lambda *_args, **_kwargs: broken_stream()
    stream = proxy.create_chat_completion(stream=True, messages=[])
    next(stream)
    with pytest.raises(RuntimeError, match="stream broke"):
        next(stream)

    proxy.cancel_active_requests()
    assert client.cancelled == []


def test_chatgguf_loading_uses_injected_shared_client_without_native_import(
    tmp_path,
):
    client = RecordingClient()
    model_path = tmp_path / "qwen.gguf"
    model_path.write_bytes(b"gguf-fixture")
    adapter = SimpleNamespace(
        _llama=None,
        sidecar_client=client,
        gguf_runtime_profile="profile-a",
        model_path=str(model_path),
        runtime_model_id="qwen3.5-9b",
        n_ctx=32768,
        n_gpu_layers=-1,
        logger=SimpleNamespace(info=lambda *_args: None),
    )

    load_model(adapter)

    assert adapter._llama is not None
    assert client.started == [("profile-a", {
        "model_path": str(model_path),
        "model_id": "qwen3.5-9b",
        "n_ctx": 32768,
        "n_gpu_layers": -1,
    })]
    adapter._llama.create_chat_completion(messages=[], stream=False)
    assert client.calls[0][2:4] == ("profile-a", "/v1/chat/completions")


def test_parent_format_detection_does_not_load_llama_cpp():
    assert _detect_chat_format("/models/Qwen3.5-32B.gguf") is None
    assert _detect_chat_format("/models/gpt-oss-20b.gguf") == "gpt-oss"


@pytest.mark.parametrize("thinking", [True, False])
def test_qwen_template_thinking_option_is_request_scoped(thinking):
    adapter = SimpleNamespace(
        sidecar_client=object(),
        model_path="Qwen3.5-32B.gguf",
        enable_thinking=thinking,
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        min_p=0,
        repeat_penalty=1.15,
    )

    kwargs = _base_chat_kwargs(adapter, [{"role": "user", "content": "x"}], 99)

    assert kwargs["chat_template_kwargs"] == {"enable_thinking": thinking}
    assert kwargs["max_tokens"] == 99


def test_other_profiles_keep_default_template_behavior():
    adapter = SimpleNamespace(
        sidecar_client=object(),
        model_path="Mistral.gguf",
        enable_thinking=True,
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        min_p=0,
        repeat_penalty=1.15,
    )

    kwargs = _base_chat_kwargs(adapter, [{"role": "user", "content": "x"}], 99)

    assert "chat_template_kwargs" not in kwargs


def test_component_loader_injects_the_registered_runtime_client(monkeypatch):
    client = RecordingClient()

    class Registry:
        def resolve(self, runtime, *, provider):
            assert runtime.value == "llm"
            assert provider == "local"
            return client

    captured = {}

    def create_from_settings(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "airunner_services.llm.managers.mixins.component_loader_mixin.ChatModelFactory.create_from_settings",
        create_from_settings,
    )
    manager = SimpleNamespace(
        _chat_model=None,
        _model=None,
        _tokenizer=None,
        _current_model_path="/models/qwen.gguf",
        llm_settings=SimpleNamespace(use_local_llm=True),
        llm_request=SimpleNamespace(gguf_runtime_profile="qwen-profile"),
        api=SimpleNamespace(runtime_registry=Registry()),
        logger=SimpleNamespace(
            info=lambda *_args: None,
            error=lambda *_args: None,
        ),
        refresh_api_reference=lambda: None,
        _release_local_execution_ownership=lambda: None,
    )
    manager.refresh_api_reference = lambda: manager.api

    ComponentLoaderMixin._load_chat_model(manager)

    assert manager._chat_model is not None
    assert captured["runtime_client"] is client
    assert captured["gguf_runtime_profile"] == "qwen-profile"


def test_unload_retains_adapter_and_reports_shared_backend_busy():
    class BusyProxy:
        def close(self):
            raise RuntimeError("active requests")

    chat = SimpleNamespace(_llama=BusyProxy())
    manager = SimpleNamespace(
        _chat_model=chat,
        logger=SimpleNamespace(error=lambda *_args: None),
    )

    with pytest.raises(RuntimeError, match="Failed to close llama.cpp model"):
        ComponentLoaderMixin._unload_chat_model(manager)

    assert manager._chat_model is chat
    assert chat._llama is not None


def test_component_unload_stops_before_tokenizer_and_model_after_chat_close_failure():
    events = []

    class Manager(ComponentLoaderMixin):
        def __init__(self):
            self.logger = SimpleNamespace(error=lambda *_args, **_kwargs: None)

        def _park_unused_model_on_cpu(self):
            return False

        def _unload_workflow_manager(self):
            events.append("workflow")

        def _unload_tool_manager(self):
            events.append("tools")

        def _unload_chat_model(self):
            events.append("chat")
            raise RuntimeError("backend still leased")

        def _unload_tokenizer(self):
            events.append("tokenizer")

        def _unload_model(self):
            events.append("model")

    with pytest.raises(RuntimeError, match="backend still leased"):
        Manager()._unload_components()
    assert events == ["chat"]


def test_active_sidecar_lease_refusal_preserves_all_dependent_components():
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=None,
        model_id=None,
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1,
    )

    class Launcher:
        endpoint = settings.endpoint
        stopped = 0

        def start(self):
            pass

        def stop(self):
            self.stopped += 1

    launcher = Launcher()
    client = SidecarLLMClient(settings=settings, launcher=launcher)
    token = client._set_backend_binding(
        ("default", "current-model", None, ()), None
    )
    record, failure = client._reserve_request(
        "active-generation", "default", expected_binding=token
    )
    assert failure is None
    original_stop = client.stop_backend
    requested_timeouts = []

    def short_wait_for_test(*, expected_binding=None, timeout_seconds=120.0):
        requested_timeouts.append(timeout_seconds)
        return original_stop(
            expected_binding=expected_binding, timeout_seconds=0.01
        )

    client.stop_backend = short_wait_for_test
    proxy = SidecarLlamaServerProxy(client, "default")
    proxy._binding_token = token
    sentinels = {
        "workflow": object(),
        "tools": object(),
        "tokenizer": object(),
        "model": object(),
    }
    chat = SimpleNamespace(_llama=proxy)
    events = []
    manager = SimpleNamespace(
        _chat_model=chat,
        _workflow_manager=sentinels["workflow"],
        _tool_manager=sentinels["tools"],
        _tokenizer=sentinels["tokenizer"],
        _model=sentinels["model"],
        logger=SimpleNamespace(error=lambda *_args, **_kwargs: None),
        _park_unused_model_on_cpu=lambda: False,
        _unload_chat_model=lambda: ComponentLoaderMixin._unload_chat_model(manager),
        _unload_workflow_manager=lambda: events.append("workflow"),
        _unload_tool_manager=lambda: events.append("tools"),
        _unload_tokenizer=lambda: events.append("tokenizer"),
        _unload_model=lambda: events.append("model"),
    )

    with pytest.raises(RuntimeError, match="Failed to close llama.cpp model"):
        ComponentLoaderMixin._unload_components(manager)

    assert requested_timeouts == [5.0]
    assert events == []
    assert manager._chat_model is chat
    assert manager._workflow_manager is sentinels["workflow"]
    assert manager._tool_manager is sentinels["tools"]
    assert manager._tokenizer is sentinels["tokenizer"]
    assert manager._model is sentinels["model"]
    assert client._active_requests["active-generation"] is record
    assert not record.cancelled.is_set()
    assert launcher.stopped == 0
    client._release_request("active-generation", record)


def test_model_manager_restores_loaded_state_and_resources_on_unload_failure():
    manager = object.__new__(LLMModelManager)
    manager._model_status = {ModelType.LLM: ModelStatus.LOADED}
    manager._current_model_path = "/models/qwen.gguf"
    manager._active_gguf_runtime_profile = "qwen-profile"
    manager.llm_request = None
    manager._last_load_error = None
    manager.logger = SimpleNamespace(info=lambda *_args: None)
    manager.refresh_api_reference = lambda: None
    manager.change_model_status = lambda _model, status: manager._model_status.__setitem__(ModelType.LLM, status)
    manager._resolve_model_id_from_path = lambda _path: "qwen"
    manager._resolve_model_name = lambda _model_id: "Qwen"
    manager._unload_components = lambda: (_ for _ in ()).throw(
        RuntimeError("active request leases")
    )

    with pytest.raises(RuntimeError, match="active request leases"):
        LLMModelManager._unload_model_locked(manager)

    assert manager.model_status[ModelType.LLM] is ModelStatus.LOADED
    assert manager._current_model_path == "/models/qwen.gguf"
    assert manager._active_gguf_runtime_profile == "qwen-profile"
    assert manager._last_load_error == "active request leases"


def _managed_model_client(monkeypatch, model_a, model_b, request_log):
	base = LlamaCppRuntimeSettings(
		executable="llama-server",
		host="127.0.0.1",
		port=8011,
		model_path=None,
		model_id=None,
		runtime_profile="default",
		n_ctx=4096,
		n_gpu_layers=0,
		startup_timeout_seconds=1,
	)
	launchers = []

	class FakeLauncher:
		def __init__(self, settings):
			self.settings = settings
			self.endpoint = settings.endpoint
			self.starts = 0
			self.stops = 0
			launchers.append(self)

		def start(self):
			self.starts += 1

		def stop(self):
			self.stops += 1

	def resolver(profile, **selection):
		return LlamaCppRuntimeSettings(
			**{
				**base.__dict__,
				"model_path": selection.get("selected_model_path") or str(model_a),
				"model_id": selection.get("selected_model_id") or "model-a",
				"runtime_profile": profile or "default",
				"n_ctx": selection.get("selected_n_ctx") or base.n_ctx,
				"n_gpu_layers": (
					selection.get("selected_n_gpu_layers")
					if selection.get("selected_n_gpu_layers") is not None
					else base.n_gpu_layers
				),
			}
		)

	class Response:
		def __enter__(self):
			return self

		def __exit__(self, *_args):
			return None

		def read(self):
			return b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}'

	def opener(request, **_kwargs):
		request_log.append(request)
		return Response()

	monkeypatch.setattr(
		"airunner_services.runtimes.sidecar_llm_client.SidecarLauncher",
		FakeLauncher,
	)
	client = SidecarLLMClient(
		settings=base,
		settings_resolver=resolver,
		http_opener=opener,
	)
	return client, launchers


def test_model_binding_prevents_stale_adapter_from_using_reloaded_backend(
	monkeypatch, tmp_path
):
	model_a = tmp_path / "a.gguf"
	model_b = tmp_path / "b.gguf"
	model_a.write_bytes(b"model-a")
	model_b.write_bytes(b"model-b")
	requests = []
	client, launchers = _managed_model_client(
		monkeypatch, model_a, model_b, requests
	)
	proxy_a = SidecarLlamaServerProxy(
		client, "same-profile", model_path=str(model_a), model_id="model-a"
	)
	proxy_b = SidecarLlamaServerProxy(
		client, "same-profile", model_path=str(model_b), model_id="model-b"
	)

	proxy_a.load()
	token_a = proxy_a._binding_token
	proxy_b.load()
	token_b = proxy_b._binding_token

	assert token_a is not None and token_b is not None and token_a != token_b
	with pytest.raises(RuntimeError, match="backend changed"):
		proxy_a.create_chat_completion(messages=[])
	assert requests == []

	assert proxy_b.create_chat_completion(messages=[])['choices'][0]['message']['content'] == "ok"
	assert len(requests) == 1
	assert requests[0].data and b"messages" in requests[0].data

	stops_before_stale_close = sum(launcher.stops for launcher in launchers)
	proxy_a.close()
	assert sum(launcher.stops for launcher in launchers) == stops_before_stale_close
	proxy_b.close()


def test_backend_switch_waits_for_existing_model_lease(monkeypatch, tmp_path):
	model_a = tmp_path / "a.gguf"
	model_b = tmp_path / "b.gguf"
	model_a.write_bytes(b"model-a")
	model_b.write_bytes(b"model-b")
	client, _launchers = _managed_model_client(monkeypatch, model_a, model_b, [])
	proxy_a = SidecarLlamaServerProxy(
		client, "same-profile", model_path=str(model_a), model_id="model-a"
	)
	proxy_a.load()
	token_a = proxy_a._binding_token
	lease, failure = client._reserve_request(
		"active-a", "same-profile", expected_binding=token_a
	)
	assert failure is None and lease is not None

	with pytest.raises(RuntimeError, match="Timed out waiting"):
		client.start_backend(
			"same-profile",
			model_path=str(model_b),
			model_id="model-b",
			timeout_seconds=0.01,
		)
	assert client._bound_model_token == token_a
	client._release_request("active-a", lease)

	proxy_b = SidecarLlamaServerProxy(
		client, "same-profile", model_path=str(model_b), model_id="model-b"
	)
	proxy_b.load()
	assert proxy_b._binding_token != token_a


def test_proxy_with_selected_path_cannot_generate_before_it_owns_a_binding():
	client = RecordingClient()
	proxy = SidecarLlamaServerProxy(
		client, "same-profile", model_path="/models/not-loaded.gguf"
	)
	with pytest.raises(RuntimeError, match="must be loaded"):
		proxy.create_chat_completion(messages=[])
	assert client.calls == []


def test_same_path_replacement_requires_backend_rebind(monkeypatch, tmp_path):
	model = tmp_path / "selected.gguf"
	model.write_bytes(b"model-a")
	requests = []
	client, launchers = _managed_model_client(
		monkeypatch, model, model, requests
	)
	proxy = SidecarLlamaServerProxy(
		client, "same-profile", model_path=str(model), model_id="model-a"
	)
	proxy.load()
	old_token = proxy._binding_token

	replacement = tmp_path / "replacement.gguf"
	replacement.write_bytes(b"model-b-is-different")
	os.replace(replacement, model)
	with pytest.raises(RuntimeError, match="GGUF file changed"):
		proxy.create_chat_completion(messages=[])
	assert requests == []

	proxy.load()
	assert proxy._binding_token != old_token
	assert sum(launcher.stops for launcher in launchers) >= 1
	assert proxy.create_chat_completion(messages=[])['choices'][0]['message']['content'] == "ok"
	assert len(requests) == 1


def test_file_replaced_during_startup_is_not_published_as_a_binding(
	monkeypatch, tmp_path
):
	model = tmp_path / "selected.gguf"
	model.write_bytes(b"model-a")
	replacement = tmp_path / "replacement.gguf"
	replacement.write_bytes(b"model-b")
	settings = LlamaCppRuntimeSettings(
		executable="llama-server",
		host="127.0.0.1",
		port=8011,
		model_path=str(model),
		model_id="model-a",
		runtime_profile="same-profile",
		n_ctx=4096,
		n_gpu_layers=0,
		startup_timeout_seconds=1,
	)

	class ReplacingLauncher:
		endpoint = settings.endpoint
		stops = 0

		def start(self):
			os.replace(replacement, model)

		def stop(self):
			self.stops += 1

	launcher = ReplacingLauncher()
	client = SidecarLLMClient(settings=settings, launcher=launcher)
	with pytest.raises(RuntimeError, match="changed while the backend was loading"):
		client.start_backend(
			"same-profile",
			model_path=str(model),
			model_id="model-a",
		)
	assert launcher.stops == 1
	assert client._bound_model_token is None


def test_stale_proxy_close_does_not_wait_for_current_backend_lease():
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path=None,
        model_id=None,
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1,
    )

    class Launcher:
        endpoint = settings.endpoint
        stopped = 0

        def start(self):
            pass

        def stop(self):
            self.stopped += 1

    launcher = Launcher()
    client = SidecarLLMClient(settings=settings, launcher=launcher)
    token = client._set_backend_binding(
        ("default", "current-model", None, ()), None
    )
    proxy = SidecarLlamaServerProxy(client, "default")
    proxy._binding_token = "stale-binding"
    record, failure = client._reserve_request(
        "current-request", "default", expected_binding=token
    )
    assert failure is None

    proxy.close()

    assert client._active_requests["current-request"] is record
    assert not record.cancelled.is_set()
    assert launcher.stopped == 0
    assert client.stop_backend(
        expected_binding=token, timeout_seconds=0.01
    ) is False
    assert client._active_requests["current-request"] is record
    assert not record.cancelled.is_set()
    assert launcher.stopped == 0
    client._release_request("current-request", record)


def test_unload_reload_invalidates_old_proxy_binding(monkeypatch, tmp_path):
    model = tmp_path / "selected.gguf"
    model.write_bytes(b"model-a")
    requests = []
    client, launchers = _managed_model_client(monkeypatch, model, model, requests)
    current = SidecarLlamaServerProxy(
        client, "same-profile", model_path=str(model), model_id="model-a"
    )
    current.load()
    old_token = current._binding_token
    stale = SidecarLlamaServerProxy(
        client, "same-profile", model_path=str(model), model_id="model-a"
    )
    stale._binding_token = old_token

    assert client.stop_backend(expected_binding=old_token)
    current.load()
    assert current._binding_token != old_token

    with pytest.raises(RuntimeError, match="backend changed"):
        stale.create_chat_completion(messages=[])
    stops_before_stale_close = sum(launcher.stops for launcher in launchers)
    stale.close()
    assert sum(launcher.stops for launcher in launchers) == stops_before_stale_close
    assert requests == []


def _graph_manager_for_sidecar(monkeypatch, model_path, client, profile="same-profile"):
	"""Build a graph manager fixture using the real sidecar proxy lifecycle."""
	from airunner_services.model_management import llm_model_manager as manager_module

	class Resources:
		def prepare_model_loading(self, **_kwargs):
			return {"can_load": True}

		def model_loaded(self, *_args, **_kwargs):
			pass

		def cleanup_model(self, *_args, **_kwargs):
			pass

	monkeypatch.setattr(manager_module, "ModelResourceManager", Resources)
	monkeypatch.setattr(manager_module, "apply_cudnn_benchmark", lambda *_args: None)
	monkeypatch.setattr(manager_module, "clear_memory", lambda *_args: None)
	monkeypatch.setattr(
		LLMModelManager,
		"model_path",
		property(lambda manager: manager._fixture_model_path),
	)
	monkeypatch.setattr(
		LLMModelManager,
		"device",
		property(lambda _manager: "cpu"),
	)
	monkeypatch.setattr(
		LLMModelManager,
		"memory_settings",
		property(lambda _manager: None),
	)
	manager = object.__new__(LLMModelManager)
	manager._runtime_activity_lock = __import__("threading").RLock()
	manager._model_status = {ModelType.LLM: ModelStatus.UNLOADED}
	manager._current_model_path = None
	manager._active_gguf_runtime_profile = None
	manager._last_load_error = None
	manager._fixture_model_path = str(model_path)
	manager.llm_settings = SimpleNamespace(use_local_llm=True)
	manager.llm_request = SimpleNamespace(gguf_runtime_profile=profile)
	manager.logger = SimpleNamespace(
		info=lambda *_args, **_kwargs: None,
		error=lambda *_args, **_kwargs: None,
	)
	manager._chat_model = None
	manager._tool_manager = None
	manager._workflow_manager = None
	manager._model = None
	manager._tokenizer = None
	manager.change_model_status = lambda _kind, status: manager._model_status.__setitem__(ModelType.LLM, status)
	manager.refresh_api_reference = lambda: None
	manager._validate_model_path = lambda: True
	manager._check_and_download_model = lambda: True
	manager._resolve_model_id_from_path = lambda _path: "model-a"
	manager._resolve_model_name = lambda _model_id: "Model A"
	manager._send_quantization_info = lambda: None
	manager._load_local_llm_components = lambda: None
	manager._load_tool_manager = lambda: None
	manager._load_workflow_manager = lambda: None
	manager._update_model_status = lambda: manager.change_model_status(ModelType.LLM, ModelStatus.LOADED)

	def load_chat():
		proxy = SidecarLlamaServerProxy(
			client,
			profile,
			model_path=str(model_path),
			model_id="model-a",
			n_ctx=4096,
			n_gpu_layers=0,
		)
		proxy.load()
		manager._chat_model = SimpleNamespace(_llama=proxy)

	def unload_components():
		if manager._chat_model is not None:
			manager._chat_model._llama.close()
		manager._chat_model = None

	manager._load_chat_model = load_chat
	manager._unload_components = unload_components
	return manager


def _ready_sidecar_client(model_path, model_id="model-a", profile="same-profile"):
	settings = LlamaCppRuntimeSettings(
		executable="llama-server",
		host="127.0.0.1",
		port=8011,
		model_path=str(model_path),
		model_id=model_id,
		runtime_profile=profile,
		n_ctx=4096,
		n_gpu_layers=0,
		startup_timeout_seconds=1,
	)
	launchers = []

	class Launcher:
		def __init__(self):
			self.endpoint = settings.endpoint
			self.starts = 0
			self.stops = 0
			self.ready = True
			self.health_checks = 0
			launchers.append(self)

		def start(self):
			self.starts += 1
			self.ready = True

		def stop(self):
			self.stops += 1
			self.ready = False

		def health_status(self):
			from airunner_services.runtimes.contracts import RuntimeHealthStatus
			self.health_checks += 1
			return (
				RuntimeHealthStatus.READY if self.ready else RuntimeHealthStatus.FAILED,
				"fixture",
			)

	launcher = Launcher()
	return SidecarLLMClient(settings=settings, launcher=launcher), launcher


def _runtime_control(client, action, request_id):
	return client.invoke(
		SimpleNamespace(runtime=RuntimeKind.LLM, action=action, request_id=request_id)
	)


def test_graph_load_adopts_matching_modern_reload_and_keeps_graph_adapter(
	monkeypatch, tmp_path
):
	model = tmp_path / "model-a.gguf"
	model.write_bytes(b"same model bytes")
	client, launcher = _ready_sidecar_client(model)
	manager = _graph_manager_for_sidecar(monkeypatch, model, client)

	manager.load()
	graph_chat = manager._chat_model
	graph_proxy = graph_chat._llama
	graph_token = graph_proxy._binding_token

	assert _runtime_control(client, RuntimeAction.UNLOAD_MODEL, "modern-unload").status.value == "succeeded"
	assert _runtime_control(client, RuntimeAction.LOAD_MODEL, "modern-load").status.value == "succeeded"
	modern_token = client._bound_model_token
	assert modern_token != graph_token

	manager.load()

	assert manager._chat_model is graph_chat
	assert graph_proxy._binding_token == modern_token
	assert launcher.starts == 2
	assert launcher.stops == 1

	requests = []
	client.openai_request = lambda *args, **kwargs: requests.append(kwargs["expected_binding"]) or {"choices": [{"message": {"content": "ok"}}]}
	assert graph_proxy.create_chat_completion(messages=[])["choices"][0]["message"]["content"] == "ok"
	assert requests == [modern_token]


def test_graph_load_reconciles_child_exit_and_same_path_replacement(
	monkeypatch, tmp_path
):
	model = tmp_path / "model-a.gguf"
	model.write_bytes(b"original model")
	client, launcher = _ready_sidecar_client(model)
	manager = _graph_manager_for_sidecar(monkeypatch, model, client)
	manager.load()
	first_chat = manager._chat_model

	launcher.ready = False
	manager.load()
	second_chat = manager._chat_model
	assert second_chat is not first_chat
	assert launcher.starts == 2
	assert launcher.stops == 1
	assert manager.model_status[ModelType.LLM] is ModelStatus.LOADED

	replacement = tmp_path / "replacement.gguf"
	replacement.write_bytes(b"replacement with distinct identity")
	os.replace(replacement, model)
	second_token = second_chat._llama._binding_token
	manager.load()
	assert manager._chat_model is not second_chat
	assert manager._chat_model._llama._binding_token != second_token
	assert launcher.starts == 3
	assert launcher.stops == 2


def test_graph_reconciliation_does_not_disturb_active_sibling_lease(
	monkeypatch, tmp_path
):
	model = tmp_path / "model-a.gguf"
	model.write_bytes(b"same model bytes")
	client, launcher = _ready_sidecar_client(model)
	manager = _graph_manager_for_sidecar(monkeypatch, model, client)
	manager.load()
	token = manager._chat_model._llama._binding_token
	lease, failure = client._reserve_request(
		"sibling-request", "same-profile", expected_binding=token
	)
	assert failure is None and lease is not None

	manager.load()

	assert manager._chat_model._llama._binding_token == token
	assert client._active_requests["sibling-request"] is lease
	assert not lease.cancelled.is_set()
	assert launcher.stops == 0
	assert launcher.starts == 1
	client._release_request("sibling-request", lease)


def test_constructed_chat_model_does_not_import_native_or_serialize_client(monkeypatch):
    import builtins
    from airunner_services.llm.adapters.chat_gguf import ChatGGUF

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "llama_cpp" or name.startswith("llama_cpp."):
            pytest.fail("supervised ChatGGUF imported native llama_cpp in parent")
        return original_import(name, *args, **kwargs)

    class PrivateClient(RecordingClient):
        def __repr__(self):
            return "private-control-client-sentinel"

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    client = PrivateClient()
    model = ChatGGUF(model_path="/fixture/Qwen3.5-9B-Q8_0.gguf", sidecar_client=client)
    assert client.started
    assert "sidecar_client" not in model.model_dump()
    assert "private-control-client-sentinel" not in repr(model)
    assert "private-control-client-sentinel" not in model.model_dump_json()
