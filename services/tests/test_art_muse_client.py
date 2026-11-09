"""Tests for the Muse cloud art runtime client."""

from __future__ import annotations

import base64
from typing import Any, Optional

import pytest

from airunner_services.ipc.messages import RequestEnvelope
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest, RuntimeAction, RuntimeKind, RuntimeMode,
)
from airunner_services.runtimes.muse_art_client import (
    MuseArtClient, register_muse_art_client,
)
from airunner_services.runtimes.muse_art_helpers import MuseArtSettings
from airunner_services.runtimes.registry import RuntimeRegistry

IMG_B64 = base64.b64encode(b"fake-png-bytes").decode("ascii")

class FakeResponse:
    """Minimal response double for the Muse session protocol."""

    def __init__(
        self, status_code: int = 200, payload: Any = None,
        content: bytes = b"", json_error: bool = False,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self._json_error = json_error

    def json(self) -> Any:
        if self._json_error:
            raise ValueError("not json")
        return self._payload

class FakeSession:
    """Session double recording post/get calls."""

    def __init__(
        self, post_response: Any = None, get_response: Any = None,
        post_error: Optional[Exception] = None,
    ) -> None:
        self._post_response = post_response
        self._get_response = get_response
        self._post_error = post_error
        self.posts: list[dict[str, Any]] = []
        self.gets: list[dict[str, Any]] = []
        self.closed = False

    def post(self, url: str, **kwargs: Any) -> Any:
        self.posts.append({"url": url, **kwargs})
        if self._post_error is not None:
            raise self._post_error
        return self._post_response

    def get(self, url: str, **kwargs: Any) -> Any:
        self.gets.append({"url": url, **kwargs})
        return self._get_response

    def close(self) -> None:
        self.closed = True

def settings(**kwargs: Any) -> MuseArtSettings:
    base: dict[str, Any] = {"api_key": "test-key"}
    base.update(kwargs)
    return MuseArtSettings(**base)

def envelope(**payload_kwargs: Any) -> RequestEnvelope:
    payload: dict[str, Any] = {"prompt": "a lighthouse"}
    payload.update(payload_kwargs)
    return RequestEnvelope(
        request_id="req-1", runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE, provider="muse", payload=payload,
    )

def ok_session() -> FakeSession:
    return FakeSession(
        post_response=FakeResponse(payload={"data": [{"b64_json": IMG_B64}]})
    )

def test_settings_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    for name in ("AIRUNNER_MUSE_BASE_URL", "AIRUNNER_MUSE_MODEL",
                 "AIRUNNER_MUSE_TIMEOUT_S", "AIRUNNER_MUSE_MAX_IMAGE_BYTES"):
        monkeypatch.delenv(name, raising=False)
    resolved = MuseArtSettings.from_env()
    assert resolved.base_url == "https://api.meta.ai/v1"
    assert resolved.model == "muse-image-1.0"
    assert resolved.api_key == ""

def test_settings_from_env_overrides() -> None:
    resolved = MuseArtSettings.from_env({
        "MODEL_API_KEY": "secret", "AIRUNNER_MUSE_BASE_URL": "https://x/v1/",
        "AIRUNNER_MUSE_MODEL": "muse-image-2", "AIRUNNER_MUSE_TIMEOUT_S": "5",
        "AIRUNNER_MUSE_MAX_IMAGE_BYTES": "10",
        "AIRUNNER_MUSE_API_KEY": "wrong-key-source",
    })
    assert resolved.api_key == "secret"
    assert resolved.base_url == "https://x/v1"
    assert resolved.model == "muse-image-2"
    assert resolved.timeout_s == 5.0
    assert resolved.max_image_bytes == 10

def test_happy_b64_envelope() -> None:
    session = ok_session()
    client = MuseArtClient(settings=settings(), session=session)
    events: list[dict[str, Any]] = []
    response = client.invoke_with_progress(envelope(), events.append)
    assert response.status.value == "succeeded"
    assert response.payload == {"images": [IMG_B64]}
    assert response.metadata == {
        "provider": "muse", "model": "muse-image-1.0", "image_count": 1}
    assert "secret" not in str(response.metadata)
    assert "lighthouse" not in str(response.metadata)
    post = session.posts[0]
    assert post["url"] == "https://api.meta.ai/v1/images/generations"
    assert post["json"]["model"] == "muse-image-1.0"
    assert post["json"]["prompt"] == "a lighthouse"
    assert post["headers"]["Authorization"] == "Bearer test-key"
    assert events and events[0]["status"] == "running"

def test_happy_direct_invocation() -> None:
    client = MuseArtClient(settings=settings(), session=ok_session())
    response = client.invoke(ArtInvocationRequest(prompt="direct"))
    assert response.status.value == "succeeded"
    assert response.payload["images"] == [IMG_B64]
    assert response.request_id.startswith("muse-")

def test_happy_url_result_is_fetched_and_encoded() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            payload={"data": [{"url": "https://8.8.8.8/i.png"}]}),
        get_response=FakeResponse(content=b"url-bytes"),
    )
    client = MuseArtClient(settings=settings(), session=session)
    response = client.invoke(envelope())
    expected = base64.b64encode(b"url-bytes").decode("ascii")
    assert response.payload == {"images": [expected]}
    assert session.gets[0]["url"] == "https://8.8.8.8/i.png"

