"""Language identifiers used internally by the vendored OpenVoice fork.

This fork previously imported AvailableLanguage from the application
(airunner.enums) -- a vendored third-party library should not depend
on this project at all (issue #2190). This is a same-valued local
copy so the fork's internal type system (function signatures,
comparisons) is unchanged. Callers outside this package (see
airunner_services.runtimes.openvoice_model_manager and
.openvoice_runtime_helpers) convert the application's own
AvailableLanguage to this type at the call boundary.
"""

from enum import Enum


class Language(Enum):
    """Languages supported by the OpenVoice runtime."""

    AUTO = "Automatic"
    EN = "EN"
    ES = "ES"
    FR = "FR"
    ZH = "ZH"
    ZH_MIX_EN = "ZH_MIX_EN"
    JP = "JP"
    KR = "KR"
    SP = "SP"
