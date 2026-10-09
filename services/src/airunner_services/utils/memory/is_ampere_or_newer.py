try:
    import torch
except ImportError:  # pragma: no cover - optional dependency
    torch = None

from airunner_common.settings import AIRUNNER_DISABLE_FLASH_ATTENTION


def is_ampere_or_newer(device: int) -> bool:
    if AIRUNNER_DISABLE_FLASH_ATTENTION:
        return False
    if torch is None:  # pragma: no cover - optional dependency
        return False
    capability = torch.cuda.get_device_capability(device)
    major, minor = capability
    # Ampere GPUs have compute capability of 8.0 or higher
    return major >= 8
