"""
HTTP API endpoints for AI Runner: /llm, /art, /stt, /tts
- /llm: POST, accepts LLMRequest dict, streams LLMResponse dicts (NDJSON)
- /art: POST, accepts ImageRequest dict, returns ImageResponse dict
- /stt, /tts: POST, stubbed
"""

import json
from http.server import BaseHTTPRequestHandler
from airunner.api.api import API
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)

api = API()


class AIRunnerAPIRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        path = self.path.rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self._set_headers(400)
            self.wfile.write(
                json.dumps({"error": "Invalid JSON"}).encode("utf-8")
            )
            return
        if path == "/llm":
            self._handle_llm(data)
        elif path == "/art":
            self._handle_art(data)
        elif path == "/stt":
            self._handle_stub("STT not implemented")
        elif path == "/tts":
            self._handle_stub("TTS not implemented")
        else:
            self._set_headers(404)
            self.wfile.write(
                json.dumps({"error": "Not found"}).encode("utf-8")
            )

    def _handle_llm(self, data):
        self._set_headers(200, content_type="application/x-ndjson")
        # For now, just stream a single fake LLMResponse as NDJSON
        response = LLMResponse(
            message="Game started! (stub)",
            is_first_message=True,
            is_end_of_message=True,
        )
        self.wfile.write(json.dumps(response.__dict__).encode("utf-8") + b"\n")
        self.wfile.flush()
        # In the future, yield multiple responses for streaming

    def _handle_art(self, data):
        self._set_headers(200)
        # For now, just return a stub ImageResponse
        response = ImageResponse(
            images=None,
            data=None,
            nsfw_content_detected=False,
            active_rect=None,
            is_outpaint=False,
        )
        self.wfile.write(json.dumps(response.to_dict()).encode("utf-8"))

    def _handle_stub(self, msg):
        self._set_headers(200)
        self.wfile.write(json.dumps({"result": msg}).encode("utf-8"))


# Usage: pass AIRunnerAPIRequestHandler to your HTTP server for /llm, /art, /stt, /tts endpoints.
