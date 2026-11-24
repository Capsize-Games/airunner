"""Stdio MCP server exposing AI Runner image generation as tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Image, MCPServer

from airunner_services.mcp.config import MCPConfig
from airunner_services.mcp.daemon_client import ArtDaemonClient, DaemonError
from airunner_services.mcp.payloads import (
    build_batch_payloads,
    build_generation_payload,
    load_input_image_b64,
)

SERVER_NAME = "airunner-image"


def _save_png(
    config: MCPConfig, job_id: str, index: int, data: bytes
) -> str:
    """Save PNG bytes under the output dir and return the file path."""
    target_dir = Path(config.output_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{job_id}-{index}.png"
    path.write_bytes(data)
    return str(path)


def run_generation(
    client: ArtDaemonClient,
    config: MCPConfig,
    payload: dict[str, Any],
) -> list[Any]:
    """Start a job, wait for it, save PNGs, return summary + images."""
    job_id = client.start_generation(payload)
    status = client.wait_for_completion(job_id)
    count = int(status.get("image_count", 0) or 0)
    saved = [
        _save_png(config, job_id, index, client.fetch_png(job_id, index))
        for index in range(max(count, 1))
    ]
    summary = {
        "job_id": job_id,
        "status": status.get("status"),
        "image_count": len(saved),
        "files": saved,
    }
    return [summary, *(Image(path=item) for item in saved)]


def run_generation_batch(
    client: ArtDaemonClient,
    config: MCPConfig,
    payloads: list[dict[str, Any]],
) -> list[Any]:
    """Run each payload sequentially, returning summaries + images."""
    summaries: list[dict[str, Any]] = []
    images: list[Any] = []
    files: list[str] = []
    for payload in payloads:
        outcome = run_generation(client, config, payload)
        summaries.append(outcome[0])
        images.extend(outcome[1:])
        files.extend(outcome[0].get("files", []))
    summary = {
        "job_count": len(summaries),
        "job_ids": [item.get("job_id") for item in summaries],
        "jobs": summaries,
        "files": files,
    }
    return [summary, *images]


def fetch_result(
    client: ArtDaemonClient,
    config: MCPConfig,
    job_id: str,
    index: int,
) -> list[Any]:
    """Fetch one finished image, save it, return metadata + image."""
    data = client.fetch_png(job_id, index)
    path = _save_png(config, job_id, index, data)
    return [{"job_id": job_id, "index": index, "file": path}, Image(path=path)]


def run_background_removal(
    client: ArtDaemonClient,
    config: MCPConfig,
    input_image_path: str,
) -> list[Any]:
    """Remove one background, save the PNG, return metadata + image."""
    image_b64 = load_input_image_b64(input_image_path)
    data = client.remove_background(image_b64)
    target_dir = Path(config.output_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(input_image_path).expanduser().stem or "image"
    path = target_dir / f"{stem}-nobg.png"
    path.write_bytes(data)
    return [{"input": input_image_path, "file": str(path)}, Image(path=path)]


def build_server(
    config: MCPConfig | None = None,
    client: ArtDaemonClient | None = None,
) -> MCPServer:
    """Create the MCP server; inject config/client in tests."""
    resolved = config or MCPConfig.from_env()
    owned = client or ArtDaemonClient(resolved)
    server = MCPServer(SERVER_NAME)

    @server.tool()
    def generate_image(
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 9,
        cfg_scale: float = 0.0,
        seed: int | None = None,
        num_images: int = 1,
        model: str | None = None,
        version: str | None = None,
        scheduler: str | None = None,
        provider: str = "local",
        input_image_path: str | None = None,
        strength: float | None = None,
    ) -> list[Any]:
        """Generate images with AI Runner and return PNGs.

        Starts a daemon art job, waits for completion, saves each
        PNG under the output dir, and returns a summary plus the
        images. Z-Image uses one detailed prompt; negative prompts
        are ignored. Guidance 0.0 with ~9 steps suits Z-Image Turbo.
        provider "muse" sends the prompt to Meta; default "local"
        stays on the host with no silent fallback.
        """
        payload = build_generation_payload(
            prompt,
            width,
            height,
            steps,
            cfg_scale,
            seed,
            num_images,
            model,
            version,
            scheduler,
            provider,
            input_image_path,
            strength,
        )
        return run_generation(owned, resolved, payload)

    @server.tool()
    def generate_image_batch(
        prompts: list[str],
        width: int = 1024,
        height: int = 1024,
        steps: int = 9,
        cfg_scale: float = 0.0,
        seed: int | None = None,
        model: str | None = None,
        version: str | None = None,
        scheduler: str | None = None,
        provider: str = "local",
        input_image_path: str | None = None,
        strength: float | None = None,
    ) -> list[Any]:
        """Generate one image per prompt, sequentially.

        Runs each prompt as its own daemon job (the model stays warm
        between prompts). At most 8 prompts, one image each. A shared
        ``seed`` is incremented per prompt.
        """
        payloads = build_batch_payloads(
            prompts,
            width,
            height,
            steps,
            cfg_scale,
            seed,
            1,
            model,
            version,
            scheduler,
            provider,
            input_image_path,
            strength,
        )
        return run_generation_batch(owned, resolved, payloads)

    @server.tool()
    def remove_background(input_image_path: str) -> list[Any]:
        """Remove the background from one image and return its PNG.

        Sends the file to the daemon's RMBG-2.0 background removal,
        saves the RGBA result under the output dir, and returns
        metadata plus the image. Synchronous: no job polling.
        """
        return run_background_removal(owned, resolved, input_image_path)

    @server.tool()
    def get_generation_status(job_id: str) -> dict[str, Any]:
        """Return progress and state for one generation job."""
        return owned.get_status(job_id)

    @server.tool()
    def fetch_generation_result(
        job_id: str, index: int = 0
    ) -> list[Any]:
        """Fetch one finished image by index and return its PNG."""
        return fetch_result(owned, resolved, job_id, index)

    @server.tool()
    def cancel_generation(job_id: str) -> dict[str, Any]:
        """Cancel a running generation job (best-effort)."""
        return owned.cancel_job(job_id)

    @server.tool()
    def list_image_models() -> dict[str, Any]:
        """List installed art models for generate_image input."""
        return {
            "models": owned.list_models(),
            "registry": owned.list_registry_models(),
        }

    return server


def main() -> None:
    """Run the image-generation MCP server over stdio."""
    try:
        build_server().run()
    except DaemonError as exc:
        raise SystemExit(f"airunner-mcp: {exc}") from exc


if __name__ == "__main__":
    main()
