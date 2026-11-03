"""Cancellable stdlib HTTP transport for sidecar requests."""

from __future__ import annotations

import http.client
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request


class CancellableHTTPResponse:
    """Expose a response while keeping its owning socket interruptible."""

    def __init__(
        self,
        transport: "CancellableHTTPTransport",
        response: http.client.HTTPResponse,
    ) -> None:
        self._transport = transport
        self._response = response

    def __enter__(self) -> "CancellableHTTPResponse":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        """Read response bytes from the owned HTTP response."""
        return self._response.read(*args, **kwargs)

    def readline(self, *args: Any, **kwargs: Any) -> bytes:
        """Read one response line from the owned HTTP response."""
        return self._response.readline(*args, **kwargs)

    def close(self) -> None:
        """Close this response and its transport connection."""
        self._transport.close()

    def interrupt(self) -> None:
        """Interrupt this response's socket without affecting other requests."""
        self._transport.interrupt()


class CancellableHTTPTransport:
    """Open one HTTP connection with a handle available before response headers."""

    def __init__(self, request: Request, timeout: float) -> None:
        self._request = request
        self._timeout = timeout
        self._interrupted = False
        self._closed = False
        self._connection = self._make_connection(request.full_url, timeout)
        self._response: http.client.HTTPResponse | None = None

    @staticmethod
    def _make_connection(url: str, timeout: float) -> http.client.HTTPConnection:
        """Create the stdlib connection for an HTTP or HTTPS URL."""
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise ValueError("Sidecar endpoint must use HTTP or HTTPS")
        port = parsed.port
        connection_type = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        return connection_type(parsed.hostname, port, timeout=timeout)

    def open(self) -> CancellableHTTPResponse:
        """Send the request and return its interruptible response handle."""
        if self._interrupted:
            raise OSError("Sidecar request was cancelled")
        parsed = urlsplit(self._request.full_url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        headers = dict(self._request.header_items())
        headers.setdefault("Accept-Encoding", "identity")
        try:
            self._connection.request(
                self._request.get_method(),
                path,
                body=self._request.data,
                headers=headers,
            )
            if self._interrupted:
                raise OSError("Sidecar request was cancelled")
            response = self._connection.getresponse()
            self._response = response
            if response.status >= 400:
                raise HTTPError(
                    self._request.full_url,
                    response.status,
                    response.reason,
                    response.headers,
                    response,
                )
            return CancellableHTTPResponse(self, response)
        except HTTPError:
            raise
        except OSError as exc:
            if self._interrupted:
                raise
            raise URLError(exc) from exc

    def interrupt(self) -> None:
        """Shut down only this request's socket to release blocked reads."""
        self._interrupted = True
        connection = self._connection
        sock = connection.sock
        response = self._response
        if sock is None and response is not None:
            file_pointer = getattr(response, "fp", None)
            raw = getattr(file_pointer, "raw", None)
            sock = getattr(raw, "_sock", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        connection.close()

    def close(self) -> None:
        """Close this response and its owned connection."""
        if self._closed:
            return
        self._closed = True
        response = self._response
        if response is not None:
            try:
                response.close()
            except OSError:
                pass
        self._connection.close()
