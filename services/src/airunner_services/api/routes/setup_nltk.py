"""Bound language-data installation and terminate abandoned worker processes."""

import asyncio
import os
import sys
from pathlib import Path

import anyio

from airunner_services.setup_nltk_worker import PACKAGES


def _worker_command(directory: Path) -> list[str]:
    """Use the same daemon worker mode in Python and frozen bundles."""
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command.extend(["-m", "airunner_services.daemon"])
    return [*command, "--install-nltk-data", str(directory)]


async def _terminate_worker(process: asyncio.subprocess.Process) -> None:
    """Reap only the process owned by this request."""
    if process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


async def _wait_for_worker(
    process: asyncio.subprocess.Process, timeout: float,
) -> None:
    """Always stop the child on timeout, cancellation or failed execution."""
    try:
        if await asyncio.wait_for(process.wait(), timeout) != 0:
            raise RuntimeError("NLTK data installation failed")
    finally:
        # Streaming responses use cancellation scopes, which can otherwise
        # interrupt every cleanup await after a client disconnects.
        with anyio.CancelScope(shield=True):
            await _terminate_worker(process)


async def install_nltk_data(base_path: str) -> list[str]:
    """Install resources in a cancellable child with a finite deadline."""
    timeout = int(os.environ.get("AIRUNNER_SETUP_NLTK_TIMEOUT_SECONDS", "120"))
    if not 1 <= timeout <= 600:
        raise ValueError("Language-data deadline must be between 1 and 600 seconds")
    directory = Path(base_path) / "nltk_data"
    process = await asyncio.create_subprocess_exec(
        *_worker_command(directory),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await _wait_for_worker(process, timeout)
    return list(PACKAGES)
