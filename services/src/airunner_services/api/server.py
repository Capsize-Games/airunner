"""
FastAPI server implementation for AI Runner.

Provides REST and WebSocket endpoints for remote access to AI Runner's
capabilities including LLM, art generation, TTS, and STT.
"""
from typing import Optional, Any
from contextlib import asynccontextmanager
import os
import secrets
from ipaddress import ip_address

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.api.routes import (
    art,
    conversations,
    daemon,
    domain_resources,
    downloads,
    health,
    llm,
    persistence,
    stt,
    tts,
)
from airunner_services.api.routes import legacy as legacy_routes
from airunner_services.data.tenant import reset_tenant_key, set_tenant_key
from airunner_services.runtimes.bootstrap import build_runtime_registry


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def access_logs_enabled() -> bool:
    """Return whether uvicorn access logs should be emitted."""
    return os.environ.get("AIRUNNER_API_ACCESS_LOG", "0") == "1"


def _resolve_runtime_registry(app_instance: Any) -> Optional[Any]:
    """Return or create the runtime registry for an app instance."""
    runtime_registry = getattr(app_instance, "runtime_registry", None)
    if runtime_registry is not None:
        return runtime_registry

    try:
        runtime_registry = build_runtime_registry(app_instance=app_instance)
    except Exception:
        logger.exception("Failed to build runtime registry")
        return None

    try:
        setattr(app_instance, "runtime_registry", runtime_registry)
    except Exception:
        logger.debug("Unable to attach runtime registry to app instance")
    return runtime_registry


def _resolve_lifecycle_service(app_instance: Any) -> Optional[Any]:
    """Return the lifecycle service attached to an app instance."""
    return getattr(app_instance, "lifecycle_service", None)


def is_loopback_host(host: str) -> bool:
    if not host:
        return False

    normalized = host.strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True

    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def is_loopback_request(request: Request) -> bool:
    client = getattr(request, "client", None)
    if not client:
        return False
    return is_loopback_host(getattr(client, "host", ""))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown tasks.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("FastAPI server starting...")
    yield
    # Shutdown
    logger.info("FastAPI server shutting down...")


