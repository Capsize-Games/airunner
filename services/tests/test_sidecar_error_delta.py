"""Unit tests for SidecarLLMClient._error_delta_for.

The helper is shared by the inner and outer stream error handlers. These
tests pin its cancel-awareness and error-code mapping.
"""

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.runtimes.sidecar_llm_client import (
    NativeBackendUnavailable,
    SidecarLLMClient,
)


def _make_client(record):
    client = SidecarLLMClient.__new__(SidecarLLMClient)
    client._complete_request = MagicMock(return_value=True)
    client._cancelled_delta = MagicMock(return_value="cancelled")
    client._failure_delta = MagicMock(return_value="failure")
    client._client_error_message = MagicMock(return_value="boom")
    return client, record


def _record(cancelled=False):
    record = SimpleNamespace(cancelled=threading.Event())
    if cancelled:
        record.cancelled.set()
    return record


def test_cancelled_record_yields_cancelled_delta():
    record = _record(cancelled=True)
    client, _ = _make_client(record)
    assert client._error_delta_for("r1", record, RuntimeError("x")) == "cancelled"
    client._complete_request.assert_called_once_with("r1", record)
    client._failure_delta.assert_not_called()


def test_plain_error_yields_failure_with_default_code():
    record = _record()
    client, _ = _make_client(record)
    assert client._error_delta_for("r1", record, RuntimeError("x")) == "failure"
    client._failure_delta.assert_called_once_with("r1", "boom", code="llm_invoke_failed")


def test_native_backend_error_uses_its_code_when_with_code():
    record = _record()
    client, _ = _make_client(record)
    exc = NativeBackendUnavailable("backend down")
    exc.code = "native_unavailable"
    client._error_delta_for("r1", record, exc, with_code=True)
    assert client._failure_delta.call_args[1]["code"] == "native_unavailable"


def test_other_error_uses_code_attr_when_with_code():
    record = _record()
    client, _ = _make_client(record)
    exc = RuntimeError("x")
    exc.code = "custom_code"
    client._error_delta_for("r1", record, exc, with_code=True)
    assert client._failure_delta.call_args[1]["code"] == "custom_code"


def test_without_with_code_ignores_error_code_attr():
    record = _record()
    client, _ = _make_client(record)
    exc = RuntimeError("x")
    exc.code = "custom_code"
    client._error_delta_for("r1", record, exc)
    assert client._failure_delta.call_args[1]["code"] == "llm_invoke_failed"
