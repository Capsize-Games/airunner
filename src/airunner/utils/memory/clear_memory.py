import gc

try:
    import torch
except ImportError:
    torch = None


def clear_memory(device=0):
    """
    Clear the GPU ram.
    """
    if (
        torch is not None
        and hasattr(torch, "cuda")
        and torch.cuda.is_available()
    ):
        try:
            torch.cuda.set_device(device)
            torch.cuda.empty_cache()
            torch.cuda.reset_max_memory_allocated(device=device)
            torch.cuda.reset_max_memory_cached(device=device)
            torch.cuda.synchronize(device=device)
        except RuntimeError:
            print("Failed to clear memory")
    gc.collect()
