"""Judge-provider helpers for AIRunner eval suites."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from typing import Protocol

import requests

from airunner_services.eval.client import AIRunnerClient
from airunner_services.settings import AIRUNNER_LLM_OPENROUTER_MODEL


JUDGE_SERVICE_ENV = "AIRUNNER_TEST_JUDGE_SERVICE"
JUDGE_MODEL_ENV = "AIRUNNER_TEST_JUDGE_MODEL"
_DEFAULT_SERVICE = "airunner"
_SERVICE_ALIASES = {
    "airunner": "airunner",
    "local": "airunner",
    "groq": "groq",
    "openrouter": "openrouter",
}
_SERVICE_API_KEYS = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
_SERVICE_URLS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}
_SERVICE_DEFAULT_MODELS = {
    "openrouter": AIRUNNER_LLM_OPENROUTER_MODEL,
}


class JudgeClient(Protocol):
    """Protocol for judge transports used by evaluators."""

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Return one non-streaming model response."""


class JudgeProviderError(RuntimeError):
    """Raised when judge-provider configuration is invalid."""


@dataclass(frozen=True)
class JudgeConfig:
    """Resolved judge-provider configuration."""

    service: str
    model: str | None

    @classmethod
    def from_env(
        cls,
        candidate_model: str,
        *,
        judge_service: str | None = None,
        judge_model: str | None = None,
    ) -> JudgeConfig:
        """Return one resolved judge configuration."""
        service_name = judge_service or os.environ.get(JUDGE_SERVICE_ENV)
        model_name = judge_model or os.environ.get(JUDGE_MODEL_ENV)
        service = _resolve_service(service_name)
        model = _resolve_model(service, candidate_model, model_name)
        return cls(service=service, model=model)

    def build_client(self, base_url: str) -> JudgeClient:
        """Return the client for this judge configuration."""
        if self.service == _DEFAULT_SERVICE:
            return AIRunnerClient(base_url=base_url)
        return OpenAIJudgeClient.for_service(self.service)


class OpenAIJudgeClient:
    """Minimal OpenAI-compatible client for external judge providers."""

    def __init__(
        self,
        *,
        service: str,
        api_url: str,
        api_key: str,
        timeout: int = 300,
    ) -> None:
        """Initialize one external judge client."""
        self.service = service
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def for_service(cls, service: str) -> OpenAIJudgeClient:
        """Build one external judge client for a supported service."""
        normalized_service = _resolve_service(service)
        api_key = _required_api_key(normalized_service)
        return cls(
            service=normalized_service,
            api_url=_SERVICE_URLS[normalized_service],
            api_key=api_key,
        )

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Return one non-streaming judge response."""
        if stream:
            raise ValueError("Judge clients do not support streaming")
        request_data = _build_request_data(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        request_data.update(_supported_request_kwargs(kwargs))
        response_data = self._post(request_data)
        return {"text": _extract_text(response_data), "raw_response": response_data}

    def _headers(self) -> dict[str, str]:
        """Return request headers for one judge service."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.service == "openrouter":
            headers["X-Title"] = "AIRunner Eval"
        return headers

    def _post(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Post one chat-completions request and return parsed JSON."""
        try:
            response = requests.post(
                self.api_url,
                json=request_data,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise JudgeProviderError(
                f"Judge request failed for {self.service}: {error}"
            ) from error
        return response.json()


def _resolve_service(service_name: str | None) -> str:
    """Return one normalized judge service name."""
    name = (service_name or _DEFAULT_SERVICE).strip().lower()
    try:
        return _SERVICE_ALIASES[name]
    except KeyError as error:
        supported = ", ".join(sorted(_SERVICE_ALIASES))
        raise JudgeProviderError(
            f"Unsupported judge service '{service_name}'. "
            f"Supported values: {supported}"
        ) from error


def _resolve_model(
    service: str,
    candidate_model: str,
    judge_model: str | None,
) -> str:
    """Return one resolved judge model name."""
    if judge_model:
        return judge_model
    if service == _DEFAULT_SERVICE:
        return candidate_model
    default_model = _SERVICE_DEFAULT_MODELS.get(service)
    if default_model:
        return default_model
    raise JudgeProviderError(
        f"Judge model required for service '{service}'"
    )


def _required_api_key(service: str) -> str:
    """Return the API key for one external judge service."""
    env_name = _SERVICE_API_KEYS[service]
    api_key = os.environ.get(env_name)
    if api_key:
        return api_key
    raise JudgeProviderError(
        f"{env_name} environment variable required for {service}. "
        f"Ensure it is exported before running pytest, for example: "
        f"'source ~/.bashrc && export {env_name}=\"${env_name}\"'"
    )


def _build_request_data(
    *,
    prompt: str,
    model: str | None,
    max_tokens: int | None,
    temperature: float | None,
) -> dict[str, Any]:
    """Return one OpenAI-compatible chat-completions payload."""
    if not model:
        raise JudgeProviderError("Judge model is required")
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens or 128,
        "temperature": 0.3 if temperature is None else temperature,
    }


def _supported_request_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return provider kwargs supported by chat-completions APIs."""
    supported_keys = {
        "frequency_penalty",
        "presence_penalty",
        "response_format",
        "stop",
        "top_p",
    }
    return {
        key: value
        for key, value in kwargs.items()
        if key in supported_keys and value is not None
    }


def _extract_text(response_data: dict[str, Any]) -> str:
    """Return the first text payload from one chat-completions response."""
    choices = response_data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, str):
        return content
    return "".join(_content_part_text(part) for part in content)


def _content_part_text(part: Any) -> str:
    """Return one content-part text fragment."""
    if not isinstance(part, dict):
        return ""
    return str(part.get("text") or "")