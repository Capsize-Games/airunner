"""Unit tests for the SidecarLLMClient constructor split.

The two extracted init helpers were factored out to keep __init__ within
the long-function threshold. These tests assert every attribute the old
monolithic __init__ set is still set with the same values.
"""

import threading

from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient


def test_init_sets_tracking_state_and_descriptor():
    client = SidecarLLMClient()
    assert client._active_requests == {}
    assert isinstance(client._active_requests_lock, type(threading.RLock()))
    assert isinstance(client._active_requests_condition, threading.Condition)
    assert isinstance(client._launcher_lock, type(threading.RLock()))
    assert client._control_action_active is False
    assert client._bound_model_selection is None
    assert client._bound_backend_identity is None
    assert client._bound_model_file_identity is None
    assert client._bound_model_token is None
    assert client.descriptor is not None
    assert client.descriptor.endpoint == client._settings.endpoint
    assert client.descriptor.supports_streaming is True


def test_init_request_tracking_helper_is_idempotent_per_instance():
    a = SidecarLLMClient()
    b = SidecarLLMClient()
    assert a._active_requests is not b._active_requests
    assert a._active_requests_lock is not b._active_requests_lock
