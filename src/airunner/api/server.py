"""
FastAPI server implementation for AI Runner.

Provides REST and WebSocket endpoints for remote access to AI Runner's
capabilities including LLM, art generation, TTS, and STT.
"""

from typing import Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.api.routes import health, llm, art, tts, stt, vision


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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

    if app_instance:
        app.state.airunner_app = app_instance

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
    app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])
    app.include_router(art.router, prefix="/api/v1/art", tags=["art"])
    app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])
    app.include_router(stt.router, prefix="/api/v1/stt", tags=["stt"])
    app.include_router(vision.router, prefix="/api/v1/vision", tags=["vision"])

    # Legacy routes for backwards compatibility (fastsearch uses /vision/*)
    app.include_router(vision.router, prefix="/vision", tags=["vision-legacy"])

    # Root health check for simple health probes
    @app.get("/health")
    async def root_health():
        """Root-level health check for container health probes."""
        return {"status": "ready"}

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"status": "ready", "service": "airunner"}

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

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
        self.app = create_app(allowed_origins, enable_cors)

        # Store app_instance in FastAPI app state for route handlers to access
        if app_instance:
            self.app.state.airunner_app = app_instance

        self.server = None

    def start(self):
        """Start the API server (blocking call)."""
        config = uvicorn.Config(
            self.app, host=self.host, port=self.port, log_level="info"
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
