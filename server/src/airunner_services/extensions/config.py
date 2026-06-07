"""Extension configuration — analogous to Django's AppConfig."""

from __future__ import annotations

from typing import Optional


class ExtensionConfig:
    """Base class for one extension's configuration.

    Subclasses define the extension's identity and optionally override
    the auto-discovered module paths.

    Minimal example::

        class AuthExtension(ExtensionConfig):
            name = "auth"
            label = "Authentication"

    The framework then discovers:
    - ``extensions/auth/server/routes.py`` → FastAPI router
    - ``extensions/auth/server/models.py`` → SQLAlchemy models
    - ``extensions/auth/server/middleware.py`` → register(app) function
    - ``extensions/auth/server/migrations/`` → Alembic migrations
    - ``extensions/auth/client/routes.tsx`` → React route objects
    - ``extensions/auth/client/Provider.tsx`` → React provider component
    """

    name: str = ""
    label: str = ""
    description: str = ""

    # ---- Overridable module paths ----
    # By convention these are derived from `name`:
    #   extensions.{name}.server.routes
    #   extensions.{name}.server.models
    #   extensions.{name}.server.middleware
    server_routes_module: Optional[str] = None
    server_models_module: Optional[str] = None
    server_middleware_module: Optional[str] = None

    def ready(self) -> None:
        """Called once after the extension and its hooks are loaded.

        Override for one-time initialisation (e.g. registering signals).
        """
