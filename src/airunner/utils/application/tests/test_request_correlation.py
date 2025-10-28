"""
Tests for request-response correlation in signal mediator.

Verifies that HTTP requests can be correlated with async responses
using request_id tracking and callbacks.
"""

import pytest
import time
import threading
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.enums import SignalCode


def test_pending_request_registration():
    """Test that pending requests can be registered and unregistered."""
    mediator = SignalMediator()

    request_id = "test-request-123"
    response_queue = mediator.register_pending_request(request_id)

    assert request_id in mediator._pending_requests
    assert response_queue is not None

    mediator.unregister_pending_request(request_id)
    assert request_id not in mediator._pending_requests


def test_request_response_correlation():
    """Test that responses are routed to correct pending request."""
    mediator = SignalMediator()

    request_id = "test-request-456"
    response_queue = mediator.register_pending_request(request_id)

    # Simulate sending a response with request_id
    response_data = {
        "request_id": request_id,
        "message": "Test response",
        "status": "success",
    }

    # Emit signal with request_id
    mediator.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, response_data)

    # Wait for response (with short timeout)
    received = mediator.wait_for_response(request_id, timeout=1.0)

    assert received is not None
    assert received["message"] == "Test response"
    assert received["status"] == "success"

    mediator.unregister_pending_request(request_id)


def test_callback_invoked_on_response():
    """Test that callback is invoked when response arrives."""
    mediator = SignalMediator()

    request_id = "test-request-789"
    callback_data = []

    def callback(data: dict):
        callback_data.append(data)

    mediator.register_pending_request(request_id, callback)

    # Emit response
    response_data = {"request_id": request_id, "message": "Callback test"}
    mediator.emit_signal(SignalCode.LLM_TEXT_STREAMED_SIGNAL, response_data)

    # Give callback time to execute
    time.sleep(0.1)

    assert len(callback_data) == 1
    assert callback_data[0]["message"] == "Callback test"

    mediator.unregister_pending_request(request_id)


def test_timeout_on_no_response():
    """Test that wait_for_response returns None on timeout."""
    mediator = SignalMediator()

    request_id = "test-request-timeout"
    mediator.register_pending_request(request_id)

    # Don't emit any response - should timeout
    received = mediator.wait_for_response(request_id, timeout=0.5)

    assert received is None

    mediator.unregister_pending_request(request_id)


def test_multiple_pending_requests():
    """Test that multiple pending requests are tracked independently."""
    mediator = SignalMediator()

    request_id_1 = "test-request-multi-1"
    request_id_2 = "test-request-multi-2"

    mediator.register_pending_request(request_id_1)
    mediator.register_pending_request(request_id_2)

    # Emit response for request 2
    mediator.emit_signal(
        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
        {"request_id": request_id_2, "message": "Response 2"},
    )

    # Only request 2 should receive response
    response_1 = mediator.wait_for_response(request_id_1, timeout=0.1)
    response_2 = mediator.wait_for_response(request_id_2, timeout=0.1)

    assert response_1 is None  # Timeout
    assert response_2 is not None
    assert response_2["message"] == "Response 2"

    mediator.unregister_pending_request(request_id_1)
    mediator.unregister_pending_request(request_id_2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