def test_descriptor_and_registration() -> None:
    client = MuseArtClient(settings=settings(), session=ok_session())
    assert client.descriptor.provider == "muse"
    assert client.descriptor.mode is RuntimeMode.CLOUD
    registry = RuntimeRegistry()
    register_muse_art_client(registry, client)
    assert registry.resolve(RuntimeKind.ART, "muse", "cloud") is client

def test_healthcheck_ready_and_missing_key() -> None:
    ready = MuseArtClient(settings=settings(), session=ok_session())
    assert ready.healthcheck().status.value == "ready"
    missing = MuseArtClient(
        settings=MuseArtSettings(api_key=""), session=ok_session())
    assert missing.healthcheck().status.value == "failed"
    response = missing.invoke(envelope())
    assert response.error.code == "muse_auth_error"

def test_cancel_returns_cancelled() -> None:
    client = MuseArtClient(settings=settings(), session=ok_session())
    response = client.cancel("req-9")
    assert response.status.value == "cancelled"
    assert response.metadata["provider"] == "muse"

@pytest.mark.parametrize("status_code,code,retryable", [
    (401, "muse_auth_error", False), (403, "muse_auth_error", False),
    (429, "muse_rate_limited", True), (500, "muse_upstream_error", True),
    (502, "muse_upstream_error", True),
])
def test_http_error_mapping(
    status_code: int, code: str, retryable: bool
) -> None:
    session = FakeSession(post_response=FakeResponse(status_code=status_code))
    client = MuseArtClient(settings=settings(), session=session)
    response = client.invoke(envelope())
    assert response.status.value == "failed"
    assert response.error.code == code
    assert response.error.retryable is retryable
    assert "lighthouse" not in response.error.message

def test_timeout_is_retryable() -> None:
    session = FakeSession(post_error=TimeoutError("slow"))
    client = MuseArtClient(settings=settings(), session=session)
    response = client.invoke(envelope())
    assert response.error.code == "muse_timeout"
    assert response.error.retryable is True

def test_malformed_json() -> None:
    session = FakeSession(post_response=FakeResponse(json_error=True))
    client = MuseArtClient(settings=settings(), session=session)
    response = client.invoke(envelope())
    assert response.error.code == "muse_malformed_response"

@pytest.mark.parametrize("payload", [{}, {"data": []}, {"images": []}])
def test_missing_data(payload: dict[str, Any]) -> None:
    session = FakeSession(post_response=FakeResponse(payload=payload))
    client = MuseArtClient(settings=settings(), session=session)
    response = client.invoke(envelope())
    assert response.error.code == "muse_missing_data"

def test_oversize_b64_rejected() -> None:
    session = ok_session()
    client = MuseArtClient(
        settings=settings(max_image_bytes=2), session=session)
    response = client.invoke(envelope())
    assert response.error.code == "muse_image_too_large"

def test_http_url_result_rejected_without_fetch() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            payload={"data": [{"url": "http://cdn.example/i.png"}]}),
        get_response=FakeResponse(content=b"x"),
    )
    client = MuseArtClient(settings=settings(), session=session)
    response = client.invoke(envelope())
    assert response.error.code == "muse_invalid_image_url"
    assert session.gets == []

def test_oversize_url_result_rejected() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            payload={"data": [{"url": "https://8.8.8.8/i.png"}]}),
        get_response=FakeResponse(content=b"123456"),
    )
    client = MuseArtClient(
        settings=settings(max_image_bytes=2), session=session)
    response = client.invoke(envelope())
    assert response.error.code == "muse_image_too_large"

def test_negative_prompt_rejected() -> None:
    client = MuseArtClient(settings=settings(), session=ok_session())
    with pytest.raises(ValueError):
        client.invoke(envelope(negative_prompt="no cats"))

def test_image_b64_metadata_rejected() -> None:
    client = MuseArtClient(settings=settings(), session=ok_session())
    with pytest.raises(ValueError):
        client.invoke(envelope(metadata={"image_b64": IMG_B64}))

def test_wrong_provider_rejected() -> None:
    client = MuseArtClient(settings=settings(), session=ok_session())
    bad = RequestEnvelope(
        request_id="r", runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE, provider="local",
        payload={"prompt": "x"},
    )
    with pytest.raises(ValueError):
        client.invoke(bad)
