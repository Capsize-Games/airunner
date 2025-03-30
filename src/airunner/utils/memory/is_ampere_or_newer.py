import torch

from airunner.settings import AIRUNNER_DISABLE_FLASH_ATTENTION


def is_ampere_or_newer(device: int) -> bool:
    if AIRUNNER_DISABLE_FLASH_ATTENTION:
        return False
    capability = torch.cuda.get_device_capability(device)
    major, minor = capability
    # Ampere GPUs have compute capability of 8.0 or higher
    return major >= 8
