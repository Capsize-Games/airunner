import gc
import torch


def clear_memory():
    """
    Clear the GPU ram.
    """
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    gc.collect()
