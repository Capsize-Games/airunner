import gc
import torch


def clear_memory():
    """
    Clear the GPU ram.
    """
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        except RuntimeError:
            print("Failed to clear memory")
    gc.collect()
