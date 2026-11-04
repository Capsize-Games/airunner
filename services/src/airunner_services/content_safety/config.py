"""Configuration for the optional application content-policy integration."""

from __future__ import annotations

import os
from typing import Final, Literal

CONTENT_POLICY_MODE_ENV_VAR: Final = "AIRUNNER_CONTENT_POLICY_MODE"
CONTENT_POLICY_DISABLED: Final = "disabled"
CONTENT_POLICY_ENFORCE: Final = "enforce"
ContentPolicyMode = Literal["disabled", "enforce"]


class ContentPolicyConfigurationError(ValueError):
    """The application content-policy mode is not a supported value."""


def resolve_content_policy_mode() -> ContentPolicyMode:
    """Return the configured mode, defaulting only when the variable is absent.

    The accepted values are deliberately exact so misspellings and legacy
    boolean spellings cannot silently turn enforcement off.
    """
    raw = os.environ.get(CONTENT_POLICY_MODE_ENV_VAR)
    if raw is None:
        return CONTENT_POLICY_DISABLED

    if raw == CONTENT_POLICY_DISABLED:
        return CONTENT_POLICY_DISABLED
    if raw == CONTENT_POLICY_ENFORCE:
        return CONTENT_POLICY_ENFORCE
    raise ContentPolicyConfigurationError(
        f"{CONTENT_POLICY_MODE_ENV_VAR} must be exactly "
        f"'{CONTENT_POLICY_DISABLED}' or '{CONTENT_POLICY_ENFORCE}'"
    )


def content_policy_is_enforced() -> bool:
    """Return whether application content policy is explicitly enabled."""
    return resolve_content_policy_mode() == CONTENT_POLICY_ENFORCE


# Validate early whenever the content-safety package is imported by a service
# entry point. Calls still resolve dynamically so a runtime environment change
# to an invalid value cannot silently continue under a previous mode.
resolve_content_policy_mode()


__all__ = [
    "CONTENT_POLICY_DISABLED",
    "CONTENT_POLICY_ENFORCE",
    "CONTENT_POLICY_MODE_ENV_VAR",
    "ContentPolicyConfigurationError",
    "ContentPolicyMode",
    "content_policy_is_enforced",
    "resolve_content_policy_mode",
]
