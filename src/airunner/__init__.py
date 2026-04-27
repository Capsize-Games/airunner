"""AIRunner package initialization and runtime compatibility helpers."""

from __future__ import annotations

import importlib
import importlib.metadata as importlib_metadata
import os

from packaging.version import InvalidVersion, Version


def _is_truthy(value: str | None) -> bool:
	return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _apply_diffusers_torchao_workaround() -> bool:
	"""Disable diffusers' torchao integration for the known broken version pair.

	Diffusers 0.35.1 imports its torchao quantizer module during pipeline
	loading. With torchao 0.16.x, that path triggers an upstream NameError
	before AIRunner can construct SDXL pipelines. AIRunner does not depend on
	diffusers torchao quantization directly, so we disable that optional path
	up front for the affected versions.
	"""
	if _is_truthy(os.environ.get("AIRUNNER_ENABLE_DIFFUSERS_TORCHAO")):
		return False

	try:
		diffusers_version = Version(importlib_metadata.version("diffusers"))
		torchao_version = Version(importlib_metadata.version("torchao"))
	except importlib_metadata.PackageNotFoundError:
		return False
	except InvalidVersion:
		return False

	if diffusers_version != Version("0.35.1"):
		return False
	if torchao_version < Version("0.16.0"):
		return False

	try:
		diffusers_import_utils = importlib.import_module(
			"diffusers.utils.import_utils"
		)
	except Exception:
		return False

	if not getattr(diffusers_import_utils, "_torchao_available", False):
		return False

	diffusers_import_utils._torchao_available = False
	diffusers_import_utils._torchao_version = "disabled-by-airunner"
	os.environ.setdefault("AIRUNNER_DIFFUSERS_TORCHAO_DISABLED", "1")
	return True


_apply_diffusers_torchao_workaround()
