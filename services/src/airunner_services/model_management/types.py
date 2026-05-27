"""Enums and dataclasses for model resource management."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelState(Enum):
	"""Model lifecycle states."""

	UNLOADED = "unloaded"
	LOADING = "loading"
	LOADED = "loaded"
	LOADED_CPU = "loaded_cpu"
	UNLOADING = "unloading"
	BUSY = "busy"


@dataclass
class ActiveModelInfo:
	"""Information about an active model."""

	model_id: str
	model_type: str
	state: ModelState
	vram_allocated_gb: float
	ram_allocated_gb: float
	can_unload: bool


@dataclass
class MemoryAllocationBreakdown:
	"""Breakdown of memory allocation by category."""

	models_vram_gb: float
	canvas_history_vram_gb: float
	canvas_history_ram_gb: float
	system_reserve_vram_gb: float
	system_reserve_ram_gb: float
	external_apps_vram_gb: float
	total_available_vram_gb: float
	total_available_ram_gb: float