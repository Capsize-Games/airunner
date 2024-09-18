import gc
import torch
from numba import cuda

def clear_memory():
    """
    Clear the GPU ram.
    """
    if torch.cuda.is_available():
        with torch.no_grad():
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            except RuntimeError:
                print("Failed to clear memory")
            gc.collect()
            try:
                torch.cuda.empty_cache()
            except RuntimeError:
                print("Failed to clear CPU memory")
    cuda.select_device(0)
    cuda.close()
    gc.collect()
