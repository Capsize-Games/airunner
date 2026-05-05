"""Trust levels for AIRunner coding projects."""

from enum import Enum


class AirunnerTrustLevel(str, Enum):
    """Supported trust levels for an AIRunner coding project."""

    UNTRUSTED = "untrusted"
    TRUSTED = "trusted"