"""Extensible application framework — Django-app-style extensions.

Extensions live in ``extensions/<name>/`` (top-level repo directory) and
are enabled via the ``EXTENSIONS`` setting.  Each extension provides a
:class:`ExtensionConfig` subclass that declares what the extension
exposes; the framework discovers routes, models, middleware, and
migrations by convention.

Usage::

    # extensions/myapp/config.py
    from airunner_services.extensions.config import ExtensionConfig

    class MyAppExtension(ExtensionConfig):
        name = "myapp"
        label = "My Application"
"""

from airunner_services.extensions.config import ExtensionConfig
from airunner_services.extensions.loader import (
    ExtensionLoader,
)

__all__ = [
    "ExtensionConfig",
    "ExtensionLoader",
]
