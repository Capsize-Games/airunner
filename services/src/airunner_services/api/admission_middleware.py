"""Apply capacity limits inside authentication for expensive HTTP routes."""

import os

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .admission_budget import AdmissionBudget

GENERATION_PATHS = frozenset({
    "/api/chat", "/api/generate", "/api/embed", "/api/embeddings",
    "/v1/chat/completions", "/llm/generate", "/llm/generate_batch",
    "/api/v1/llm/chat", "/api/v1/llm/completion", "/art",
    "/api/v1/art/generate", "/api/v1/tts/synthesize",
    "/api/v1/stt/transcribe", "/api/v1/llm/rag/index",
    "/api/v1/llm/rag/reindex",
})


def _positive_limit(name: str, default: int) -> int:
    """Reject disabled, invalid or excessive capacity configuration."""
    value = int(os.environ.get(name, str(default)))
    if not 1 <= value <= 10000:
        raise ValueError(f"{name} must be between 1 and 10000")
    return value


class AdmissionMiddleware:
    """Hold slots through streams, errors and disconnected responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.generation = AdmissionBudget(
            _positive_limit("AIRUNNER_HTTP_MAX_INFLIGHT", 4),
            _positive_limit("AIRUNNER_HTTP_REQUESTS_PER_MINUTE", 60),
        )
        self.setup = AdmissionBudget(
            _positive_limit("AIRUNNER_SETUP_MAX_INFLIGHT", 1),
            _positive_limit("AIRUNNER_SETUP_REQUESTS_PER_MINUTE", 5),
        )

    def _budget(self, scope: Scope) -> AdmissionBudget | None:
        if scope["type"] != "http" or scope["method"] != "POST":
            return None
        path = scope["path"].rstrip("/")
        if path in {"/api/v1/install", "/api/pull"}:
            return self.setup
        return self.generation if path in GENERATION_PATHS else None

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send,
    ) -> None:
        budget = self._budget(scope)
        if budget is None:
            await self.app(scope, receive, send)
            return
        if not budget.acquire():
            response = JSONResponse(
                {"error": "capacity_exceeded"}, status_code=429,
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        finally:
            budget.release()
