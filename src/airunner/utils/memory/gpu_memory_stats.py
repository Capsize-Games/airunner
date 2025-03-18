from typing import Dict
import torch


def gpu_memory_stats(device: torch.device) -> Dict:
    is_cuda = device.type == "cuda"
    
    stats = {
        "total": 0,
        "allocated": 0,
        "free": 0,
        "device_name": "N/A",
    }
    
    if is_cuda:
        stats["total"] = torch.cuda.get_device_properties(device).total_memory / (1024 ** 3)
        stats["allocated"] = torch.cuda.memory_allocated(device) / (1024 ** 3)
        stats["free"] = stats["total"] - stats["allocated"]
        stats["device_name"] = torch.cuda.get_device_name(device)
    
    return stats