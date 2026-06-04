"""Component-control routes for art API endpoints."""

from fastapi import APIRouter, Request

from airunner_services.runtimes.contracts import RuntimeAction

from .art_contracts import ArtComponentResponse
from .art_runtime import invoke_art_control

router = APIRouter()


@router.delete("/unload")
async def unload_art_model(req: Request):
    """Unload the active art model while keeping the sidecar alive."""
    await invoke_art_control(req, action=RuntimeAction.UNLOAD_MODEL)
    return {"status": "unloaded"}


@router.post(
    "/components/{component}/load",
    response_model=ArtComponentResponse,
)
async def load_art_component(component: str, req: Request):
    """Load one explicit art component through the runtime contract."""
    await invoke_art_control(
        req,
        action=RuntimeAction.LOAD_MODEL,
        component=component,
    )
    return ArtComponentResponse(component=component, status="loaded")


@router.delete(
    "/components/{component}/unload",
    response_model=ArtComponentResponse,
)
async def unload_art_component(component: str, req: Request):
    """Unload one explicit art component through the runtime contract."""
    await invoke_art_control(
        req,
        action=RuntimeAction.UNLOAD_MODEL,
        component=component,
    )
    return ArtComponentResponse(component=component, status="unloaded")