"""Daemon control endpoints — migrated to WebSocket RPC.

Previously hosted REST endpoints for runtime management
(``/status``, ``/runtimes``, ``/runtimes/{name}/load``, etc.).
These have been removed — all daemon communication now flows through
the unified WebSocket RPC channel at ``/api/v1/events``.
"""
