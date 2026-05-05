"""Persistent prompt profiles for AIRunner coding request modes."""

from dataclasses import dataclass

from airunner.utils.settings import get_qsettings


_PROMPT_GROUP = "coding_prompt_profiles"
_SELECTED_PROFILE_KEY = "selected_profile"


@dataclass(frozen=True)
class CodingPromptProfile:
    """Describe one editable coding prompt profile."""

    key: str
    label: str
    default_prompt: str


_PROFILES = (
    CodingPromptProfile(
        key="code-ask",
        label="Code Ask Agent",
        default_prompt=(
            "You are a code-focused assistant for questions about the current "
            "project. Explain tradeoffs clearly, reference relevant files when "
            "needed, and stay in ask-only mode. Do not edit files or run "
            "commands unless the user explicitly switches to Agent mode."
        ),
    ),
    CodingPromptProfile(
        key="code-plan",
        label="Code Planning Agent",
        default_prompt=(
            "You are a planning-first software engineer. Inspect the current "
            "workspace as needed, then produce a concise implementation plan, "
            "the files likely to change, and the validations to run. Do not "
            "edit files or execute commands."
        ),
    ),
    CodingPromptProfile(
        key="code-agent",
        label="Code Agent",
        default_prompt=(
            "You are an active coding agent working in the current project. "
            "Inspect files before editing, keep changes minimal, validate the "
            "result, and report concrete outcomes. Prefer direct action over "
            "long explanations when implementation is requested."
        ),
    ),
)


def coding_prompt_profiles() -> tuple[CodingPromptProfile, ...]:
    """Return the editable coding prompt profiles."""
    return _PROFILES


def get_coding_prompt_profile(key: str | None) -> CodingPromptProfile:
    """Return one coding prompt profile by key."""
    for profile in _PROFILES:
        if profile.key == key:
            return profile
    return _PROFILES[-1]


def load_coding_prompt(key: str) -> str:
    """Load one coding prompt from QSettings or fall back to default."""
    settings = get_qsettings()
    settings.beginGroup(_PROMPT_GROUP)
    value = settings.value(key, "", type=str)
    settings.endGroup()
    if value and value.strip():
        return value
    return get_coding_prompt_profile(key).default_prompt


def save_coding_prompt(key: str, prompt: str) -> None:
    """Persist one coding prompt profile."""
    settings = get_qsettings()
    settings.beginGroup(_PROMPT_GROUP)
    settings.setValue(key, prompt)
    settings.endGroup()


def reset_coding_prompt(key: str) -> str:
    """Reset one coding prompt profile to its default value."""
    prompt = get_coding_prompt_profile(key).default_prompt
    save_coding_prompt(key, prompt)
    return prompt


def load_selected_coding_prompt_profile() -> str:
    """Return the last coding prompt profile selected in preferences."""
    settings = get_qsettings()
    settings.beginGroup(_PROMPT_GROUP)
    key = settings.value(_SELECTED_PROFILE_KEY, "chatbot", type=str)
    settings.endGroup()
    return str(key or "chatbot")


def save_selected_coding_prompt_profile(key: str) -> None:
    """Persist the selected preferences prompt profile key."""
    settings = get_qsettings()
    settings.beginGroup(_PROMPT_GROUP)
    settings.setValue(_SELECTED_PROFILE_KEY, key)
    settings.endGroup()