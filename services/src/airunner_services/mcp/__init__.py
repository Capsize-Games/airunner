"""MCP server for AI Runner image generation.

Thin stdio Model Context Protocol server that drives the AI Runner
daemon's public art HTTP API (``POST /api/v1/art/generate`` and
friends). It carries no model weights and needs no GPU: the daemon
owns Z-Image/SD pipelines, content-safety gates, and capacity.
"""

__all__: list[str] = []
