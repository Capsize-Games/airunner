"""Package-level exports for service-owned LLM config helpers."""

__all__ = [
	"LLMProviderConfig",
	"PRIVACY_CONSENT_SHOWN_KEY",
	"SERVICE_CIVITAI_KEY",
	"SERVICE_DUCKDUCKGO_KEY",
	"SERVICE_HUGGINGFACE_KEY",
	"SERVICE_OPENAI_KEY",
	"SERVICE_OPENMETEO_KEY",
	"SERVICE_OPENROUTER_KEY",
	"SERVICE_POLICY_KEYS",
	"is_civitai_allowed",
	"is_duckduckgo_allowed",
	"is_huggingface_allowed",
	"is_openai_allowed",
	"is_openmeteo_allowed",
	"is_openrouter_allowed",
	"is_service_allowed",
	"privacy_consent_shown",
	"service_default",
	"set_privacy_consent_shown",
	"set_service_allowed",
	"set_service_settings",
]


def __getattr__(name: str):
	"""Resolve config exports lazily from their service-owned modules."""
	if name == "LLMProviderConfig":
		from airunner_services.llm.provider_config import LLMProviderConfig

		return LLMProviderConfig

	if name in {
		"PRIVACY_CONSENT_SHOWN_KEY",
		"SERVICE_CIVITAI_KEY",
		"SERVICE_DUCKDUCKGO_KEY",
		"SERVICE_HUGGINGFACE_KEY",
		"SERVICE_OPENAI_KEY",
		"SERVICE_OPENMETEO_KEY",
		"SERVICE_OPENROUTER_KEY",
		"SERVICE_POLICY_KEYS",
		"is_civitai_allowed",
		"is_duckduckgo_allowed",
		"is_huggingface_allowed",
		"is_openai_allowed",
		"is_openmeteo_allowed",
		"is_openrouter_allowed",
		"is_service_allowed",
		"privacy_consent_shown",
		"service_default",
		"set_privacy_consent_shown",
		"set_service_allowed",
		"set_service_settings",
	}:
		from airunner_services.downloads import policy

		return getattr(policy, name)

	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
