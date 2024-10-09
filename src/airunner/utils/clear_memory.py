import gc
import torch


def clear_memory(device=0):
    """
    Clear the GPU ram.
    """
    if torch.cuda.is_available():
        try:
            torch.cuda.set_device(device)
            torch.cuda.empty_cache()
            torch.cuda.reset_max_memory_allocated(device=device)
            torch.cuda.reset_max_memory_cached(device=device)
            torch.cuda.synchronize(device=device)
        except RuntimeError:
            print("Failed to clear memory")
    gc.collect()