def create_app(
    allowed_origins: Optional[list] = None,
    enable_cors: bool = True,
    app_instance: Optional[Any] = None,
) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        allowed_origins: List of allowed CORS origins
        enable_cors: Whether to enable CORS
        app_instance: Optional AI Runner app instance for dependency injection

    Returns:
        Configured FastAPI application
    """
    # Store app_instance in app state if provided
    app = FastAPI(
        title="AI Runner API",
        description="REST and WebSocket API for AI Runner",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.state.runtime_registry = None
    app.state.lifecycle_service = None

    try:
        app.state.runtime_registry = build_runtime_registry(
            app_instance=app_instance,
        )
    except Exception:
        logger.exception("Failed to build runtime registry")

    if app_instance:
        app.state.airunner_app = app_instance
        if app.state.runtime_registry is not None:
            try:
                setattr(
                    app_instance,
                    "runtime_registry",
                    app.state.runtime_registry,
                )
            except Exception:
                logger.debug("Unable to attach runtime registry to app instance")
        else:
            app.state.runtime_registry = _resolve_runtime_registry(app_instance)
        app.state.lifecycle_service = _resolve_lifecycle_service(app_instance)

    # Optional API key auth for production.
    # If AIRUNNER_API_KEY is set, requests must provide it via:
    # - X-API-Key: <key>
    # - Authorization: Bearer <key>
    api_key = (os.environ.get("AIRUNNER_API_KEY") or "").strip()
    require_api_key = bool(api_key)
    insecure_no_auth = os.environ.get("AIRUNNER_INSECURE_NO_AUTH", "0") == "1"

    allowed_env = (os.environ.get("AIRUNNER_ALLOWED_TENANT_KEYS") or "").strip()
    allowed_tenants = {t.strip() for t in allowed_env.split(",") if t.strip()}

    @app.middleware("http")
    async def tenant_middleware(request: Request, call_next):
        """Scope DB operations to the request's tenant/namespace.

        Airunner supports Postgres schema tenancy. We select the schema via a
        per-request ContextVar set here.

        Accepted headers (first one wins):
        - X-Tenant-Key
        - X-Uwuchat-Namespace
        - X-Namespace
        """

        header_value = (
            (request.headers.get("x-tenant-key") or "").strip()
            or (request.headers.get("x-uwuchat-namespace") or "").strip()
            or (request.headers.get("x-namespace") or "").strip()
        )

        # Only allow tenant selection from headers:
        # - Without API key auth: loopback requests only.
        # - With API key auth: allowlist-only.
        tenant_key: Optional[str] = None
        if header_value:
            if require_api_key:
                if allowed_tenants and header_value in allowed_tenants:
                    tenant_key = header_value
            else:
                if is_loopback_request(request):
                    tenant_key = header_value

        token = set_tenant_key(tenant_key)
        try:
            return await call_next(request)
        finally:
            reset_tenant_key(token)

    @app.middleware("http")
    async def api_key_auth_middleware(request: Request, call_next):
        path = request.url.path

        # Always allow health checks without auth.
        if path in {"/health", "/api/v1/health"}:
            return await call_next(request)

        # When API key auth is disabled, default to loopback-only unless explicitly overridden.
        if not require_api_key:
            if path.startswith("/admin/"):
                if is_loopback_request(request):
                    return await call_next(request)
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

            if not insecure_no_auth and not is_loopback_request(request):
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})

            return await call_next(request)

        # API key auth enabled: require auth for all endpoints except health.
        provided = (request.headers.get("x-api-key") or "").strip()
        if not provided:
            auth = (request.headers.get("authorization") or "").strip()
            if auth.lower().startswith("bearer "):
                provided = auth.split(" ", 1)[-1].strip()

        if not provided or not secrets.compare_digest(provided, api_key):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        return await call_next(request)

    # Configure CORS
    if enable_cors:
        if allowed_origins is None:
            allowed_origins = [
                "http://localhost",
                "http://localhost:*",
                "http://127.0.0.1",
                "http://127.0.0.1:*",
            ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled with origins: {allowed_origins}")

    # Register routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(daemon.router, prefix="/api/v1/daemon", tags=["daemon"])
    app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])
    app.include_router(
        conversations.router,
        prefix="/api/v1/llm",
        tags=["llm", "conversations"],
    )
    app.include_router(
        persistence.router,
        prefix="/api/v1/state",
        tags=["state"],
    )
    app.include_router(
        persistence.router,
        prefix="/api/v1/persistence",
        tags=["persistence"],
    )
    app.include_router(
        domain_resources.settings_router,
        prefix="/api/v1/settings",
        tags=["settings"],
    )
    app.include_router(
        domain_resources.catalog_router,
        prefix="/api/v1/catalog",
        tags=["catalog"],
    )
    app.include_router(
        domain_resources.library_router,
        prefix="/api/v1/library",
        tags=["library"],
    )
    app.include_router(
        domain_resources.workspace_router,
        prefix="/api/v1/workspace",
        tags=["workspace"],
    )
    app.include_router(art.router, prefix="/api/v1/art", tags=["art"])
    app.include_router(
        downloads.router,
        prefix="/api/v1/downloads",
        tags=["downloads"],
    )
    app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])
    app.include_router(stt.router, prefix="/api/v1/stt", tags=["stt"])

    # Legacy compatibility endpoints for existing clients.
    app.include_router(legacy_routes.router, tags=["legacy"])

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"status": "ready", "service": "airunner"}

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        debug = os.environ.get("AIRUNNER_DEBUG", "0") == "1"
        if debug and is_loopback_request(request):
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(exc)},
            )

        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    return app


class APIServer:
    """FastAPI server wrapper for AI Runner."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8188,
        app_instance=None,
        allowed_origins: Optional[list] = None,
        enable_cors: bool = True,
    ):
        """
        Initialize API server.

        Args:
            host: Host to bind to
            port: Port to listen on
            app_instance: Optional App instance for accessing AI Runner internals
            allowed_origins: List of allowed CORS origins
            enable_cors: Whether to enable CORS
        """
        self.host = host
        self.port = port
        self.app_instance = app_instance
        self.app = create_app(allowed_origins, enable_cors, app_instance=app_instance)

        self.server = None

    def start(self):
        """Start the API server (blocking call)."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=access_logs_enabled(),
        )

        self.server = uvicorn.Server(config)
        logger.info(f"Starting API server on {self.host}:{self.port}")
        self.server.run()

    def stop(self):
        """Stop the API server."""
        if self.server:
            logger.info("Stopping API server...")
            self.server.should_exit = True
            self.server = None
