"""HTTP response helper mixin for legacy API handlers."""

import json


class ResponseHelperMixin:
    """Mixin providing HTTP response helpers for BaseHTTPRequestHandler."""

    def _set_headers(self, status=200, content_type="application/json"):
        """Set CORS-enabled response headers."""
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _send_json_response(self, data: dict, status: int = 200):
        """Send a complete JSON response with proper Content-Length header."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_text_response(self, text: str, status: int = 200):
        """Send a complete text response with proper Content-Length header."""
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes_response(
        self,
        data: bytes,
        *,
        status: int = 200,
        content_type: str = "application/octet-stream",
    ):
        """Send a binary response with proper Content-Length header."""
        body = data or b""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_parse_error(self, error_msg: str):
        """Send a 400 parse error response."""
        self._send_json_response(
            {"error": f"Failed to parse request: {error_msg}"},
            status=400,
        )
